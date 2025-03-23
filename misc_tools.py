"""
For all the functions that are used in multiple files but are
too specific to be in their own standalone file
"""

import concurrent.futures
import datetime
import math
import pathlib
import platform
from tkinter import *
from typing import Literal

def non_blocking_executor_shutdown(widget: Widget | Tk, executor: concurrent.futures.Executor, future: concurrent.futures.Future):
	if future.done():
		executor.shutdown()
		return
	widget.after(10, non_blocking_executor_shutdown, widget, executor, future)

# Function that converts window paths to POSIX paths that are readable by rsync
def win_to_rsync_readable_posix(path: pathlib.Path):
	win_as_posix = path.as_posix()
	win_as_posix = win_as_posix.split(sep="/")
	win_as_posix[0] = "/" + win_as_posix[0][:-1].lower()
	win_as_posix = "/".join(win_as_posix)

	if path.is_dir():
		win_as_posix += "/"

	return win_as_posix

# Converts rsync filename output to windows
def rsync_posix_to_win(path: str):
	posix_as_win = path.split(sep="/")
	posix_as_win[0] = posix_as_win[0].upper() + ":"
	posix_as_win = "\\".join(posix_as_win)

	return posix_as_win

# Removes drive letters and user paths, leaving just the relevant segments
def pretty_path(path: pathlib.Path):
	drive_str = path.drive
	user_path = pathlib.Path("~").expanduser()
	user_str = pathlib.Path("~").expanduser().as_posix().lower()
	file_sep = "\\" if platform.system() == "Windows" else "/"
	path_parts = path.parts

	if path.as_posix().lower().startswith(user_str):
		path_parts = path_parts[len(user_path.parts):]
	elif drive_str != "" and path.as_posix().startswith(drive_str):
		path_parts = path_parts[1:]

	pretty_str = file_sep.join(path_parts)
	if path.is_dir():
		pretty_str += file_sep

	return pretty_str

def datetime_to_ISO8601(when: datetime.datetime):
	return when.strftime("%Y-%m-%dT%H:%M:%S")

# Converts bytes into human readable sizes
def human_readable_file_size(size: int, unit: Literal["B", "iB"]="B"):
		base = 1000 if unit == "B" else 1024
		prefixes = "kMGTPEZ"

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

# Includes directories and files
def how_many_files_in(dir: pathlib.Path):
	if dir.is_file():
		return 1
	
	return len(list(dir.glob("**/*")))

def size_of(file: pathlib.Path):
		if file.is_dir():
			return sum(f.stat().st_size for f in file.glob('**/*') if f.is_file())
		elif file.is_file():
			return file.stat().st_size
		
		return -1