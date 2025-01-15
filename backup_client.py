import concurrent.futures
import pathlib
import platform
from tkinter import *
from tkinter import ttk, messagebox
from typing import Literal
import socket_io as sio
import socket
import sys

TIMEOUT_LENGTH = 300
HOST: str = None
port: int = None
root = Tk()

def get_backup_conf(HOST: str, port: int, out: list[str]):
	try:
		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client.settimeout(TIMEOUT_LENGTH)
		try:
			client.connect((HOST, port))
		except ConnectionRefusedError:
			out.append("ConnectionRefusedError")
			return
			
		sio.send(client, "ReqBC")
		out.extend(sio.recv_delim(client).split(sep="\n"))
		sio.send(client, "0")
		client.close()
	except socket.timeout:
		out.append("Connection Timed Out")

def non_blocking_executor_shutdown(executor: concurrent.futures.Executor, future: concurrent.futures.Future):
	if future.done():
		executor.shutdown()
		return
	root.after(10, non_blocking_executor_shutdown, executor, future)

# TODO: get file and directory sizes
def get_size(path: pathlib.Path) -> str:
	return ""

# Function that converts window paths to POSIX paths that are readable by rsync
def win_to_rsync_readable_posix(path: pathlib.Path) -> str:
	win_as_posix = path.as_posix()
	win_as_posix = win_as_posix.split(sep="/")
	win_as_posix[0] = "/" + win_as_posix[0][0].lower()
	win_as_posix = "/".join(win_as_posix)

	return win_as_posix

class ClientWindow:
	def __init__(self):
		global HOST
		global port

		hostname = "rpi.local" # TODO: Harcoded for now
		try:
			HOST = socket.gethostbyname(hostname) # Add gaierror hadnling to entire program
		except socket.gaierror:
			messagebox.showerror(
				title="getaddrinfo failed",
				message="Failed to get the server's IP",
				detail="Please check if the server exists"
			)
		port = 9999
		self.backup_win = BackupWindow()


"""
This does not come with ScrollBars do it yourself
"""
class DirectoryView:
	def __init__(self, parent: Misc | None = None):
		self.directories = []

		info_columns = ("Size", "Selected")	# TODO: Size will be implemented later also may add date
		self.view = ttk.Treeview(parent, columns=info_columns, padding=(5))
		
		# Setting column configuration
		self.view.column("#0", anchor="nw", minwidth=200, stretch=True)
		self.view.column("Size", anchor="ne", width=70, stretch=False)
		self.view.column("Selected", anchor="center", width=70, stretch=False)

		# Setting the headers
		self.view.heading("#0", text="Name")
		for column in info_columns:
			self.view.heading(column, text=column)

	def populate(self):
		if self.directories == []:
			root.after(10, self.populate)
			return
		
		# Check if either the connection timed out or is refused
		if "ConnectionRefusedError" in self.directories:
			messagebox.showerror(
				title="Connection Refused", 
				message="Please check if the server you are connecting to is online"
			)
			return
		if "Connection Timed Out" in self.directories:
			messagebox.showerror(
				title="Connection Timed Out", 
				message="Please check if your internet has a stable connection"
			)
			return

		# Check is there are no directories
		if "None" in self.directories:
			messagebox.showerror(
				title="No Directories",
				message="There are no directories, please check your server."
			)
			return

		# Set the root directory
		root_dir = pathlib.Path(sys.executable).anchor
		if platform.system() == "Windows":
			root_dir = root_dir[:2].upper()
		self.view.insert("", iid=root_dir, index=0, text=root_dir, values=(get_size(pathlib.Path(root_dir)), "\u2610"))
		root.after(1, self.__populate__, 0)

	def __populate__(self, index):
		try:
			directory = self.directories[index]
		except IndexError:
			return
		
		path = pathlib.Path(directory)

		if not path.exists():
			self.directories.remove(directory)
			root.after(10, self.__populate__, index)
			return
		
		self.add_item(path, selected=True)
		root.after(10, self.__populate__, index+1)
	
	def add_item(self, path: pathlib.Path, selected: bool=False):
		posix_path = path.as_posix()
		path_segments = posix_path.split(sep="/")

		# Check if all parents are created
		for i in range(len(path_segments[:-1])):
			parent = "/".join(path_segments[:i+1])
			if not self.view.exists(parent):
				self.__add_item__(pathlib.Path(parent), type="dir")
	
		if path.is_dir():
			self.__add_item__(path, "dir", selected)
		else:
			self.__add_item__(path, "file", selected)

	# TODO: Add folder icons for directories and file icons for files
	def __add_item__(self, path: pathlib.Path, type: Literal["dir", "file"], selected: bool=False):
		checkbox = "\u2611" if selected else "\u2610"
		posix_path = path.as_posix()
		path_segments = posix_path.split(sep="/")

		parent_iid = "/".join(path_segments[:-1])
		self.view.insert(parent_iid, iid=posix_path, index="end", text=path_segments[-1], values=[get_size(path), checkbox])

		if not selected or type == "file":
			return
		
		path_sep = "\\" if platform.system() == "Windows" else "/"
		dirpath = ""
		dirnames = []
		filenames = []

		for dirpath, dirnames, filenames in path.walk(follow_symlinks=True):
			break
		for dirname in dirnames:
			if self.view.exists(f"{dirpath}{path_sep}{dirname}"):
				continue
			root.after(100, self.add_item, pathlib.Path(f"{dirpath}{path_sep}{dirname}"), True)
		for filename in filenames:
			if self.view.exists(f"{dirpath}{path_sep}{filename}"):
				continue
			root.after(100, self.add_item, pathlib.Path(f"{dirpath}{path_sep}{filename}"), True)

