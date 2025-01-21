import concurrent.futures
import math
import pathlib
import platform
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from typing import Literal
import socket_io as sio
import socket

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

def __get_size__(path: pathlib.Path):
	if path.is_dir():
		return sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
	elif path.is_file():
		return path.stat().st_size
	return -1

def get_size(path: pathlib.Path, unit: Literal["B", "iB"]="B"):
	base = 1000 if unit == "B" else 1024
	prefixes = "kMGTPEZ"
	size = __get_size__(path)
	if size == 0:
		return "0 B"
	elif size < 0:
		return "N/A"
	
	power = int(math.log(size, base))
	prefix = prefixes[power-1]
	if power == 0:
		return f"{size} B"
	
	prefixed_size = round(size/(base**power), 1)

	return f"{prefixed_size} {prefix}{unit}"


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


class DirectoryView:
	"""
	Although the class is called "Directory View", it is fully capable of
	displaying files. Though admittedly, that is not what it was originally
	designed for but knowing there will be definitely be people who want to
	just back up one file in a whole directory, I have decided to add that
	functionality. Therefore, anything with the a name containing the word
	directory and all its other derivatives are also able to work with paths
	to files except for its methods. Methods meant to handle both files and
	directories use the word item due to a lack of a better word.

	DISCLAIMER: This class does not come with ScrollBars, you have to implement
	that yourself
	"""
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
	
		# Add base node with children if directory
		self.add_item(path, base=True)
		if (not path.is_dir() and not path.is_file()):
			messagebox.showerror(
				title="Erm",
				message="What did you give me? How is {path} somehow not a file or directory? I'm confused"
			)

		root.after(10, self.__populate__, index+1)
	
	def add_item(self, path: pathlib.Path, base: bool=False):
		text = str(path) if base else path.name
		parent = "" if base else path.parent.as_posix()
		self.view.insert(parent, iid=path.as_posix(), index="end", text=text, values=(self.update_size(path), "\u2611"))

		if path.is_dir():
			self.__add_children__(path)

	def __add_children__(self, path: pathlib.Path):
		path_sep = "\\" if platform.system() == "Windows" else "/"
		dirpath = ""
		dirnames = []
		filenames = []
		for dirpath, dirnames, filenames in path.walk(follow_symlinks=True):
			break

		children = dirnames + filenames
		for child in children:
			child_p = pathlib.Path(f"{dirpath}{path_sep}{child}")
			root.after(10, self.add_item, child_p)

		return

	# Wrapper for get_size but may be used for optimisations later
	def update_size(self, path: pathlib.Path, unit: Literal["iB", "B"]="B"):
		return get_size(path, unit)

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

		menubar = Menu(root)
		file_menu = Menu(menubar)
		menubar.add_cascade(menu=file_menu, label="File", underline=0)
		root["menu"] = menubar

		executor = concurrent.futures.ThreadPoolExecutor()
		future = executor.submit(get_backup_conf, HOST, port, self.dir_view.directories)
		root.after(500, non_blocking_executor_shutdown, executor, future)
		root.after(100, self.dir_view.populate)
		root.mainloop()

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

def main():
	client_win = ClientWindow()

if __name__ == "__main__":
	main()