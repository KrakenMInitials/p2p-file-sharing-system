import struct

MAX_FILENAME_LENGTH = 64 #some areas statically use 64

#tcp buffer handling is static offsets (careful with changing protocols)

#region BUILDS
def build_file_offer(peerID: int, filename: str) -> bytes:
    msg_type = 'O'.encode('utf-8')
    enc_filename = filename.encode('utf-8').ljust(MAX_FILENAME_LENGTH, b'\x00')
    return struct.pack("!cII64s", msg_type, peerID, len(filename), enc_filename)

def build_file_request(filename: str) -> bytes:
    msg_type = 'R'.encode('utf-8')
    enc_filename = filename.encode('utf-8').ljust(MAX_FILENAME_LENGTH, b'\x00')
    return struct.pack("!cI64s", msg_type, len(filename), enc_filename)

def build_file_transfer(data: bytes) -> bytes:
    msg_type = 'T'.encode('utf-8')
    return struct.pack("!cI", msg_type, len(data)) + data

def build_ack_message(peer_id: int) -> bytes:
    msg_type = 'A'.encode('utf-8')
    return struct.pack("!cI", msg_type, peer_id)

def build_file_transfer_EOF(checksum: str) -> bytes:
    msg_type = 'E'.encode('utf-8')
    enc_checksum = checksum.encode("utf-8").ljust(MAX_FILENAME_LENGTH, b'\x00')
    return struct.pack("!c64s", msg_type, enc_checksum)
#endregion BUILDS

#region PARSES
def parse_file_offer(segment: bytes) -> tuple[int, str]:
    _, peer_id, filename_length, enc_filename = struct.unpack("!cII64s", segment)
    filename = enc_filename[:filename_length].decode('utf-8').rstrip('\x00').rstrip()
    return peer_id, filename

def parse_file_request(segment: bytes) -> str:
    _, filename_length, enc_filename = struct.unpack("!cI64s", segment)
    filename = enc_filename[:filename_length].decode('utf-8').rstrip('\x00').rstrip()
    return filename

def parse_file_transfer(segment: bytes) -> bytes:
    _, data_length = struct.unpack("!cI", segment[:5])
    data = segment[5:5 + data_length]
    return data

def parse_ack_message(segment: bytes) -> int:
    _, peer_id = struct.unpack("!cI", segment)
    return peer_id

def parse_file_transfer_EOF(segment: bytes) -> str: #returns expected checksum  
    _, checksum = struct.unpack("!c64s", segment)
    return checksum.decode('utf-8').rstrip('\x00').rstrip()
#endregion PARSES

#========================

#region peer X central_server

   #client-side
def build_request_register(peer_id: int, port: int):
    return struct.pack("!ccII", b'S', b'R', peer_id, port)

def build_request_lookup(peer_id: int):
    return struct.pack("!ccI", b'S', b'L', peer_id)

    #server-side
def build_response_register(operation: bool):
    return struct.pack("!ccI", b'S', b'R', int(operation))

def build_response_error(err_msg: str):
    return struct.pack("!cc64s", b'S', b'E', err_msg.encode("utf-8").ljust(MAX_FILENAME_LENGTH, b'\x00'))

def build_response_lookup(peer_addr: tuple[str,int]):
    host = peer_addr[0]
    enc_addr = host.encode("utf-8").ljust(MAX_FILENAME_LENGTH, b'\x00')
    return struct.pack("!cc64sI", b'S', b'L', enc_addr, peer_addr[1])

    #--------------

def parse_request_register(raw_message: bytes):
    _, _, peer_id, port = struct.unpack("!ccII", raw_message)
    return peer_id, port

def parse_resposne_register(raw_msg: bytes) -> bool:
    _, _, operation = struct.unpack("!ccI", raw_msg)
    return bool(operation)

def parse_response_error(raw_message: bytes):
    _, _, enc_err_msg = struct.unpack("!cc64s", raw_message)
    err_msg = enc_err_msg.decode("utf-8").rstrip('\x00').rstrip()
    return err_msg

def parse_request_lookup(raw_msg: bytes):
    _, _, peer_id = struct.unpack("!ccI", raw_msg)
    return peer_id

def parse_response_lookup(raw_msg: bytes):
    _, _, enc_host, port = struct.unpack("!cc64sI", raw_msg)
    host = enc_host.decode("utf-8").rstrip('\x00').rstrip()
    peer_addr = (host, port)
    return peer_addr