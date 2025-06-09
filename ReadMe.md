# Simple Peer-to-Peer (P2P) Networked File System

## INSTRUCTIONS

- `peer.py` main() can be adjusted to simulate additional file requests, and files can be added to `initial_peer_folders` to support more peers.
- Clearing folders is already implemented. For example, running `peer.py` with `peerID = 1` will clear the `peer-1` folder.
- By default: Peer 1 has `dummyfile.txt`, Peer 2 has `piratedGame`. Peer 1 wants `piratedGame` and Peer 3 wants `dummyfile.txt`.
- `demo.bat` automates this demonstration.

### Storage & Broadcasts

- Each peer's storage is simulated to be distributed using folders in the root directory (similar to Assignment 1).
  - `initial_peer_folders` contains the initial files each peer should have.
- Broadcasts are handled by binding all peers to a common UDP port and sending file offers to the port.
  - Each peer has `broadcastListener` and `broadcasterSender` threads.
  - Listener updates `known_files` dictionary (filenames: peerIDs).
  - Sender uses `local_files` set to track local files to broadcast offers.
- EOFs are communicated through a new protocol type 'E' with a checksum for the complete file.
  - The first time a peer downloads a file from another peer, it will force a corruption of the checksum to simulate checksum failure.
  - Checksum fail recovery involves wiping the local file and requesting the file again from scratch before killing the old thread and associated resources.

### Central Server

- Disconnected/crashed clients get removed from the central server registry.
- Peer failure is abstracted away from other peers to an extent.
- Duplicate ports or peerIDs are prevented.
- Broadcasts are handled between peers.

### Main Functions

- Registration
- Lookups

---

## Peer Logic (Thread Architecture)

_Thread architecture I'm really proud of:_

- A `server_soc` is kept connected to the central server by every peer for fetching lookups.
- Each peer has two main functionalities:
  - `global_requester()`: creates an 'outgoing' thread to handle outgoing requests, incoming file transfers, and outgoing acks for each peer.
  - `global_listener()`: creates an 'incoming' thread to handle incoming requests, outgoing file transfers, and incoming acks for each peer.

#### GlobalListener Thread

- Spawns a handler thread (Listener Thread) for each new incoming peer connection.

#### Listener Thread

- Spawns a concurrent thread to process `requests_queue` (communicates with it through ack events).
- Appends to `request_queue` on loop.
- Remote peer crashes are handled gracefully.

#### GlobalRequester Thread

- Creates a request and spawns a concurrent thread to process incoming file transfers ("downloads") through `downloads_queue`.
- EOF is passed into the queue using a Sentinel marker (suggested by Copilot), and the concurrent thread adds the file to `local_files` before killing itself.
- Core thread kills itself after.

---

## Protocol Table

| Message Type       | Code | Format       | Purpose / Description                                                               |
| ------------------ | ---- | ------------ | ----------------------------------------------------------------------------------- |
| **File Offer**     | O    | `!cII64s`    | Peer advertises its available files                                     |
| **File Request**   | R    | `!cI64s`     | Peer requests a file from another peer.                                             |
| **File Transfer**  | T    | `!cI` + data | Sends a chunk of file data to the requesting peer.                                  |
| **Acknowledgment** | A    | `!cI`        | Acknowledgement chunk.                                               |
| **EOF/Checksum**   | E    | `!c64s`      | Signals end of file and provides file checksum  |

### Central Server Protocol

| Message Type          | Code | Format    | Purpose / Description                                                |
| --------------------- | ---- | --------- | -------------------------------------------------------------------- |
| **Register Request**  | S,R  | `!ccII`   | Peer requests to register itself on central server registry.          |
| **Register Response** | S,R  | `!ccI`    | Server response to registration (1=success, 0=failure).              |
| **Lookup Request**    | S,L  | `!ccI`    | Peer requests lookup of address of target peerID from the server.               |
| **Lookup Response**   | S,L  | `!cc64sI` | Server response with the address (host, port) of the requested peer. |
| **Error Response**    | S,E  | `!cc64s`  | Server error message.                                       |

