"""
All recieve and send functions use utf-8 encoding
Default delimiting character is \0
Prefixed Length is in Base-16 and is limited to one letter
The max length of a prefixed message is 15 characters
Due to the Global Variable of PREV_CHUNK, all socket IO using
delimited messages are not thread-safe
"""

import socket
from threading import Lock
from typing import Literal, override

PREV_CHUNK: dict[str, bytes] = {}
DELIM_LOCK = Lock()


def send(
    sock: socket.socket,
    unprocessed_msg: str,
    type: Literal["delim", "prefix", None] = None,
):
    msg = unprocessed_msg.encode("utf-8")
    msg_len = len(msg)

    if type == "delim":
        msg += "\0".encode("utf-8")
        msg_len += 1
    elif type == "prefix":
        prefix = hex(msg_len)[2].encode("utf-8")
        msg = prefix + msg
        msg_len += 1

    total_sent = 0
    while total_sent < msg_len:
        bytes_sent = sock.send(msg[total_sent:])
        if bytes_sent == 0:
            raise SendingError
        total_sent += bytes_sent
    return


def recv(sock: socket.socket, bufsize: int):
    msg_chunks = []
    bytes_recv = 0
    while bytes_recv < bufsize:
        chunk = sock.recv(min(bufsize - bytes_recv, 4096)).strip()
        if chunk == b"":
            return ""
        bytes_recv += len(chunk)
        msg_chunks.append(chunk)
    msg = b"".join(msg_chunks)
    msg = msg.decode("utf-8")
    return msg


# A recieve function that uses delimiters to indicate end of message
def recv_delim(sock: socket.socket, ip: str):
    global PREV_CHUNK
    DELIM_LOCK.acquire()
    prev_chunk = PREV_CHUNK.get(ip)
    if prev_chunk != b"":
        PREV_CHUNK[ip] = b""
    DELIM_LOCK.release()

    msg_chunks = []
    if prev_chunk not in [None, b""]:
        msg_chunks.append(prev_chunk)

    delim = False
    while not delim:
        chunk = sock.recv(4096)
        if chunk == b"":
            break
        for index, letter in enumerate(chunk):
            if letter == 0:
                delim = True
                DELIM_LOCK.acquire()
                PREV_CHUNK[ip] = chunk[index + 1 :]
                DELIM_LOCK.release()
                chunk = chunk[:index]
                break
        msg_chunks.append(chunk)
    msg = b"".join(msg_chunks)
    msg = msg.decode("utf-8")
    return msg


# A recieve function that uses prefixed metadata to get message length
def recv_prefix(sock: socket.socket):
    msg_len = int(sock.recv(1), base=16)
    return recv(sock, msg_len)


class SendingError(Exception):
    """
    Raised by send when the return value of socket.send is 0
    """

    def __init__(self, message=""):
        if message == "":
            message = "UNABLE TO SEND MESSAGE"
        self.message = message
        super().__init__(message)

    @override
    def __str__(self):
        return self.message

