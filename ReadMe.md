I used UDP to handle broadcasts because if I used TCP:
1. I would have to flood a range of TCP ports on sending
2. The bigger problem is the amount of parsing I have to do on recieving (all 4 msg types will arrive on the same port)
Multiple processes on the same machine can listen to the same UDP port because its connectionless, and all processes/peers send to the same address. Messages sent from the same peer is ignored by the peer.
So I spawned listener and sender threads for Broadcasting using UDP on the same port

Ideas for improvement:
 - broadcast functionality does not include handling removed files and updating removed files

