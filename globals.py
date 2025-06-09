import socket, time, sys, queue, threading
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple as namedTuple

LOCALHOST = "localhost"
SERVER_ADDRESS = (LOCALHOST, 5000)

FILE_CHUNK_SIZE = 1024 

 # will be replaced by central_server later

PEER_GRAPH = {       
    1: (3),
    2: (1, 2, 5),
    3: (3, 4),
    5: (3), 
}

def write_to_file_BYTE(path, data: bytes):
    try:
        out_file = open(path, "ab")
    except FileNotFoundError:
        print(f"New {path} created.")
        out_file = open(path, "wb") 

    out_file.write(data)
    out_file.close()