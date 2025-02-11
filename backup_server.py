import platform
import socket_io as sio
import socket

def read_backup_conf():
	backup_dir = ["None"]
	try:
		with open("backup.conf") as backup_conf:
			backup_dir = [line.strip() for line in backup_conf]
	except FileNotFoundError:
		pass

	return backup_dir

def main():
	port = 9999
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	if platform.system() != "Windows":
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	server.bind(("", port))
	server.listen(1)	# TODO: Change when I add silmultaneous connections

	while True:
		client, client_address = server.accept()
		command = sio.recv(client, 5)

		match command:
			case "ReqBC":
				backup_dir = read_backup_conf()
				sio.send(client, "\n".join(backup_dir), type="delim")
				client.recv(1).decode("utf-8")
				client.close()

	return

if __name__ == "__main__":
	main()