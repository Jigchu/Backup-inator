from tkinter import *
from tkinter import ttk, filedialog
import pathlib

root = Tk()
list = Listbox(root)
list.grid(column=1, row=1, sticky="NSEW")
def add_file():
	dir = filedialog.askopenfilename(parent=root, title="Add File", initialdir=pathlib.Path.cwd().as_posix())
	list.insert(0, dir)
button = ttk.Button(root, command=add_file)
button.grid(column=1, row=2)
root.columnconfigure(1, weight=1)
root.mainloop()