class BackupWindow:
	def __init__(self):
		root.option_add("*tearOff", FALSE)
		root.title("Backup-inator")
		root.minsize(width=800, height=400)

		self.mainframe = ttk.Frame(root, padding="5 10")
		self.mainframe.grid(column=0, row=0, sticky=(N, S, E, W))
		root.columnconfigure(index=0, weight=1)
		root.rowconfigure(index=0, weight=1)

		# TODO: May make dir view and scroll bars in their own frame
		self.dir_view = DirectoryView(self.mainframe)
		self.dir_view.view.grid(column=0, row=0, columnspan=4, rowspan=5, sticky=(N, S, E, W), padx=5, pady=3)

		# Setting Scrollbars
		vert_scroll = ttk.Scrollbar(self.mainframe, orient="vertical", command=self.dir_view.view.yview)
		hori_scroll = ttk.Scrollbar(self.mainframe, orient="horizontal", command=self.dir_view.view.xview)
		self.dir_view.view.configure(yscrollcommand=vert_scroll.set, xscrollcommand=hori_scroll.set)
		vert_scroll.grid(column=4, row=0, rowspan=5, sticky=(N, S, W), padx=(0, 10))
		hori_scroll.grid(column=0, row=5, columnspan=4, sticky=(W, E, N), pady=(0, 10))

		# Setting up Buttons
		add_button = ttk.Button(self.mainframe, text="Add", command=self.add_dir)
		add_button.grid(column=5, row=0, sticky=(N, E), padx=5, pady=(5, 3))

		remove_button = ttk.Button(self.mainframe, text="Remove", command=self.remove_dir)
		remove_button.grid(column=5, row=1, sticky=(N, E), padx=5, pady=3)

		select_button = ttk.Button(self.mainframe, text="Select All", command=self.select_all)
		select_button.grid(column=5, row=2, sticky=(N, E), padx=5, pady=3)

		deselect_button = ttk.Button(self.mainframe, text="Deselect All", command=self.deselect_all)
		deselect_button.grid(column=5, row=3, sticky=(N, E), padx=5, pady=3)

		backup_button = ttk.Button(self.mainframe, text="Backup", command=self.backup)
		backup_button.grid(column=3, row=7, sticky=(N, W, E), padx=5, pady=(3, 5))

		# Setting up the treeview's fit to window
		self.mainframe.columnconfigure(index=0, weight=1)
		self.mainframe.columnconfigure(index=1, weight=1)
		self.mainframe.columnconfigure(index=2, weight=1)
		self.mainframe.rowconfigure(index=4, weight=1)

		menubar = Menu(root)
		file_menu = Menu(menubar)
		menubar.add_cascade(menu=file_menu, label="File", underline=0)
		root["menu"] = menubar

		executor = concurrent.futures.ThreadPoolExecutor()
		future = executor.submit(get_backup_conf, HOST, port, self.dir_view.directories)
		root.after(500, non_blocking_executor_shutdown, executor, future)
		root.after(100, self.dir_view.populate)
		root.mainloop()

	def add_dir(self):
		raise NotImplementedError

	def remove_dir(self):
		raise NotImplementedError

	def select_all(self):
		raise NotImplementedError

	def deselect_all(self):
		raise NotImplementedError

	def backup(self):
		raise NotImplementedError

def main():
	client_win = ClientWindow()

if __name__ == "__main__":
	main()