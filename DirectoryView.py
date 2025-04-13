import pathlib
from tkinter import *
from tkinter import ttk
from typing import Literal

import misc_tools as tools

class DirectoryView:
	"""
	DISCLAIMER:
	1. "Directories" can refer to files not just directories
	2. "Folder" refers to Directories
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
		self.populating = False
		self.directories: list[str] = []
		self.removed: set[str] = set()
		self.deselected: set[str] = set()
		"""
		UUID will be in self.deselected if:
		- It is a deselected file 
		- It is a directory in which all children are also deselected
		- It has been removed using the "Remove" button

		Where children of directories in self.deselected will not be
		in self.deselected
		"""

		self.view = ttk.Frame(parent)

		self.dir_tree = ttk.Treeview(self.view, columns=self.INFO_COLUMNS[1:], padding=(5))
		self.dir_tree.grid(column=0, row=0, sticky=(N, S, E, W))
		
		self.dir_tree.column("#0", anchor="nw", minwidth=200, stretch=True)
		self.dir_tree.column("#1", anchor="ne", width=70, stretch=False)
		self.dir_tree.column("#2", anchor="center", width=70, stretch=False)

		# Setting the headers
		self.dir_tree.heading("#0", text="Name")
		for index, column in enumerate(self.INFO_COLUMNS):
			self.dir_tree.heading(f"#{index}", text=column)

		vert_scroll = ttk.Scrollbar(self.view, orient="vertical", command=self.dir_tree.yview)
		hori_scroll = ttk.Scrollbar(self.view, orient="horizontal", command=self.dir_tree.xview)
		self.dir_tree.configure(yscrollcommand=vert_scroll.set, xscrollcommand=hori_scroll.set)
		vert_scroll.grid(column=1, row=0, sticky=(N, S, W), padx=(0, 10))
		hori_scroll.grid(column=0, row=1, sticky=(N, W, E), pady=(0, 10))

		self.view.rowconfigure(0, weight=1)
		self.view.columnconfigure(0, weight=1)

		self.dir_tree.bind("<Button-1>", func=(
				lambda e: 
				self.select_binding(self.dir_tree.identify_row(e.y))
				if self.get_column(e) == "Selected" 
				else None
			)
		)

		self.dir_tree.bind("<<TreeviewSelect>>", func=self.update_last_selection)

	def edit_population_state(self):
		self.populating = not self.populating

	def update_last_selection(self, e: Event):
		self.last_selection = self.dir_tree.selection()

	def select_binding(self, uuid: str):
		self.deselect(uuid) if self.get_current_selection(uuid) == self.SELECTED else self.select(uuid)

	def get_column(self, e: Event):
		try:
			return self.INFO_COLUMNS[int(self.dir_tree.identify_column(e.x)[1:])]
		except ValueError:
			return ""

	def populate(self):
		if self.directories == []:
			self.view.after(10, self.populate)
			return
		
		if self.directories == None:
			return

		self.populating = True
		self.view.after(1, self.__populate__, 0)

	def add_item(self, path: pathlib.Path, base: bool=False):
		uuid = path.as_posix()
		if self.dir_tree.exists(uuid):
			return

		if not self.populating:
			try:
				self.removed.remove(uuid)
			except KeyError:
				pass

		if base and uuid not in self.directories:
			self.directories.append(uuid)
		
		text = str(path) if base else path.name
		parent = "" if base else path.parent.as_posix()
		self.dir_tree.insert(parent, iid=uuid, index="end", text=text, values=(self.update_size(path, unit="B"), self.SELECTED))

		if path.is_dir():
			self.__add_children__(path)

	def remove_item(self, uuid: str):
		if uuid == "":
			self.deselected.clear()
			return
		
		parent = self.dir_tree.parent(uuid)
		self.dir_tree.delete(uuid)
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
		self.dir_tree.set(uuid, column="Selected", value=new_symbol)
		self.__edit_child_selection__(uuid, select)

		parent_id = self.dir_tree.parent(uuid)
		self.view.after(10, self.__edit_parent_selection__, parent_id)

	
	def __edit_parent_selection__(self, uuid: str):
		original_selection = self.get_current_selection(uuid)
		children = self.dir_tree.get_children(uuid)
		all_selected = all (
			map (
				lambda c: self.get_current_selection(c) == self.SELECTED,
				children
			)
		)

		new_selection = self.SELECTED if all_selected else self.NOT_SELECTED
		self.dir_tree.set(uuid, column="Selected", value=new_selection)

		if original_selection == new_selection or uuid == "":
			self.view.after(10, self.__compute_deselected__, "")
		else:
			self.view.after(
				10, self.__edit_parent_selection__, 
				self.dir_tree.parent(uuid),
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
			for child in self.dir_tree.get_children(root):
				self.view.after(10, self.__compute_deselected__, child)

		return

	def get_all_children(self, root: str):
		children: list = list(self.dir_tree.get_children(root))

		for child in children:
			children.extend(self.dir_tree.get_children(child))

		return children

	def __edit_child_selection__(self, uuid: str, select: bool):
		new_symbol = self.SELECTED if select else self.NOT_SELECTED
		children = self.get_all_children(uuid)

		# Converted to list so that map is evaluated as map uses lazy evaluation
		list(map(lambda c: self.dir_tree.set(c, column="Selected", value=new_symbol), children))
		
		return

	def get_current_selection(self, uuid: str):
		return self.dir_tree.set(uuid, column="Selected")

	def __populate__(self, index):
		try:
			directory = self.directories[index]
		except IndexError:
			self.view.after(10, self.__populate_end_checker__)
			return
		
		path = pathlib.Path(directory)

		if not path.exists():
			self.directories.remove(directory)
			self.view.after(10, self.__populate__, index)
			return
	
		# Add base node with children if directory
		self.add_item(path, base=True)

		self.view.after(10, self.__populate__, index+1)

	def __populate_end_checker__(self):
		total_files = 0
		
		for dir in self.directories:
			total_files += tools.how_many_files_in(pathlib.Path(dir))

		for dir in self.removed:
			total_files -= len(tools.how_many_files_in(pathlib.Path(dir)))

		if total_files == len(self.get_all_children("")):
			self.populating = False
			for f in self.deselected:
				self.view.after(10, self.deselect, f)
			return

		self.view.after(10, self.__populate_end_checker__)

	def __add_children__(self, path: pathlib.Path):
		children = tools.descendants_of(path)

		for child in children:
			self.view.after(10, self.add_item, child)
		return