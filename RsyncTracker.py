import concurrent
import concurrent.futures
import datetime
import pathlib
import platform
import subprocess
from tkinter import *
from tkinter import ttk, messagebox

import misc_tools as tools

class RsyncTracker:
	def __init__(self, parent: Widget, HOST: str, rsync_command: list[str], total_to_backup: int):
		self.total_to_backup = total_to_backup
		self.rsync_command = rsync_command
		self.HOST = HOST
		
		self.window = Toplevel(parent)
		self.window.resizable(width=False, height=False)
		self.window.title("Backing Up...")
		progress_frame = ttk.Frame(self.window)

		self.backed_up = IntVar()
		self.progress_bar = ttk.Progressbar(
			progress_frame, orient="horizontal", length=500, mode="determinate",
			maximum=self.total_to_backup, variable=self.backed_up
		)

		self.backup_item = StringVar(value="-")
		backup_item_label = ttk.Label(progress_frame, textvariable=self.backup_item, justify="left")

		self.backup_speed = StringVar(value="0 b/s")
		backup_speed_label = ttk.Label(progress_frame, textvariable=self.backup_speed, justify="left")

		progress_frame.grid(column=0, row=0, padx=5, pady=5)
		self.progress_bar.grid(column=0, row=1, columnspan=3, sticky=(N, S, E, W), padx=5, pady=5)
		backup_item_label.grid(column=0, row=0, sticky=(S, W), padx=5, pady=5)
		backup_speed_label.grid(column=0, row=2, sticky=(S, W), padx=5, pady=5)
		
		self.window.update_idletasks()
		self.start_rsync()
		
	def start_rsync(self):
		self.process = subprocess.Popen(
			self.rsync_command, text=True, encoding="utf-8", stdin=subprocess.PIPE,
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
		)

		self.poller()
		self.latest_lines = []
		self.read_output()
		self.window.after(10, self.update_ui, datetime.datetime.now())
		return

	def exit(self):
		self.window.withdraw()
		messagebox.showinfo(
			title="Backup Completed",
			message=f"Successfully backed up files to {self.HOST}"
		)
		self.window.event_generate("<<RsyncCompleted>>")

	# TODO: Make the current file actually the current file
	def update_ui(self, last_backup: datetime.datetime, done: bool=False):
		if self.latest_lines != []:
			info = self.parse_output(self.latest_lines)

			now = datetime.datetime.now()
			time_between_backup = now - last_backup
			time_between_backup = time_between_backup.total_seconds()
			sending_speed = info["TotalSent"] // time_between_backup
			sending_speed = tools.human_readable_file_size(sending_speed)

			self.backup_speed.set(f"{sending_speed}/s")
			self.backup_item.set(f"{info["CurrentFile"]} ({self.backed_up.get()} / {self.total_to_backup})")
			self.backed_up.set(self.backed_up.get() + info["AmountBackedUp"])
			
			if not done:
				self.latest_lines = []
				self.read_output()

		if done:
			self.backed_up.set(self.total_to_backup)
			self.exit()
			return

		self.window.after(50, self.update_ui, last_backup, not self.running)

	def parse_output(self, lines: list[str]):
		info = {}
		current_file = self.get_file_sent(lines[-1])
		if platform.system() == "Windows":
			current_file = tools.rsync_posix_to_win(current_file)

		current_file = tools.pretty_path(pathlib.Path(current_file))

		total_sent = sum(map(self.get_bytes_sent, lines))

		info["CurrentFile"] = current_file
		info["AmountBackedUp"] = len(lines)
		info["TotalSent"] = total_sent

		return info
	
	def get_file_sent(self, line: str):
		return "|".join(line.split(sep="|")[1:-1])
	
	def get_bytes_sent(self, line: str):
		return int(line.split(sep="|")[-1])
	
	def read_output(self):
		executor = concurrent.futures.ThreadPoolExecutor()
		future = executor.submit(self.__read_output__)

		self.window.after(10, tools.non_blocking_executor_shutdown, self.window, executor, future)
	
	def __readlines__(self):
		yield self.process.stdout.readline()

	def __read_output__(self):	
		if not self.running:
			return
		
		new_lines = []
		for line in self.__readlines__():
			if line == "":
				break
			new_lines.append(line.strip())

		self.latest_lines = new_lines
		return
	
	def poller(self):
		self.running = self.process.poll() == None
		self.window.after(10, self.poller)