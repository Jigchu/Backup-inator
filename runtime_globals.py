"""
For all runtime global variables including settings etc
"""

import json
import socket

settings: dict = {}
HOST: str = ""
port: int = -1
TIMEOUT_LENGTH = 300

def load():
	global settings, HOST, port, TIMEOUT_LENGTH
	
	settings = {}

	try:
		settings_file = open("settings.json", mode="r")
	except FileNotFoundError:
		settings_file = open("settings.json", mode="x")
	finally:
		settings_file.close()

	with open("settings.json", mode="r") as settings_file:
		settings = json.load(settings_file)

	TIMEOUT_LENGTH = settings.get("TimeoutLength") or 300
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