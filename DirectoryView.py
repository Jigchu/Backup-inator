import math
import pathlib
import platform
from tkinter import *
from tkinter import ttk, messagebox
from typing import Literal

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
	def __init__(self, parent):
		self.parent = parent
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
			self.parent.after(10, self.populate)
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
		
		self.parent.after(1, self.__populate__, 0)

	def __populate__(self, index):
		try:
			directory = self.directories[index]
		except IndexError:
			return
		
		path = pathlib.Path(directory)

		if not path.exists():
			self.directories.remove(directory)
			self.parent.after(10, self.__populate__, index)
			return
	
		# Add base node with children if directory
		self.add_item(path, base=True)
		if (not path.is_dir() and not path.is_file()):
			messagebox.showerror(
				title="Erm",
				message="What did you give me? How is {path} somehow not a file or directory? I'm confused"
			)

		self.parent.after(10, self.__populate__, index+1)
	
	def add_item(self, path: pathlib.Path, base: bool=False):
		posixed_path = path.as_posix()
		if self.view.exists(posixed_path):
			return

		if posixed_path not in self.directories:
			self.directories.append(posixed_path)
		text = str(path) if base else path.name
		parent = "" if base else path.parent.as_posix()
		self.view.insert(parent, iid=posixed_path, index="end", text=text, values=(self.update_size(path), "\u2611"))

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
			self.parent.after(10, self.add_item, child_p)

		return

	# Wrapper for get_size but may be used for optimisations later
	def update_size(self, path: pathlib.Path, unit: Literal["iB", "B"]="B"):
		return self.get_size(path, unit)
	
	def __get_size__(self, path: pathlib.Path):
		if path.is_dir():
			return sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
		elif path.is_file():
			return path.stat().st_size
		return -1

	def get_size(self, path: pathlib.Path, unit: Literal["B", "iB"]="B"):
		base = 1000 if unit == "B" else 1024
		prefixes = "kMGTPEZ"
		size = self.__get_size__(path)
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
