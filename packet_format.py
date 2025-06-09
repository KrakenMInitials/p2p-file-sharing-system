import struct

MAX_FILENAME_LENGTH = 64 #some areas statically use 64

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

def build_file_transfer_EOF() -> bytes:
    msg_type = 'E'.encode('utf-8')
    return struct.pack("!c", msg_type)
#endregion BUILDS

#region PARSES
def parse_file_offer(segment: bytes) -> tuple[int, str]:
    _, peer_id, filename_length, enc_filename = struct.unpack("!cII64s", segment)
    filename = enc_filename[:filename_length].decode('utf-8').rstrip('\x00')
    return peer_id, filename

def parse_file_request(segment: bytes) -> str:
    _, filename_length, enc_filename = struct.unpack("!cI64s", segment)
    filename = enc_filename[:filename_length].decode('utf-8').rstrip('\x00')
    return filename

def parse_file_transfer(segment: bytes) -> bytes:
    _, data_length = struct.unpack("!cI", segment[:5])
    data = segment[5:5 + data_length]
    return data

def parse_ack_message(segment: bytes) -> int:
    _, peer_id = struct.unpack("!cI", segment)
    return peer_id

def parse_file_transfer_EOF(): #just here to complete the builds and parses, doesn't really matter
    return None
#endregion PARSES