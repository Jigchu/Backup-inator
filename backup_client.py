from tkinter import *
from tkinter import messagebox

import settings
from BackupWindow import BackupWindow


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
        if settings.settings["Host"] == "socket.gaierror":
            messagebox.showerror(
                title="getaddrinfo failed",
                message="Failed to get the server's IP",
                detail="Please check if the server exists",
            )

        if settings.settings["Host"] == "no hostname":
            messagebox.showerror(
                title="No hostname in settings",
                message="No hostname listed in settings",
                detail="Please enter a hostname into settings",
            )

        # TODO: Let them type in their username instead of just the error message
        if settings.settings["Username"] == "no username":
            messagebox.showerror(
                title="No username in settings",
                message="No username listed in settings",
                detail="Please enter a username into settings",
            )

        # TODO: Check if any setting var is missing and set it up

    def run(self):
        self.root.mainloop()


def main():
    settings.load()
    client_win = ClientWindow()
    client_win.run()


if __name__ == "__main__":
    main()
