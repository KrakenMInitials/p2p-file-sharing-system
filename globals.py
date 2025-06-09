import socket, time, sys, queue, threading
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple as namedTuple

LOCALHOST = "localhost"

FILE_CHUNK_SIZE = 1024 

 # will be replaced by central_server later
PEER_IP_REGISTRY ={
    1: (LOCALHOST, 5001),
    2: (LOCALHOST, 5002),
    3: (LOCALHOST, 5003),
    4: (LOCALHOST, 5004),
    5: (LOCALHOST, 5005),
}

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