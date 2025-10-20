"""
A program to export backups created by Backup-inator
This is only meant to be used on the device running backup_server.py
"""

import pathlib
import sys


def main(dest: pathlib.Path):
    backup_src = pathlib.Path("~/Backup/").resolve()

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: backups_exporter.py [FULL DESTINATION PATH]")

    dest = pathlib.Path(sys.argv[1].strip())
    if not dest.exists():
        print(f"{dest} does not exist!")

    main(dest)
