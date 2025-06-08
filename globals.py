import socket, time, sys, queue, threading
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple as namedTuple

LOCALHOST = "localhost"

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






def create_socket(host, port):
    while (True):
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.connect((host, port))
            print(f"[CLIENT] Client socket created on {port}.")
            return soc
        except ConnectionRefusedError:
            print(f"Client socket on {port} not ready to recieve. Retrying...")
            time.sleep(2)
            continue
        except:
            print("Unexpected Connection Error to", port)
            sys.exit()

def handle_client(conn, addr, queueToAddTo : queue.Queue):
    try:
        while (True):
            data = conn.recv(1024).decode()
            if not data:
                time.sleep(1)
            print(f"[{threading.Thread.getName()}][{addr}] Received: {data}")
            queueToAddTo.put(data) ##causing problem
    except Exception as e:
        print(f"[{threading.Thread.getName()}] UnexpectedError while handling {addr}: {e}")
    finally:
        conn.close() 

 # creates a handler thread (MainSeeder) for incoming connections
 # child threads are called SeederThread)
def start_seeding(home_port, queueToAddTo : queue.Queue):
    try:
        #print(f"[DEBUG] Creating server socket on port {port}...")
        with ThreadPoolExecutor(thread_name_prefix="SeederThread") as ThreadManager:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reusing the port
            try:
                server.bind((LOCALHOST, home_port))
                print(f"[SeederMain] Successfully bound to {LOCALHOST}:{home_port}")
            except Exception as e:
                print(f"[SeederMain][ERROR] Failed to bind to {LOCALHOST}:{home_port}. Error: {e}")
                sys.exit()

            server.listen()
            print(f"[SeederMain] Router is listening on {LOCALHOST}:{home_port}")
            while True:
                conn, addr = server.accept() 
                print(f"[SeederMain] New Connection {addr} connected")
                ThreadManager.submit(handle_client, conn, addr, queueToAddTo)

    except Exception as e:
        print(f"UnexpectedError: {e}")
    finally:
        server.close() 


def write_to_file_BYTE(path, data: bytes):
    try:
        out_file = open(path, "ab")
    except FileNotFoundError:
        out_file = open(path, "wb") 

    out_file.write(data)
    out_file.close()