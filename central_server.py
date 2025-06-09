from globals import *
from packet_format import *

# PEER_IP_REGISTRY = {
#     1: (LOCALHOST, 5001),
#     2: (LOCALHOST, 5002),
#     3: (LOCALHOST, 5003),
#     4: (LOCALHOST, 5004),
#     5: (LOCALHOST, 5005),
# }

peer_IP_registry: dict[int, tuple[str,int]] = dict()

def start_global_listener():
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.bind(SERVER_ADDRESS)
    soc.listen(5)  # Allow up to 5 queued connections

    while True:
        conn, addr = soc.accept()
        print(f"[SERVER] Accepted connection from {addr}")
        # Spawn a new thread to handle this connection
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

def handle_client(conn: socket.socket):
    client_peer_id: int
    try:
        while True:
            raw_message = conn.recv(1024) # need to be > FILE_CHUNK_SIZE
            if raw_message:
                msg_type = raw_message[0:2].decode('utf-8')
                if msg_type == 'SR':
                    peer_id, port = parse_request_register(raw_message)
                    client_peer_id = peer_id
                    register_peer(conn, peer_id, port)
                    continue
                elif msg_type == 'SL':
                    peer_id = parse_request_lookup(raw_message)
                    lookup_addr(conn, peer_id)
                    continue
                else:
                    print("[SERVER] Unknown message type ignored.")
                    continue
    except ConnectionResetError as e:
        print(f"[SERVER] Client peer closed the connection abruptly.")
        peer_IP_registry.pop(client_peer_id)
        conn.close()
        return

def register_peer(conn: socket.socket, peer_id, port):
    global peer_IP_registry

    if peer_id in peer_IP_registry.keys():
        err_message = build_response_error("Existing peer ID") #Error 0
        conn.sendall(err_message)
        return
    if any(port == value[1] for value in peer_IP_registry.values()):
        err_message = build_response_error("Existing port") #Error 1
        conn.sendall(err_message)
        return

    peer_IP_registry[peer_id] = (LOCALHOST, port)
    response = build_response_register(True)
    conn.sendall(response)
    print(f"Peer {peer_id} registered successsfully.")
    return

def lookup_addr(conn: socket.socket, target_peer_id):
    global peer_IP_registry

    print("===================")
    print(f"Debug: {peer_IP_registry}")
    print("===================")

    if target_peer_id not in peer_IP_registry.keys():
        print(f"Lookup failed for {target_peer_id}")
        err_message = build_response_error("Target peer not found.") #Error 2
        conn.sendall(err_message)
        return
    
    response = build_response_lookup(peer_IP_registry[target_peer_id])
    conn.sendall(response)
    print(f"Lookup returned successsfully: {peer_IP_registry[target_peer_id]}")
    return

def main():
    start_global_listener()

if __name__ == "__main__":
    main()