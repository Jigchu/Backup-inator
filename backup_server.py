import json
import platform
import socket_io as sio
import socket

def main():
	port = 9999
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	if platform.system() != "Windows":
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	server.bind(("", port))
	server.listen(1)	# TODO: Change when I add silmultaneous connections

	while True:
		client, client_address = server.accept()
		command = sio.recv_delim(client)

		match command:
			case "RequestBackupConf":
				msg = load_backup_conf()
				sio.send(client, msg, type="delim")
			case "UpdateBackupConf":
				update_backup_conf(client, client_address[0])
		
		client.shutdown(socket.SHUT_RDWR)
		client.close()

	return

def load_backup_conf():
	try:
		backup_json = open("backup.json", mode="r")
	except FileNotFoundError:
		backup_json = open("backup.json", mode="x")
	finally:
		backup_json.close()

	backup_conf = ""
	with open("backup.json", mode="r") as backup_json:
		backup_conf = "".join([line for line in backup_json])

	return backup_conf

def update_backup_conf(client: socket.socket, client_ip: str):
	json_string = sio.recv_delim(client, client_ip)
	backup_conf = json.loads(json_string)

	with open("backup.json", mode="w") as backup_json:
		json.dump(backup_conf, backup_json)
	
	return

if __name__ == "__main__":
	main()