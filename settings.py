"""
For all Settings related stuff
Includes:
1. Loading and Saving settings
2. Settings edittor UI and functionality
3. Loading different config files during runtime
"""

import json
import pathlib
import socket

settings: dict = {}
"""
These settings will always be setand can be 
retrieved by simply using settings["SETTING"]:
1. Host
2. Port
3. TimeoutLength
4. RemoteUpdateInterval
5. SSHPort
"""


def load():
    global settings
    settings = {}

    if pathlib.Path("backup.json").exists():
        settings_file = open("backup.json", mode="r")
    else:
        settings_file = open("backup_json", mode="x")
    settings_file.close()

    with open("settings.json", mode="r") as settings_file:
        settings = json.load(settings_file)

    settings["Port"] = settings.get("Port") or 9999
    settings["Host"] = settings.get("Host")
    if settings.get("UseHostname"):
        try:
            settings["Host"] = socket.gethostbyname(settings.get("Hostname"))
        except socket.gaierror:
            print(settings)
            settings["Host"] = "socket.gaierror"

    settings["TimeoutLength"] = settings.get("TimeoutLength") or 300
    settings["RemoteUpdateInterval"] = settings.get("TimeoutLength") or 5
    settings["SSHPort"] = settings.get("SSHPort") or 22

    return


def save():
    with open("settings.json", mode="w") as settings_file:
        json.dump(settings, settings_file)

    return

