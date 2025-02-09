"""
For all the functions that are used in multiple files but are
too specific to be in their own standalone file
"""

import concurrent.futures
import pathlib
from tkinter import *


def non_blocking_executor_shutdown(widget: Widget | Tk, executor: concurrent.futures.Executor, future: concurrent.futures.Future):
	if future.done():
		executor.shutdown()
		return
	widget.after(10, non_blocking_executor_shutdown, executor, future)

# Function that converts window paths to POSIX paths that are readable by rsync
def win_to_rsync_readable_posix(path: pathlib.Path) -> str:
	win_as_posix = path.as_posix()
	win_as_posix = win_as_posix.split(sep="/")
	win_as_posix[0] = "/" + win_as_posix[0][0].lower()
	win_as_posix = "/".join(win_as_posix)

	return win_as_posix