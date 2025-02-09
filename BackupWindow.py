import concurrent.futures
import platform
import pathlib
from tkinter import *
from tkinter import ttk, filedialog
import socket

import runtime_globals as globals
import misc_tools as tools
import socket_io as sio
from DirectoryView import DirectoryView

class BackupWindow:
	def __init__(self, parent):
		self.mainframe = ttk.Frame(parent, padding="5 10")
		self.mainframe.grid(column=0, row=0, sticky=(N, S, E, W))

		# TODO: May make dir view and scroll bars in their own frame
		self.dir_view = DirectoryView(self.mainframe)
		self.dir_view.view.grid(column=0, row=0, columnspan=4, rowspan=6, sticky=(N, S, E, W), padx=5, pady=3)


		# Setting Scrollbars
		vert_scroll = ttk.Scrollbar(self.mainframe, orient="vertical", command=self.dir_view.view.yview)
		hori_scroll = ttk.Scrollbar(self.mainframe, orient="horizontal", command=self.dir_view.view.xview)
		self.dir_view.view.configure(yscrollcommand=vert_scroll.set, xscrollcommand=hori_scroll.set)
		vert_scroll.grid(column=4, row=0, rowspan=6, sticky=(N, S, W), padx=(0, 10))
		hori_scroll.grid(column=0, row=6, columnspan=4, sticky=(W, E, N), pady=(0, 10))

		# Setting up Buttons
		add_button = ttk.Button(self.mainframe, text="Add Folder", command=self.add_dir)
		add_button.grid(column=5, row=0, sticky=(N, E), padx=5, pady=(5, 3))

		add_button = ttk.Button(self.mainframe, text="Add File", command=self.add_file)
		add_button.grid(column=5, row=1, sticky=(N, E), padx=5, pady=(5, 3))

		remove_button = ttk.Button(self.mainframe, text="Remove", command=self.remove_item)
		remove_button.grid(column=5, row=2, sticky=(N, E), padx=5, pady=3)

		select_button = ttk.Button(self.mainframe, text="Select All", command=self.select_all)
		select_button.grid(column=5, row=3, sticky=(N, E), padx=5, pady=3)

		deselect_button = ttk.Button(self.mainframe, text="Deselect All", command=self.deselect_all)
		deselect_button.grid(column=5, row=4, sticky=(N, E), padx=5, pady=3)

		backup_button = ttk.Button(self.mainframe, text="Backup", command=self.backup)
		backup_button.grid(column=3, row=7, sticky=(N, W, E), padx=5, pady=(3, 5))

		# Setting up the treeview's fit to window
		self.mainframe.columnconfigure(index=0, weight=1)
		self.mainframe.columnconfigure(index=1, weight=1)
		self.mainframe.columnconfigure(index=2, weight=1)
		self.mainframe.rowconfigure(index=5, weight=1)

		executor = concurrent.futures.ThreadPoolExecutor()
		future = executor.submit(self.get_backup_conf, globals.HOST, globals.port, self.dir_view.directories)
		self.dir_view.view.after(500, tools.non_blocking_executor_shutdown, self.mainframe, executor, future)
		self.dir_view.view.after(100, self.dir_view.populate)

	def get_backup_conf(self, HOST: str, port: int, out: list[str]):
		try:
			client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			client.settimeout(globals.settings["TimeoutLength"] or 300)
			try:
				client.connect((HOST, port))
				print(HOST, port)
			except ConnectionRefusedError:
				out.append("ConnectionRefusedError")
				return
				
			sio.send(client, "ReqBC")
			out.extend(sio.recv_delim(client).split(sep="\n"))
			sio.send(client, "0")
			client.close()
		except socket.timeout:
			out.append("Connection Timed Out")

	# TODO: Make sure it updates the server about these changes and also make sure not to add files that are already present
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
		self.dir_view.directories.append(dir)
		self.dir_view.add_item(pathlib.Path(dir), base=True)

	def add_file(self):
		filename = filedialog.askopenfilename(
			parent=self.mainframe,
			title="Add File"
		)

		if filename == "":
			return
		self.dir_view.directories.append(filename)
		self.dir_view.add_item(pathlib.Path(filename), base=True)

	def remove_item(self):
		raise NotImplementedError

	def select_all(self):
		raise NotImplementedError

	def deselect_all(self):
		raise NotImplementedError

	def backup(self):
		raise NotImplementedError
