import os, shutil, sys
from globals import *
from packet_format import *

#INDIVIDUAL PEER INFORMATION STORED
peer_id: int = -1
peer_folder: str
neighbours:set[int] = set()

known_files:dict[str, int] = {
    # "filename": source_peer_id
}
peer_files:dict[int, set[str]] = {
    # peer_id: set of filenames
}
#above two dicts are double dictionaries

local_files = set() #stores all COMPELETED FILENAMES


#=================================================================================================================
# region Broadcast Function
BROADCAST_ADDRESS = "255.255.255.255"
BROADCAST_PORT = 8000

def listen_for_broadcasts():
    global peer_id
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #allows socket resuse so all peers can listen on one port for broadcasts
        sock.bind(("", BROADCAST_PORT))

        while True:
            raw_datagram, addr = sock.recvfrom(1024) #addr should always be source_peer's address if want to use for updating registry or known peers
            source_peer, filename = parse_file_offer(raw_datagram)
            if raw_datagram and source_peer != peer_id:  # ignore own broadcasts
                if not filename in known_files:
                    known_files[filename] = source_peer
                    peer_files.setdefault(source_peer, set()).add(filename) #handles case set empty
                    print(f"[BROADCAST] Received broadcast offer that Peer {source_peer}: {filename}")

def periodic_broadcast():
    global peer_id
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True: # Broadcast every 5 seconds
            for filename in local_files:
                print(f"[BROADCAST] Broadcasting offer for {filename}")
                datagram = build_file_offer(peer_id, filename)
                sock.sendto(datagram, (BROADCAST_ADDRESS, BROADCAST_PORT))
            time.sleep(5) 

#endregion Broadcast Function end
#=================================================================================================================
# region File Transfer Function

 #requests filename and kills itself (outside/level of global listener)
 #connects to other peers' globalListener

 # NEW REFACTOR:
 # - global_requester() to handle outgoing requests, incoming file transfers, and outgoing acks
 # - global_listener() to handle incoming requests, out going file transfers, and incoming acks
    #each will spawn thread to handle each new connection and have a handle_incoming/outgoing_peer() thread
    #each handle_peer() function is a one-way connection to one peer

# global_requester() doesn't need to be a separate thread like global_listener()
# - will also reduce complexity
#-------------------------------GlobalRequester---------------------------------------
pending_request = False
def start_global_requester(filename: str):
    global peer_id

    
    while filename not in known_files: #busy wait until file known, potential issues
        print(f"[GLOBALRequester] busy waiting due to unknown peer to download '{filename}'")
        time.sleep(3) 
    source_peer = known_files[filename]
    source_peer_address = PEER_IP_REGISTRY[source_peer]  # Get the address of the source peer

    handle_outgoing_peer(source_peer_address, filename)
    #where to put unknown file logic? --might not be neccessary if broadcasts are handled right,
    # maybe busy wait a handle_outgoing_thread until file known?

EOF_SENTINEL = object() #cool 'flag' to pass into the downloads_queue to signal EOF suggested by Copilot
def handle_outgoing_peer(source_peer_address, filename: str):
    #request a file using build_file_request()
    # loop:
    #   wait for incoming file transfers
    #   send back acks

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect(source_peer_address)

    downloads_queue = queue.Queue()
    downloads_thread = threading.Thread(target=downloadsThread, args=(conn, downloads_queue, filename), daemon=True)
    downloads_thread.start()

    print(f"[Requester] Requesting file {filename} from Peer {known_files[filename]}") # outgoing request
    request = build_file_request(filename)
    conn.sendall(request)

    while True:
        raw_message = conn.recv(1024) # need to be > FILE_CHUNK_SIZE
        if raw_message:
            msg_type = raw_message[0:1].decode('utf-8')
            if msg_type == 'T':  # incoming File Transfer
                message = parse_file_transfer(raw_message)
                downloads_queue.put(message)
            elif msg_type == 'E':
                downloads_queue.put(EOF_SENTINEL)
                downloads_thread.join() #wait for child thread to die
                break
            else:
                print(f"[Requester] Unexpected message type encountered, packets tossed.")
    print(f"[Requester] Request for {filename} ended.")

def downloadsThread(conn: socket.socket,
                     download_queue: queue.Queue[bytes | object],
                       filename):
    while True:
        try:
            #download_queue has a queue of (raw_message, addr) intended for download on current peer
            chunk = download_queue.get(timeout=1) #waits 1 sec and raises Empty is empty
            if chunk == EOF_SENTINEL:
                local_files.add(filename)
                conn.close()
                break
                #finish up thread chain

            write_to_file_BYTE({os.path.join(peer_folder, filename)}, chunk)
            ack_message = build_ack_message(peer_id)
            conn.sendall(ack_message)
        except queue.Empty:
            continue 
    print(f"[downloadsThread] Completeted {filename} download.")


#-------------------------------GlobalListener-----------------------------------
 #main server that handles all incoming tcp segments
    # can be incoming Requests
    # can be landing File Chunks
    
