"""
For all runtime global variables including settings etc
"""

import json
import socket

settings: dict = {}
HOST: str = ""
port: int = -1

def load():
	global settings, HOST, port
	# TODO: Preset timoutlength setting when not present
	# Load the settings using JSON because why not
	settings = {}
	# TODO: Check if the settings json even exists
	with open("settings.json", mode="r") as settings_file:
		settings = json.load(settings_file)

	port = settings.get("port") or 9999

	if settings.get("UseHostname"):
		hostname = settings.get("Hostname")
		if hostname == None:
			HOST = None
			return
		
		try:
			HOST = socket.gethostbyname(hostname)
		except socket.gaierror:
			HOST = "socket.gaierror"
	else:
		HOST = settings.get("Server_IP")

	return