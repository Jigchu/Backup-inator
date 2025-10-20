import json
import socket
from base64 import encode
from math import ceil, log
from typing import Any, TypedDict, override

PREFIX_MAX = 1152921504606846975  # 0xFFFFFFFFFFFFFFF in decimal
CHUNK_SIZE = 4098


class Request(TypedDict):
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


def send(client: socket.socket, request: Request):
    plaintext_message = json.JSONEncoder().encode(request)
    encoded_message = plaintext_message.encode(encoding="utf-8")

    total_bytes_sent = 0
    message_length = len(encoded_message)
    while total_bytes_sent != message_length:
        bytes_sent = client.send(encoded_message[total_bytes_sent:])
        if bytes_sent == 0:
            raise SendingError

        total_bytes_sent += bytes_sent


def send_prefix(client: socket.socket, request: Request):
    plaintext_message = json.JSONEncoder().encode(request)
    encoded_message = plaintext_message.encode(encoding="utf-8")
    message_length = len(encoded_message)
    if message_length > PREFIX_MAX:
        raise SendingError("Message length is over PREFIX_MAX")

    prefix_length = ceil(log(message_length, 16))
    if client.send(hex(prefix_length).encode()) == 0:
        raise SendingError

    total_bytes_sent = 0
    prefix = hex(message_length).encode()
    while total_bytes_sent != prefix_length:
        bytes_sent = client.send(prefix[total_bytes_sent:])
        if bytes_sent == 0:
            raise SendingError

        total_bytes_sent += bytes_sent

    total_bytes_sent = 0
    while total_bytes_sent != message_length:
        bytes_sent = client.send(encoded_message[total_bytes_sent:])
        if bytes_sent == 0:
            raise SendingError

        total_bytes_sent += bytes_sent


def send_delim(client: socket.socket, request: Request):
    plaintext_message = json.JSONEncoder().encode(request)
    plaintext_message = f"{plaintext_message}\0"
    encoded_message = plaintext_message.encode(encoding="utf-8")

    message_length = len(encoded_message)
    total_bytes_sent = 0
    while total_bytes_sent != message_length:
        bytes_sent = client.send(encoded_message[total_bytes_sent:])
        if bytes_sent == 0:
            raise SendingError

        total_bytes_sent += bytes_sent


def recieve(client: socket.socket, length: int) -> Request:
    encoded_message = b""

    total_bytes_recieved = 0
    while total_bytes_recieved != length:
        message_buffer = client.recv(length - total_bytes_recieved)
        encoded_message = b"".join([encoded_message, message_buffer])

    plaintext_message = encoded_message.decode(encoding="utf-8")
    request: Request = json.JSONDecoder().decode(plaintext_message)

    return request


def recieve_prefix(client: socket.socket) -> Request:
    prefix_length = int(client.recv(1).decode(encoding="utf-8"), base=16)

    encoded_prefix = b""
    total_bytes_recieved = 0
    while total_bytes_recieved != prefix_length:
        message_buffer = client.recv(prefix_length - total_bytes_recieved)
        total_bytes_recieved += len(message_buffer)
        encoded_prefix = b"".join([encoded_prefix, message_buffer])

    message_length = int(encoded_prefix.decode(encoding="utf-8"), base=16)
    encoded_message = b""
    total_bytes_recieved = 0
    while total_bytes_recieved != message_length:
        message_buffer = client.recv(message_length - total_bytes_recieved)
        total_bytes_recieved += len(message_buffer)
        encoded_message = b"".join([encoded_message, message_buffer])

    plaintext_message = encoded_message.decode(encoding="utf-8")
    request: Request = json.JSONDecoder().decode(plaintext_message)

    return request


def recieve_delim(client: socket.socket, delimiter: bytes = b"\0") -> Request:
    encoded_message = b""

    while True:
        message_buffer = client.recv(CHUNK_SIZE)
