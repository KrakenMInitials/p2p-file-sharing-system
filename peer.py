import os, shutil, sys
from globals import *
from packet_format import *

#IMPORT INDIVIDUAL PEER INFORMATION STORED
peer_id: int = -1
neighbours:set[int] = set()

known_files:dict[str, int] = {
    # "filename": source_peer_id
}
peer_files:dict[int, set[str]] = {
    # peer_id: set of filenames
}
#above two dicts are double dictionaries



#=================================================================================================================
# region Broadcast Function start
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
            if raw_datagram and source_peer != peer_id:  # Ignore own broadcasts
                if not filename in known_files:
                    known_files[filename] = source_peer
                    peer_files.setdefault(source_peer, set()).add(filename) #handles case set empty
                    print(f"[BROADCAST] Received broadcast offer that Peer {source_peer}: {filename}")

def periodic_broadcast():
    global peer_id
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True: # Broadcast every 5 seconds
            for filename in os.listdir(f"./peer-{peer_id}"):    #Send all files in current peer's folder
                print(f"[BROADCAST] Broadcasting offer for {filename}")
                datagram = build_file_offer(peer_id, filename)
                sock.sendto(datagram, (BROADCAST_ADDRESS, BROADCAST_PORT))
            time.sleep(5)  # Broadcast every 5 seconds

#endregion Broadcast Function end
#=================================================================================================================
 # start() op on assignment desc.
 # path: the folder specific to the peer (may include local files)
def initialize():
    print("initalizing peer...")
    global peer_id
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
    threading.Thread(target=listen_for_broadcasts, name="BroadcastListener", daemon=True).start()
    threading.Thread(target=periodic_broadcast, name="BroadcastSender", daemon=True).start()
    print(f"Peer {peer_id} is now running and listening for broadcasts...")
    
    while True: 
        time.sleep(1)


if __name__ == "__main__":
    main()