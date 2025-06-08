import os, shutil, sys
from globals import *
from packet_format import *

#INDIVIDUAL PEER INFORMATION STORED
peer_id: int = -1
peer_folder = f"./peer-{peer_id}"
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
 # - global_sender() to handle outgoing requests, incoming file transfers, and outgoing acks
 # - global_listener() to handle incoming requests, out going file transfers, and incoming acks
    #each will spawn thread to handle each new connection and have a handle_incoming/outgoing_peer() thread


 #TODO: Main should spawn multiple threads with request_file() to support multiple outgoing files?
def global_sender(filename: str):
    global peer_id
    if filename in known_files:
        source_peer = known_files[filename]
        source_peer_address = PEER_IP_REGISTRY[source_peer]  # Get the address of the source peer
        client_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_soc.connect((source_peer_address))

        
        print(f"[FileDownloader] Requesting file {filename} from Peer {source_peer}")
        request_datagram = build_file_request(filename)
        client_soc.sendto(request_datagram, source_peer_address)





#------------------------------------------------------------------
 #main server that handles all incoming tcp segments
    # can be incoming Requests
    # can be landing File Chunks       
def global_listener():
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.bind((PEER_IP_REGISTRY[peer_id]))
    soc.listen(5)  # Allow up to 5 queued connections

    while True:
        conn, addr = soc.accept()
        print(f"[GLOBALListener] Accepted connection from {addr}")
        # Spawn a new thread to handle this connection
        threading.Thread(target=handle_incoming_peer, args=(conn,), daemon=True).start()

EOF_SENTINEL = object() #cool 'flag' to pass into the downloads_queue to signal EOF suggested by Copilot
def handle_incoming_peer(conn: socket.socket):
    global peer_id    
    downloads_queue: queue.Queue[bytes | object] = queue.Queue() # contains message or EOF_SENTINEL
    requests_queue: queue.Queue[str] = queue.Queue() # contains filename
    acknowledged = threading.Event()
    acknowledged.clear()

    #spawn concurrent thread to process download_queue()
    threading.Thread(target=uploadThread, args=(conn, requests_queue, acknowledged), daemon=True).start()
    
    #spawn concurrent thread (no plural) to process requests_queue()
         # cannot spawn only one worker thread to process each request cause will cause problems with acknowledgements
    threading.Thread(target=processDownloadsThread, args=(conn, downloads_queue), daemon=True).start()

    while True:
        raw_message = conn.recv(1024) # need to be > FILE_CHUNK_SIZE
        if raw_message:
            msg_type = raw_message[0:1].decode('utf-8')
            if msg_type == 'R':  # incoming Request
                # needs to use addr to find requesting peer
                message = parse_file_request(raw_message)
                requests_queue.put(message)
            elif msg_type == 'T':  # outgoingFile transfer
                #can queue raw_message and have a concurrently running process_downloads() thread
                message = parse_file_transfer(raw_message)
                downloads_queue.put(message)
            elif msg_type == 'A':
                acknowledged.set()
            elif msg_type == 'E': #EOF
                downloads_queue.put(EOF_SENTINEL)
            else:
                print(f"Unexpected message type encountered, packets tossed.")

def uploadThread(conn: socket.socket, request_queue: queue.Queue[str], acknowleged: threading.Event):
    #only upload from local_files
    #there may be a mismatch between current peer local_files and other peers' known files
    #assuming no deletes, should be fine
    while True:
        try:
            filename, requesting_peer = request_queue.get()
            file_path = f"{peer_folder}/{filename}"
            file_chunks = utility_split_file(file_path)

            for chunk in file_chunks:
                chunk: bytes
                conn.sendall(build_file_transfer(chunk))

                acknowleged.wait() #blocking wait for ack response
                acknowleged.clear() #reset ack
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
    file_chunks.append()
    return file_chunks
    
def processDownloadsThread(conn: socket.socket, download_queue: queue.Queue[bytes | object]):
    while True:
        try:
            #download_queue has a queue of (raw_message, addr) intended for download on current peer
            chunk = download_queue.get(timeout=1) #waits 1 sec and raises Empty is empty
            if chunk == EOF_SENTINEL:
                local_files.add()
                #finish up local_files update and downloading file tracking

            write_to_file_BYTE(peer_folder, chunk)
            #send ack
            ack_message = build_ack_message(peer_id)
            conn.sendall(ack_message)

        except queue.Empty:
            continue 




#endregion File Transfer Function end
#=================================================================================================================

 # start() op on assignment desc.
 # path: the folder specific to the peer (may include local files)
def initialize():
    print("initalizing peer...")
    global peer_id, peer_folder
    
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
    threading.Thread(target=listen_for_broadcasts, name="BROADCASTListener", daemon=True).start()
    threading.Thread(target=periodic_broadcast, name="BROADCASTSender", daemon=True).start()
    print(f"Peer {peer_id} is now running and listening for broadcasts...")
    
    while True: 
        time.sleep(1)


if __name__ == "__main__":
    main()