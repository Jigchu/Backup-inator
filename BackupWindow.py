import concurrent.futures
import datetime
import json
import platform
import pathlib
import shutil
import socket
from tkinter import *
from tkinter import ttk, filedialog, messagebox

import runtime_globals as globals
import misc_tools as tools
import socket_io as sio
from DirectoryView import DirectoryView
from RsyncTracker import RsyncTracker

class BackupWindow:
	def __init__(self, parent, menubar: Menu):
		self.last_modified = ""
		self.mainframe = ttk.Frame(parent, padding="5 10")
		self.mainframe.grid(column=0, row=0, sticky=(N, S, E, W))

		self.dir_view = DirectoryView(self.mainframe)
		self.dir_view.view.grid(column=0, row=0, columnspan=2, rowspan=6, sticky=(N, S, E, W), padx=5, pady=3)

		add_dir_button = ttk.Button(self.mainframe, text="Add Folder", command=self.add_dir)
		add_dir_button.grid(column=2, row=0, sticky=(N, E), padx=5, pady=(5, 3))

		add_file_button = ttk.Button(self.mainframe, text="Add File", command=self.add_file)
		add_file_button.grid(column=2, row=1, sticky=(N, E), padx=5, pady=(5, 3))

		remove_button = ttk.Button(self.mainframe, text="Remove", command=self.remove_item)
		remove_button.grid(column=2, row=2, sticky=(N, E), padx=5, pady=3)

		select_button = ttk.Button(self.mainframe, text="Select All", command=self.select_all)
		select_button.grid(column=2, row=3, sticky=(N, E), padx=5, pady=3)

		deselect_button = ttk.Button(self.mainframe, text="Deselect All", command=self.deselect_all)
		deselect_button.grid(column=2, row=4, sticky=(N, E), padx=5, pady=3)

		backup_button = ttk.Button(self.mainframe, text="Backup", command=self.backup)
		backup_button.grid(column=1, row=6, sticky=(N, W, E), padx=5, pady=(3, 5))

		self.buttons = {
			"AddFile": add_file_button,
			"AddDir": add_dir_button,
			"SelectAll": select_button,
			"DeselectAll": deselect_button,
			"Backup": backup_button,
		}

		# Setting up the treeview's fit to window
		self.mainframe.columnconfigure(0, weight=1)
		self.mainframe.rowconfigure(5, weight=1)

		self.dir_view.view.bind("<<DeselectedUpdate>>", lambda _: self.save_backup_conf())

		self.menubar = menubar
		self.populate_menubar()

		# Populate dir_view with backup directories
		executor = concurrent.futures.ThreadPoolExecutor()
		future = executor.submit(self.load_backup_conf)
		self.mainframe.after(500, tools.non_blocking_executor_shutdown, self.mainframe, executor, future)
		self.dir_view.view.after(100, self.dir_view.populate)

		# Kickstart the backup.json autoupdater
		self.mainframe.after(10, self.update_remote_backup_conf, datetime.datetime.now())

	def populate_menubar(self):
		file_menu = Menu(self.menubar)
		file_menu.add_command(label="Add Folder", command=self.add_dir)
		file_menu.add_command(label="Add File", command=self.add_file)
		file_menu.add_separator()

		import_menu = Menu(file_menu)
		import_menu.add_command(label="Backup.json")
		import_menu.add_command(label="Settings.json")

		export_menu = Menu(file_menu)
		export_menu.add_command(label="Backup.json")
		export_menu.add_command(label="Settings.json")

		file_menu.add_cascade(menu=import_menu, label="Import...")
		file_menu.add_cascade(menu=export_menu, label="Export...")

		edit_menu = Menu(self.menubar)
		edit_menu.add_command(label="Remove", command=self.remove_item)
		edit_menu.add_command(label="Select All", command=self.select_all)
		edit_menu.add_command(label="Deselect All", command=self.deselect_all)
		edit_menu.add_command(label="Edit Host Details")
		edit_menu.add_command(label="Edit Preferences")

		backup_menu = Menu(self.menubar)
		backup_menu.add_command(label="Backup", command=self.backup)
		backup_menu.add_command(label="Backup All", command=self.backup_all)
		backup_menu.add_command(label="Backup From...", command=self.backup_from)

		self.menubar.add_cascade(menu=file_menu, label="File")
		self.menubar.add_cascade(menu=edit_menu, label="Edit")
		self.menubar.add_cascade(menu=backup_menu, label="Backup")

	def load_backup_conf(self):
		remote_backup_conf = self.get_remote_backup_conf()
		local_backup_conf = self.get_local_backup_conf()

		remote_last_modified = remote_backup_conf.get("LastModified") or ""
		local_last_modified = local_backup_conf.get("LastModified")

		backup_conf = (
			local_backup_conf 
			if local_last_modified >= remote_last_modified
			else remote_backup_conf
		)

		self.last_modified = backup_conf.get("LastModified") or ""
		self.dir_view.directories = backup_conf.get("BackupDirectories")
		self.dir_view.deselected = set(backup_conf.get("DeselectedDirectories")) or set()
		self.dir_view.removed = set(backup_conf.get("RemovedDirectories")) or set()
	
	def get_remote_backup_conf(self):
		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client.settimeout(globals.TIMEOUT_LENGTH)
		client.connect((globals.HOST, globals.port))
		sio.send(client, "RequestBackupConf", type="delim")
		backup_conf_string = sio.recv_delim(client, globals.HOST)
		client.shutdown(socket.SHUT_RDWR)
		client.close()

		if backup_conf_string == "":
			return {}

		return json.loads(backup_conf_string)

	def get_local_backup_conf(self):
		try:
			backup_json = open("backup.json", mode="r")
		except FileNotFoundError:
			backup_json = open("backup.json", mode="x")
		finally:
			backup_json.close()

		backup_json = open("backup.json", mode="r")
		try:
			backup_conf: dict = json.load(backup_json)
		except json.JSONDecodeError:
			backup_conf = {}

		return backup_conf

	def save_backup_conf(self):
		self.last_modified = datetime.datetime.now(datetime.timezone.utc)
		self.last_modified = tools.datetime_to_ISO8601(self.last_modified)
		json_contents = {}

		json_contents["LastModified"] = self.last_modified
		json_contents["BackupDirectories"] = self.dir_view.directories
		json_contents["DeselectedDirectories"] = list(self.dir_view.deselected)
		json_contents["RemovedDirectories"] = list(self.dir_view.removed)
		
		with open("backup.json", mode="w") as backup_json:
			json.dump(json_contents, backup_json)

		return

	# Interval is in minutes
	def update_remote_backup_conf(self, last_update_time: datetime.datetime):
		INTERVAL = globals.settings.get("RemoteUpdateInterval") or 5
		now = datetime.datetime.now()
		time_since_last_update = now - last_update_time
		if time_since_last_update < datetime.timedelta(minutes=INTERVAL):
			self.mainframe.after(10, self.update_remote_backup_conf, last_update_time)
			return

		executor = concurrent.futures.ThreadPoolExecutor()
		future = executor.submit(self.send_backup_conf)
		self.mainframe.after(10, tools.non_blocking_executor_shutdown, self.mainframe, executor, future)

		# If updated start another countdown but with the current time as the last updated time
		self.mainframe.after(10, self.update_remote_backup_conf, now)

		return

	def send_backup_conf(self):
		json_contents = {}
		json_contents["LastModified"] = self.last_modified
		json_contents["BackupDirectories"] = self.dir_view.directories
		json_contents["DeselectedDirectories"] = list(self.dir_view.deselected)
		json_contents["RemovedDirectories"] = list(self.dir_view.removed)

		json_string = json.dumps(json_contents)

		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client.settimeout(globals.TIMEOUT_LENGTH)
		client.connect((globals.HOST, globals.port))
		sio.send(client, "UpdateBackupConf", type="delim")
		sio.send(client, json_string, type="delim")
		client.shutdown(socket.SHUT_RDWR)
		client.close()

		return

	def add_dir(self):
		"""
		The reason why the title of dialogs can use platform specific terminology
		but the name of buttons cannot is due to the fact that the word "Directory"
		is too long and would cause the button to widen which just looks wrong
		so "Add Folder" is the name of button regardless of platform while the
		title will change based on whether you are using a Unix OS or Windows
		"""
		terminology = "Folder" if platform.system == "Windows" else "Directory"
		dir = filedialog.askdirectory(
			parent=self.mainframe,
			title=f"Add {terminology}",
			mustexist=True
		)

		if dir == "":
			return
		
		self.dir_view.add_item(pathlib.Path(dir), base=True)
		self.save_backup_conf()

	def add_file(self):
		filename = filedialog.askopenfilename(
			parent=self.mainframe,
			title="Add File"
		)

		if filename == "":
			return
		
		self.dir_view.add_item(pathlib.Path(filename), base=True)
		self.save_backup_conf()

	def remove_item(self):
		selected_items = self.dir_view.last_selection
		for item in selected_items:
			self.dir_view.remove_item(item)
		self.save_backup_conf()

	def select_all(self):
		self.dir_view.select("")

	def deselect_all(self):
		self.dir_view.deselect("")

	def backup(self):
		include_dirs = self.dir_view.directories.copy()
		
		exclude_dirs = []
		exclude_dirs.extend(self.dir_view.deselected.copy())
		exclude_dirs.extend(self.dir_view.removed.copy())

		self.__backup__(include_dirs=include_dirs, exclude_dirs=exclude_dirs)

	def backup_all(self):
		include_dirs = self.dir_view.directories.copy()
		self.__backup__(include_dirs=include_dirs, exclude_dirs=[])
	
	def backup_from(self):
		terminology = "Folder" if platform.system == "Windows" else "Directory"
		dir = filedialog.askdirectory(
			parent=self.mainframe,
			title=f"Add {terminology}",
			mustexist=True
		)

		if dir == "":
			return
		
		dir = pathlib.Path(dir)

		self.__backup__(include_dirs=[dir.as_posix()], exclude_dirs=[])

	def __backup__(self, include_dirs: list[str], exclude_dirs: list[str]):
		self.menubar.entryconfigure("Backup", state=DISABLED)
		self.buttons["Backup"].state(["disabled"])

		include_file = self.__create_files_from_file__(include_dirs)
		exclude_file = self.__create_exclude_file__(exclude_dirs)
		
		if platform.system() == "Windows":
			include_file = tools.win_to_rsync_readable_posix(include_file)
			exclude_file = tools.win_to_rsync_readable_posix(exclude_file)
		
		rsync_path = shutil.which("rsync")
		rsync_user = globals.settings.get("ServerUser") or "user"
		
		out_format = "| %f | %b"
		ssh_port = globals.settings.get("SSHPort") or 22
		ssh_command = f"ssh -p {ssh_port}"
		rsync_command = [
			rsync_path, "-e", ssh_command, "--archive", "--recursive", "--no-relative", "--compress",
			"--partial", f"--exclude-from={exclude_file}", f"--files-from={include_file}",
			f'--out-format={out_format}', "/", f"{rsync_user}@{globals.HOST}:~/Backup/"
		]
		
		total_to_backup = self.total_files_to_backup(include_dirs, exclude_dirs)
		rsync_progress = RsyncTracker(
			self.mainframe, rsync_command=rsync_command, total_to_backup=total_to_backup
		)

		rsync_progress.window.bind("<<RsyncCompleted>>", lambda e: self.__end_backup__(e))

		return

	def __end_backup__(self, e: Event):
		pathlib.Path("ExcludeFrom.tmp").resolve().unlink()
		pathlib.Path("FilesFrom.tmp").resolve().unlink()
		e.widget.destroy()
		
		self.menubar.entryconfigure("Backup", state=NORMAL)
		self.buttons["Backup"].state(["!disabled"])
		return

	def __create_files_from_file__(self, include_dirs: list[str]):
		if platform.system() == "Windows":
			include_dirs = list(map(tools.win_to_rsync_readable_posix, map(pathlib.Path, include_dirs)))

		file_contents = "\n".join(include_dirs)
		with open("FilesFrom.tmp", mode="w") as include_file:
			if include_file.write(file_contents) != len(file_contents):
				messagebox.showwarning(
					title="Write Error",
					message="Could not fully write the contents of FilesFrom.tmp"
				)

		return pathlib.Path("FilesFrom.tmp").resolve()
	
	def __create_exclude_file__(self, exclude_dirs: list[str]):
		if platform.system() == "Windows":
			exclude_dirs = list(map(tools.win_to_rsync_readable_posix, map(pathlib.Path, exclude_dirs)))
		
		file_contents = "\n".join(exclude_dirs)
		with open("ExcludeFrom.tmp", mode="w") as exclude_file:
			if exclude_file.write(file_contents) != len(file_contents):
				messagebox.showwarning(
					title="Write Error",
					message="Could not fully write the contents of ExcludeFrom.tmp"
				)

		return pathlib.Path("ExcludeFrom.tmp").resolve()
	
	def total_files_to_backup(self, include_dirs: list[str], exclude_dirs: list[str]):
		total_include = map(pathlib.Path, include_dirs)
		total_include = sum(
			map(tools.how_many_files_in, total_include)
		)

		total_exclude = map(pathlib.Path, exclude_dirs)
		total_exclude = sum(
			map(tools.how_many_files_in, total_exclude)
		)

		return total_include - total_exclude