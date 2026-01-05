import json
import socket
from math import ceil, log
from typing import Any, Literal, TypedDict, override

PREFIX_MAX = 1152921504606846975  # 0xFFFFFFFFFFFFFFF in decimal
CHUNK_SIZE = 4098


class Request(TypedDict):
    length: int
    body: str
    sender: str
    reciever: str
    metadata: dict[str, Any]


class SendingError(Exception):
    """
    Raised when there is a problem with any of the send functions
    """

    def __init__(self, message=""):
        if message == "":
            message = "UNABLE TO SEND MESSAGE"
        self.message = message
        super().__init__(message)

    @override
    def __str__(self):
        return self.message


class BackupSocket:
    def __init__(
        self, socket_type: Literal["server", "client"] = "client", init_socket=True
    ):
        self.socket: socket.socket
        if init_socket:
            self.init_socket()
        self.socket_type = socket_type
        if self.socket_type == "server":
            self.client_list = {}

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return

    def bind(self, adress):
        if self.socket_type == "client":
            return
        self.socket.bind(adress)

    def accept(self):
        if self.socket_type == "client":
            return
        client_socket, client_addr = self.socket.accept()
        client = BackupSocket(socket_type="client", init_socket=False)
        client.socket = client_socket
        self.client_list[client_addr] = client
        return client, client_addr

    def connect(self, address):
        self.socket.connect(address)

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def send(self, request: Request):
        plaintext_message = json.JSONEncoder().encode(request)
        encoded_message = plaintext_message.encode(encoding="utf-8")

        total_bytes_sent = 0
        message_length = len(encoded_message)
        while total_bytes_sent != message_length:
            bytes_sent = self.socket.send(encoded_message[total_bytes_sent:])
            if bytes_sent == 0:
                raise SendingError

            total_bytes_sent += bytes_sent

    def send_prefix(self, request: Request):
        plaintext_message = json.JSONEncoder().encode(request)
        encoded_message = plaintext_message.encode(encoding="utf-8")
        message_length = len(encoded_message)
        if message_length > PREFIX_MAX:
            raise SendingError("Message length is over PREFIX_MAX")

        prefix_length = ceil(log(message_length, 16))
        if self.socket.send(hex(prefix_length).encode()) == 0:
            raise SendingError

        total_bytes_sent = 0
        prefix = hex(message_length).encode()
        while total_bytes_sent != prefix_length:
            bytes_sent = self.socket.send(prefix[total_bytes_sent:])
            if bytes_sent == 0:
                raise SendingError

            total_bytes_sent += bytes_sent

        total_bytes_sent = 0
        while total_bytes_sent != message_length:
            bytes_sent = self.socket.send(encoded_message[total_bytes_sent:])
            if bytes_sent == 0:
                raise SendingError

            total_bytes_sent += bytes_sent

    def send_delim(self, request: Request):
        plaintext_message = json.JSONEncoder().encode(request)
        plaintext_message = f"{plaintext_message}\0"
        encoded_message = plaintext_message.encode(encoding="utf-8")

        message_length = len(encoded_message)
        total_bytes_sent = 0
        while total_bytes_sent != message_length:
            bytes_sent = self.socket.send(encoded_message[total_bytes_sent:])
            if bytes_sent == 0:
                raise SendingError

            total_bytes_sent += bytes_sent

    def recieve(self, length: int) -> Request:
        encoded_message = b""

        total_bytes_recieved = 0
        while total_bytes_recieved != length:
            message_buffer = self.socket.recv(length - total_bytes_recieved)
            encoded_message = b"".join([encoded_message, message_buffer])

        plaintext_message = encoded_message.decode(encoding="utf-8")
        request: Request = json.JSONDecoder().decode(plaintext_message)

        return request

    def recieve_prefix(self) -> Request:
        prefix_length = int(self.socket.recv(1).decode(encoding="utf-8"), base=16)

        encoded_prefix = b""
        total_bytes_recieved = 0
        while total_bytes_recieved != prefix_length:
            message_buffer = self.socket.recv(prefix_length - total_bytes_recieved)
            total_bytes_recieved += len(message_buffer)
            encoded_prefix = b"".join([encoded_prefix, message_buffer])

        message_length = int(encoded_prefix.decode(encoding="utf-8"), base=16)
        encoded_message = b""
        total_bytes_recieved = 0
        while total_bytes_recieved != message_length:
            message_buffer = self.socket.recv(message_length - total_bytes_recieved)
            total_bytes_recieved += len(message_buffer)
            encoded_message = b"".join([encoded_message, message_buffer])

        plaintext_message = encoded_message.decode(encoding="utf-8")
        request: Request = json.JSONDecoder().decode(plaintext_message)

        return request

    def recieve_delim(self, delimiter: bytes = b"\0") -> Request:
        encoded_message = b""

        while True:
            message_buffer = self.socket.recv(CHUNK_SIZE)
