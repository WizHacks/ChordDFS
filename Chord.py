import hashlib
import select
import socket
import struct
import sys

# Control message types
FIND_SUCCESSOR = 1
GET_PREDECESSOR = 2
SET_PREDECESSOR = 3

class ChordNode:
    def __init__(self, ip):
        self.ip = ip
        self.chord_id = get_hash(ip) % ring_size

# Get the hash of a key
def get_hash(key):
    # Run hash function on given key
    hash_func = hashlib.sha1()
    hash_func.update(key.encode())
    hash_bytes = hash_func.digest()

    # Return integer conversion of first 4 bytes of hash
    return struct.unpack("<L", hash_bytes[:4])[0]

# Send a UDP message to another node
def sendUDP(sock, dst_ip, dst_port, type, msg):
    pass

# Received a UDP message
def udpReceived(sock, mask):
    # Parse message type and respond accordingly
    pass

# Determine if the given key is between the two given endpoints
def keyInRange(key, start_id, end_id, inc_end=False):
    # If endpoints are on same side of chord ring
    if end_id > start_id:
        return key > start_id and (key <= end_id if inc_end else key < end_id)
    # If endpoints straddle the 0 point of the chord ring
    else:
        return key > start_id or (key <= end_id if inc_end else key < end_id)

# Find the ip of the chord node that should succeed the given key
def findSuccessor(key):
    # If key is somewhere between self and self.successor, then self.successor directly succeeds key
    if keyInRange(key, me.chord_id, successor.chord_id, inc_end=True):
        return successor
    # Otherwise, send request to successor
    else:
        if using_finger_table:
            dst = closestPreceedingNode(key) # TODO: if dst == me, we might have a problem
        else:
            dst = successor
        sendUDP(control_sock, dst.ip, control_port, FIND_SUCCESSOR, "...")

# Find the node in { {me} U finger_table } that preceeds the given key closest
def closestPreceedingNode(key):
    # Starting at furthest point in table, moving closer, see if table entry preceeds the given key
    for i in range(finger_table_size, -1, -1):
        if keyInRange(finger_table[i].chord_id, me.chord_id, key):
            return finger_table[i]
    
    # Otherwise, we are the closest node we know of
    return me


def stabilize():
    # Ask successor for its current predecessor
    x = None

    if x != None and keyInRange(x.chord_id, me.chord_id, successor.chord_id):
        successor = x

    # Notify successor that we are its new predecessor


def notify(node):
    # If the given id is between our current predecessor and us (or if we had no predecessor) then set it to be our predecessor
    if predecessor == None or keyInRange(node.chord_id, predecessor.chord_id, me.chord_id):
        predecessor = node
        # TODO: transfer all keys/files whose ids < node.chord_id to node

def fixFingers():
    pass

def checkPredecessor():
    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
	print("Missing self ip!")
    # Load parameters from config file
    #configFile = open("chordDFS.config")
    finger_table_size = 6
    ring_size = 2**finger_table_size
    tracker_node_ip = "172.1.1.1"
    control_port = 500
    file_listen_port = 501
    file_send_port = 502
    using_finger_table = False

    finger_table = []

    tracker_node = ChordNode(tracker_node_ip)

    my_ip = sys.argv[1] # need to pass in self as ip ow we get localhost as ip
    me = ChordNode(my_ip)

    is_tracker = my_ip == tracker_node_ip

    print("Hi! I'm a chord node, my IP is {0}, my chord_id is {1}".format(my_ip, me.chord_id))

    if is_tracker:
        print("Oh, and I'm the tracker!")
    sys.stdout.flush() # need to flush output, else never show up
    # Socket specifically for communicating with other chord nodes
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control_sock.bind((my_ip, control_port))

    # Socket specifically for accepting file transfer connections
    file_listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    file_listen_sock.bind((my_ip, file_listen_port))
    file_listen_sock.listen(5)

    # Socket specifically for sending files
    file_send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    file_send_sock.bind((my_ip, file_send_port))

    # Set our successor node
    successor = me
    if not is_tracker:
        # TODO: ask tracker to find successor
        pass

    # Predecessor node is null by default
    predecessor = None

    # Multiplexing lists
    rlist = []
    wlist = []
    xlist = []

    # Keeps track of (sock, local_fd) pairs for each incoming file
    incoming_file_transfers = []

    while True:
        # Multiplex on possible network messages
        _rlist, _wlist, _xlist = select.select(rlist, wlist, xlist)

        # TODO: if on control_sock, parse message and respond
        if control_sock in _rlist:
            pass

        # TODO: if on file_listen_sock, accept connection, add to client_connections, add to sel
        if file_listen_sock in _rlist:
            pass

        # TODO: if on any incoming_file_transfers, read data and write to file
        for ift in incoming_file_transfers:
            if ift[0] in _rlist:
                pass

        # TODO: if on file_send_sock, send data, do we need multiplexing for this? (to not get stuck on tcp write)
        if file_send_sock in _wlist:
            pass
