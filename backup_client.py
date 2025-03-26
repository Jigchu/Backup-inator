from tkinter import *
from tkinter import messagebox

from BackupWindow import BackupWindow
import runtime_globals as globals

class ClientWindow:
	def __init__(self):
		self.root = Tk()

		self.root.option_add("*tearOff", FALSE)
		self.root.title("Backup-inator")
		self.root.minsize(width=800, height=400)

		self.root.columnconfigure(index=0, weight=1)
		self.root.rowconfigure(index=0, weight=1)

		menubar = Menu(self.root)
		self.root["menu"] = menubar

		self.backup_win = BackupWindow(self.root, menubar)
		
		if globals.HOST == "socket.gaierror":
			messagebox.showerror(
				title="getaddrinfo failed",
				message="Failed to get the server's IP",
				detail="Please check if the server exists"
			)
			
		# TODO: Check if any setting var is missing and set it up
	
	def run(self):
		self.root.mainloop()

def main():
	globals.load()
	client_win = ClientWindow()
	client_win.run()

if __name__ == "__main__":
	main()