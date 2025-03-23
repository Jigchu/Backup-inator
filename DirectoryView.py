import pathlib
import platform
from tkinter import *
from tkinter import ttk, messagebox
from typing import Literal

import misc_tools as tools

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

	NOT_SELECTED = "\u2610"
	"""
	UUID will have the NOT_SELECTED symbol if:

	- It is in self.deselected
	- It is a child of a directory who is in 
	self.deselected
	- It has a child that has a NOT_SELECTED
	symbol or is in self.deselected
	"""

	SELECTED = "\u2611"
	"""
	UUID will have the SELECTED symbol if:
	1. UUID is not in self.deselected
	2. UUID's children all also have the
	SELECTED symbol
	"""
	
	INFO_COLUMNS = ("Name", "Size", "Selected")

	def __init__(self, parent):
		self.parent = parent
		self.last_selection = ()
		self.directories: list[str] = []
		self.deselected: set[str] = set()
		self.removed: set[str] = set()
		"""
		UUID will be in self.deselected if:
		- It is a deselected file 
		- It is a directory in which all children are also deselected
		- It has been removed using the "Remove" button

		Where children of directories in self.deselected will not be
		in self.deselected
		"""

		self.view = ttk.Treeview(parent, columns=self.INFO_COLUMNS[1:], padding=(5))
		
		# Setting column configuration
		self.view.column("#0", anchor="nw", minwidth=200, stretch=True)
		self.view.column("#1", anchor="ne", width=70, stretch=False)
		self.view.column("#2", anchor="center", width=70, stretch=False)

		# Setting the headers
		self.view.heading("#0", text="Name")
		for index, column in enumerate(self.INFO_COLUMNS):
			self.view.heading(f"#{index}", text=column)
		
		self.view.bind("<Button-1>", func=(
				lambda e: 
				self.select_binding(self.view.identify_row(e.y))
				if self.get_column(e) == "Selected" 
				else None
			)
		)

		self.view.bind("<<TreeviewSelect>>", func=self.update_last_selection)

	def update_last_selection(self, e):
		self.last_selection = self.view.selection()

	def select_binding(self, uuid: str):
		self.deselect(uuid) if self.get_current_selection(uuid) == self.SELECTED else self.select(uuid)

	def get_column(self, e: Event):
		return self.INFO_COLUMNS[int(self.view.identify_column(e.x)[1:])]

	def populate(self):
		if self.directories == []:
			self.parent.after(10, self.populate)
			return
		
		if self.directories == None:
			return

		self.parent.after(1, self.__populate__, 0)

	def add_item(self, path: pathlib.Path, base: bool=False):
		posixed_path = path.as_posix()
		if self.view.exists(posixed_path):
			return

		try:
			self.removed.remove(posixed_path)
		except KeyError:
			pass

		if base and posixed_path not in self.directories:
			self.directories.append(posixed_path)
		text = str(path) if base else path.name
		parent = "" if base else path.parent.as_posix()
		self.view.insert(parent, iid=posixed_path, index="end", text=text, values=(self.update_size(path, unit="B"), self.SELECTED))

		if path.is_dir():
			self.__add_children__(path)

	def remove_item(self, uuid: str):
		if uuid == "":
			self.deselected.clear()
			return
		
		parent = self.view.parent(uuid)
		self.view.delete(uuid)
		self.removed.add(uuid)

		if uuid in self.directories:
			self.directories.remove(uuid)
			self.removed.remove(uuid)
		
		try:
			self.deselected.remove(uuid)
		except KeyError:
			return
		
		# Remove Children
		self.deselected = set([i for i in self.deselected if uuid not in i])
		self.removed = set([i for i in self.removed if uuid not in i])

		if self.get_all_children(parent) == []:
			if parent == "":
				self.directories = []
				self.removed = set()
				self.deselected = set()
				return
			self.deselected = set([i for i in self.deselected if parent not in i])
			self.removed = set([i for i in self.removed if parent not in i])

		self.__edit_parent_selection__(parent)
		return

	# Wrapper for get_size but may be used for optimisations later
	def update_size(self, path: pathlib.Path, unit: Literal["iB", "B"]):
		return self.get_size(path, unit)

	def get_size(self, path: pathlib.Path, unit: Literal["B", "iB"]):
		return tools.human_readable_file_size(tools.size_of(path), unit)
	
	def remove_from_deselect(self, uuid):
		try:
			self.deselected.remove(uuid)
		except KeyError:
			pass

	def select(self, uuid: str):
		self.__edit_selection__(uuid, select=True)
		self.remove_from_deselect(uuid)
		self.view.event_generate("<<DeselectedUpdate>>")
	
	def deselect(self, uuid: str):
		self.__edit_selection__(uuid, select=False)
		self.deselected.add(uuid)
		self.view.event_generate("<<DeselectedUpdate>>")

	def __edit_selection__(self, uuid: str, select: bool):
		new_symbol = self.SELECTED if select else self.NOT_SELECTED
		self.view.set(uuid, column="Selected", value=new_symbol)
		self.__edit_child_selection__(uuid, select)

		parent_id = self.view.parent(uuid)
		self.view.after(10, self.__edit_parent_selection__, parent_id)

	
	def __edit_parent_selection__(self, uuid: str):
		original_selection = self.get_current_selection(uuid)
		children = self.view.get_children(uuid)
		all_selected = all (
			map (
				lambda c: self.get_current_selection(c) == self.SELECTED,
				children
			)
		)

		new_selection = self.SELECTED if all_selected else self.NOT_SELECTED
		self.view.set(uuid, column="Selected", value=new_selection)

		if original_selection == new_selection or uuid == "":
			self.view.after(10, self.__compute_deselected__, "")
		else:
			self.view.after(
				10, self.__edit_parent_selection__, 
				self.view.parent(uuid),
			)

		return

	def __compute_deselected__(self, root: str):
		children: list = list(self.get_all_children(root))
		
		if self.get_current_selection(root) == self.SELECTED:
			self.remove_from_deselect(root)
			self.deselected = self.deselected.difference(children)
			return
		
		all_deselected = all (
			map (
				lambda c: self.get_current_selection(c) == self.NOT_SELECTED,
				children
			)
		)

		if all_deselected:
			self.deselected.add(root)
			self.deselected = self.deselected.difference(children)
		elif not all_deselected:
			self.remove_from_deselect(root)
			# Compute deselected of children
			for child in self.view.get_children(root):
				self.view.after(10, self.__compute_deselected__, child)

		return

	def get_all_children(self, root: str):
		children: list = list(self.view.get_children(root))

		for child in children:
			children.extend(self.view.get_children(child))

		return children

	def __edit_child_selection__(self, uuid: str, select: bool):
		new_symbol = self.SELECTED if select else self.NOT_SELECTED
		children = self.get_all_children(uuid)

		# Converted to list so that map is evaluated as map uses lazy evaluation
		list(map(lambda c: self.view.set(c, column="Selected", value=new_symbol), children))
		
		return

	def get_current_selection(self, uuid: str):
		return self.view.set(uuid, column="Selected")

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