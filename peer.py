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

 #requests filename and kills itself (outside of global listener)
def request_file(client_soc: socket.socket, filename: str):
    global peer_id
    if filename in known_files:
        source_peer = known_files[filename]
        source_peer_address = PEER_IP_REGISTRY[source_peer]  # Get the address of the source peer
        print(f"[FileDownloader] Requesting file {filename} from Peer {source_peer}")
        request_datagram = build_file_request(filename)
        client_soc.sendto(request_datagram, source_peer_address)

 #handles all incoming tcp segments
    # can be incoming Requests
    # can be landing File Chunks          
def global_listener():
    global peer_id    
    downloads_queue = queue.Queue() # contains Tuples of (raw_segment, addr)

    acknowledged = threading.Event()
    acknowledged.clear()

    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.bind(("", BROADCAST_PORT))  # Bind to the broadcast port

    #spawn concurrent thread to process download_queue()

    while True:
        raw_segment, addr = soc.recvfrom(1024) # = 
        if raw_segment:
            msg_type = raw_segment[0:1].decode('utf-8')
            if msg_type == 'R':  # incoming Request
                # spawns a upload thread that will send chunks of data to requesting peer
                # needs to use addr to find requesting peer
            elif msg_type == 'T':  # File transfer
                #can queue raw_segment and have a concurrently running process_downloads() thread
                downloads_queue.put(raw_segment, addr)
            else:
                print(f"Unexpected message type encountered, packets tossed.")

def uploadThread(filename: str, source_peer: int, soc: socket.socket, acknowleged: threading.Event):
    #only upload from local_files
    #there may be a mismatch between current peer local_files and other peers' known files
    #assuming no deletes, should be fine
    file_path = f"{peer_folder}/{filename}"
    
    #break down file in filepath into chunks

    for file_chunk in file:
        file_chunk: bytes
        soc.sendall(build_file_transfer(file_chunk))

        acknowleged.wait() #blocking wait for ack response
        acknowleged.clear() #reset ack
    

def processDownloadsThread(download_queue: queue.Queue, soc: socket.socket):
    while True:
        try:
            #download_queue has a queue of (raw_segment, addr) intended for download on current peer
            raw_segment, addr = download_queue.get(timeout=1)
            write_to_file_BYTE(peer_folder, parse_file_transfer(raw_segment))
            #send ack

            ack_message = build_ack_message(peer_id)
            soc.sendall(ack_message)

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