def start_global_listener():
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.bind((PEER_IP_REGISTRY[peer_id]))
    soc.listen(5)  # Allow up to 5 queued connections

    while True:
        conn, addr = soc.accept()
        print(f"[GLOBALListener] Accepted connection from {addr}")
        # Spawn a new thread to handle this connection
        threading.Thread(target=handle_incoming_peer, args=(conn,), daemon=True).start()

def handle_incoming_peer(conn: socket.socket):
    global peer_id    
    requests_queue: queue.Queue[str] = queue.Queue() # contains filename
    acknowledged = threading.Event()
    acknowledged.clear()

    handle_err = threading.Event()

    #spawn concurrent thread for outgoing file transfer
    uploads_thread = threading.Thread(target=uploadsThread, args=(conn, requests_queue, acknowledged, handle_err), daemon=True)
    uploads_thread.start()
    
    try:
        while True:
            raw_message = conn.recv(1024) # need to be > FILE_CHUNK_SIZE
            if raw_message:
                msg_type = raw_message[0:1].decode('utf-8')
                if msg_type == 'R':  # incoming Request
                    message = parse_file_request(raw_message)
                    requests_queue.put(message)
                elif msg_type == 'A': # incoming Ack
                    acknowledged.set()
                else:
                    print(f"[Listener] Unexpected message type encountered, packets tossed.")
    except ConnectionResetError as e:
        print(f"[Listener] Socket error: {e}. Remote peer closed the connection abruptly.")
        print(f"[Listener] Closing handle for peer.")
        conn.close()
        handle_err.set()
        uploads_thread.join()


def uploadsThread(conn: socket.socket,
                   request_queue: queue.Queue[str],
                    acknowleged: threading.Event,
                    handle_err: threading.Event):
    #only upload from local_files
    #there may be a mismatch between current peer local_files and other peers' known files
    #assuming no deletes, should be fine
    while True:
        try:
            if handle_err.is_set():
                break
            filename = request_queue.get()
            file_path = os.path.join(peer_folder, filename)
            file_chunks = utility_split_file(file_path)

            for chunk in file_chunks:
                chunk: bytes
                conn.sendall(build_file_transfer(chunk))

                while not acknowleged.is_set():
                    acknowleged.wait(timeout=3) #blocking wait for ack response
                    conn.sendall(build_file_transfer(chunk))
                    print(f"[uploadThread] ACK Timeout retransmitting chunk...")
                    if handle_err.is_set():
                        break
                acknowleged.clear() #reset ack

            #send EOF
            conn.sendall(build_file_transfer_EOF())
        except queue.Empty:
            continue 

def utility_split_file(filepath):
    file_chunks = list()
    try:
        with open(filepath, 'rb') as file: 
            while True:
                chunk = file.read(FILE_CHUNK_SIZE)  
                if not chunk:
                    break
                file_chunks.append(chunk)
        print(f"File '{filepath}' processed into {len(file_chunks)} chunks.")
    except IOError as e:
        print(f"Error reading file '{filepath}': {e}")
    return file_chunks


#endregion File Transfer Function end
#=================================================================================================================

 # start() op on assignment desc.
 # path: the folder specific to the peer (may include local files)
def initialize():
    print("initalizing peer...")
    global peer_id, peer_folder
    peer_folder = f"./peer-{peer_id}"
     #reset existing peer folder
    if os.path.exists(peer_folder):
        shutil.rmtree(peer_folder)
    os.makedirs(peer_folder, exist_ok=True) 
    
     # copy initial files (section of code provided by Github Copilot)
    template_folder = f"./initial_peer_folders/peer-{peer_id}"
    if os.path.exists(template_folder):
        for filename in os.listdir(template_folder):
            src = os.path.join(template_folder, filename)
            dst = os.path.join(peer_folder, filename)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                local_files.add(filename)
        print(f"Initial files copied from {template_folder}.")
     # end of Github Copilot

def main(): # args: peerID 
    global peer_id, neighbours

    if len(sys.argv) > 1:
        peer_id = int(sys.argv[1])
        if peer_id in PEER_GRAPH:
            neighbours.add(PEER_GRAPH[peer_id])
            print(f"Peer ID {peer_id} connected.")
        else:
            print(f"Peer ID {peer_id} not currently in hardcoded list.")
    else:
        print("Usage: python peer.py <peer_id>")
        sys.exit(1)
    initialize()

    broadcast_listener = threading.Thread(target=listen_for_broadcasts, daemon=True)
    broadcast_listener.start()
    broadcast_sender = threading.Thread(target=periodic_broadcast, daemon=True)
    broadcast_sender.start()
    print(f"Peer {peer_id} is now running and listening for broadcasts...")

    global_listener = threading.Thread(target=start_global_listener, daemon=True)
    global_listener.start()

    if peer_id == 1:
        filename:str = "piratedGame"
        global_requester = threading.Thread(target=start_global_requester, args=(filename,), daemon=True)
        global_requester.start() 

    while True: 
        time.sleep(1)


if __name__ == "__main__":
    main()