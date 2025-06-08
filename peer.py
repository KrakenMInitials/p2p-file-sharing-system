import os, shutil, sys
from globals import *
from packet_format import *

#IMPORT INDIVIDUAL PEER INFORMATION STORED
peer_id: int = -1
neighbours:set[int] = set()
all_known_peers:set[int] = set(PEER_GRAPH.keys()) # All known peers in the network to flood
 # alt could be broadcasting too all ports on ip?
 

 # Broadcasts local files to neighbours
def broadcast_local_files(client_soc: socket.socket):
    global peer_id
    peer_folder = f"./peer{peer_id}"
    if not os.path.exists(peer_folder):
        print(f"Peer folder {peer_folder} does not exist. Cannot broadcast files.")
        return
    print(f"Broadcasting local files from {peer_folder}...")
    for neighbour in neighbours:
        socket_addr = PEER_IP_LOOKUP[neighbour]

        for filename in os.listdir(peer_folder):    
            file_path = os.path.join(peer_folder, filename)
            if os.path.isfile(file_path):
                segment: bytes = build_file_offer(peer_id, filename)
                client_soc.sendall(new_packet.encode())
                # Here you would implement the logic to send the file to connected peers
                # For now, we just print the action


 # start() op on assignment desc.
 # path: the folder specific to the peer (may include local files)
def initialize():
    print("start() op")
    global peer_id
    peer_folder = f"./peer{peer_id}"
    
     #reset existing peer folder
    if os.path.exists(peer_folder):
        shutil.rmtree(peer_folder)
    os.makedirs(peer_folder, exist_ok=True) 
    print(f"Peer path: {peer_folder} initialized.")
    
     # copy initial files (section of code provided by Github Copilot)
    template_folder = f"./initial_peer_folders/peer{peer_id}"
    if os.path.exists(template_folder):
        for filename in os.listdir(template_folder):
            src = os.path.join(template_folder, filename)
            dst = os.path.join(peer_folder, filename)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        print(f"Initial files copied from {template_folder}.")
     # end of Github Copilot

    

def main(): # args: peerID 
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



if __name__ == "__main__":
    main()