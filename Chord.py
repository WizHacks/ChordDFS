from datetime import datetime
import hashlib
import json
import os
import select
import signal
import socket
import struct
import sys
import time

# Message types
FIND_SUCCESSOR = "1"        # Propogate a find successor message
RETURN_SUCCESSOR = "2"      # Return the result of a find successor query
GET_PREDECESSOR = "3"       # Request a node's predecessor
RETURN_PREDECESSOR = "4"    # Return your predecessor
NOTIFY_PREDECESSOR = "5"    # Notify node that you are its predecessor
CHECK_ALIVE = "6"           # Request a validation that you are alive
AM_ALIVE = "7"              # Return alive validation
SEND_FILE = "8"             # Forward a file to a node
REQUEST_FILE = "9"          # Request a file from a node (or client)

# Message types specific to Tracker/Client interactions
INSERT_FILE = "9"
GET_FILE = "10"
GET_FILE_LIST = "11"
ERR = "12"

# Network file operations
OP_SEND_FILE = "send"
OP_REQ_FILE = "request"

# Print that will show up in mininet output and get added to log file
def mnPrint(msg):
    global my_ip

    # Format msg
    msg = "<{0}>: {1}".format(my_ip, msg)

    # Print msg to stdout
    print(msg)
    sys.stdout.flush() # need to flush output, else never show up

    # Write msg to log file
    if my_ip != "":
        #with open("logs/" + fileName() + ".log", "a") as logFile:
        with open(node_directory + "/log.log", "w") as logFile:
            logFile.write("{0} {1}\n".format(str(datetime.now()).replace(" ", "_"), msg))

# Represents any object that has a place on the Chord ring
class ChordNode:
    def __init__(self, key):
        # Chord Nodes can be used for network nodes or files
        self.ip = key
        self.filename = key
        
        # Use hash to find position on ring
        self.chord_id = get_hash(key) % ring_size

    def __str__(self):
        return "key: {0}, chord id: {1}".format(self.ip, self.chord_id)

# Get the hash of a key
def get_hash(key):
    # Run hash function on given key
    hash_func = hashlib.sha1()
    hash_func.update(key.encode())
    hash_bytes = hash_func.digest()

    # Return integer conversion of first 4 bytes of hash
    return struct.unpack("<L", hash_bytes[:4])[0]

# Send a UDP message to another node
def sendCtrlMsg(dst_ip, msg_type, msg):
    # Include the type of message this is
    msg['msg_type'] = msg_type

    # Serialize the message
    msg_json = json.dumps(msg)
    if sys.version_info[0] >= 3:
        msg_json = bytes(msg_json)
    
    # Send the message to the destination's control port
    control_sock.sendto(msg_json, (dst_ip, control_port))

# Received a UDP message
def ctrlMsgReceived():
    global successor, predecessor, entries, outstanding_file_reqs

    # Get data from socket
    try:
        data, addr = control_sock.recvfrom(1024)
    except socket.error as e:
        print(e)
        return
    
    # Parse message type and respond accordingly
    msg = json.loads(str(data))
    msg_type = msg['msg_type']

    # We are supposed to find target's successor
    if msg_type == FIND_SUCCESSOR:
        key = msg['key']
        target = msg['target']
        filename = msg['filename']
        findSuccessor(key, target, filename)
    # Someone returned our find successor query
    elif msg_type == RETURN_SUCCESSOR:
        suc_ip = msg['suc_ip']
        filename = msg['filename']

        # No filename indicates we wanted to find our successor
        if filename == "":
            successor = ChordNode(suc_ip)
            mnPrint("Successor updated by find successor: " + str(successor))
        # Filename indicates we wanted to find a file's location
        else:
            if outstanding_file_reqs[filename] == OP_SEND_FILE:
                sendFile(suc_ip, filename)
            elif outstanding_file_reqs[filename] == OP_REQ_FILE:
                msg = dict()
                msg['filename'] = filename
                sendCtrlMsg(suc_ip, REQUEST_FILE, msg)
    # Someone wants to know who our predecessor is
    elif msg_type == GET_PREDECESSOR:
        msg = dict()
        msg['pred_ip'] = None if predecessor is None else predecessor.ip
        sendCtrlMsg(addr[0], RETURN_PREDECESSOR, msg)
    # Our successor told us who their predecessor is
    elif msg_type == RETURN_PREDECESSOR:
        pred_ip = msg['pred_ip']
        stabilize(None if pred_ip == None else ChordNode(pred_ip))
    # Someone told us that they are our predecessor
    elif msg_type == NOTIFY_PREDECESSOR:
        pred_ip = msg['pred_ip']
        notify(ChordNode(pred_ip))
    # Someone wants to know we are alive
    elif msg_type == CHECK_ALIVE:
        pass
    # Someone told us they were alive
    elif msg_type == AM_ALIVE:
        pass
    # Someone sent us a file
    elif msg_type == SEND_FILE:
        filename = msg['filename']
        content = msg['content']
        # TODO: write content to file
        entries.append(filename)
        mnPrint("Received file: " + str(entry))
    # Someone wants a file from us
    elif msg_type == REQUEST_FILE:
        sendFile(addr[0], msg['filename'])

# This calls all methods that need to be called frequently to keep the network synchronized
def handle_alrm(signum, frame):
    global successor, predecessor

    # Will get our successor's predecessor and call stabilize on return
    if successor != None:
        sendCtrlMsg(successor.ip, GET_PREDECESSOR, dict())

    # Update our finger table
    fixFingers()

    # Checks to see if the predecessor is still alive
    if predecessor != None:
        checkPredecessor()

    signal.alarm(1)

# Determine if the given key is between the two given endpoints
def keyInRange(key, start_id, end_id, inc_end=False):
    # If endpoints are on same side of chord ring
    if end_id > start_id:
        return key > start_id and (key <= end_id if inc_end else key < end_id)
    # If endpoints straddle the 0 point of the chord ring (or are equal)
    else:
        return key > start_id or (key <= end_id if inc_end else key < end_id)

# Join the network by finding out who your successor is
def join():
    mnPrint("Joining the network...")
    findSuccessor(me.chord_id, me.ip)

# Find the ip of the chord node that should succeed the given key
# If filename is specified, this is for inserting a file
def findSuccessor(key, target, filename=""):
    global successor

    # If key is somewhere between self and self.successor, then self.successor directly succeeds key
    if successor != None and keyInRange(key, me.chord_id, successor.chord_id, inc_end=True):
        # Build and send response
        msg = dict()
        msg['suc_ip'] = successor.ip
        msg['filename'] = filename
        sendCtrlMsg(target, RETURN_SUCCESSOR, msg)
    # Otherwise, send request to successor
    else:
        # Get node to send request to
        if successor == None:
            dst = tracker
        elif using_finger_table:
            dst = closestPreceedingNode(key) # TODO: if dst == me, we might have a problem
        else:
            dst = successor
        
        # Build and send request
        msg = dict()
        msg['key'] = key
        msg['target'] = target
        msg['filename'] = filename
        sendCtrlMsg(dst.ip, FIND_SUCCESSOR, msg)

# Find the node in { {me} U finger_table } that preceeds the given key closest
def closestPreceedingNode(key):
    global finger_table, finger_table_size

    # Starting at furthest point in table, moving closer, see if table entry preceeds the given key
    for i in range(finger_table_size, -1, -1):
        if keyInRange(finger_table[i].chord_id, me.chord_id, key):
            return finger_table[i]
    
    # Otherwise, we are the closest node we know of
    return me

# Given the returned predecessor of our successor, update if necessary and touch base with successor
def stabilize(x):
    global successor

    # If x is closer than our current successor, it is our new successor
    if x != None and keyInRange(x.chord_id, me.chord_id, successor.chord_id):
        successor = x
        mnPrint("Successor updated by stabilize: " + str(successor))

    # Notify successor that we are its predecessor
    msg = dict()
    msg['pred_ip'] = me.ip
    sendCtrlMsg(successor.ip, NOTIFY_PREDECESSOR, msg)

# Node told us that it is our predecessor
def notify(node):
    global predecessor

    # If the given id is between our current predecessor and us (or if we had no predecessor) then set it to be our predecessor
    if predecessor == None or keyInRange(node.chord_id, predecessor.chord_id, me.chord_id):
        predecessor = node
        mnPrint("Predecessor updated by notify: " + str(predecessor))
        # TODO: transfer all keys/files whose ids < node.chord_id to node

def fixFingers():
    pass

def checkPredecessor():
    pass

def sendFile(dst_ip, filename):
    msg = dict()
    msg['filename'] = filename
    # TODO: open TCP connection using a thread or fork
    # TODO: load content from file
    msg['content'] = ""
    sendCtrlMsg(suc_ip, SEND_FILE, msg)
    entries.remove(filename)


if __name__ == "__main__":
    # Default parameters
    finger_table_size = 6
    tracker_node_ip = "172.1.1.1"
    control_port = 500
    file_listen_port = 501
    using_finger_table = False

    try:
        # Open config file
        configFile = open("chordDFS.config")
        config = json.loads(configFile.read())
        configFile.close()

        # Load parameters from config file
        finger_table_size = config['finger_table_size']
        tracker_node_ip = config['tracker_node_ip']
        control_port = config['control_port']
        file_listen_port = config['file_listen_port']
        using_finger_table = config['using_finger_table']
    except:
        pass

    # Ring size is relative to finger table size s.t.
    #   the last entry on the finger table will cross half the ring
    ring_size = 2**finger_table_size

    # Pass in self as ip (getpeername gets localhost as ip)
    my_ip = ""
    if len(sys.argv) < 2:
        mnPrint("Missing self ip!")
        quit()
    my_ip = sys.argv[1]
    me = ChordNode(my_ip)

    # Create directory for this node
    node_directory = my_ip.replace(".", "_")
    if not os.path.exists(node_directory):
        os.makedirs(node_directory)

    # Create/clear log file
    # with open("logs/" + fileName() + ".log", "w") as logFile:
    with open(node_directory + "/log.log", "w") as logFile:
        logFile.write("")

    # Create files directory for this node
    if not os.path.exists(node_directory + "/files"):
        os.makedirs(node_directory + "/files")

    # TODO: clear out files

    # Get tracker based on ip from config
    tracker = ChordNode(tracker_node_ip)

    # If we are the tracker node
    is_tracker = my_ip == tracker_node_ip

    # Announce initialization
    mnPrint("Hi! I'm a chord node, my IP is {0}, my chord_id is {1}".format(my_ip, me.chord_id))
    if is_tracker:
        mnPrint("Oh, and I'm the tracker!")
    
    # Socket specifically for communicating with other chord nodes
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control_sock.bind((my_ip, control_port))

    # Socket specifically for accepting file transfer connections
    file_listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    file_listen_sock.bind((my_ip, file_listen_port))
    file_listen_sock.listen(5)

    # Name of every file that we are responsible for
    entries = []

    # Maps filename to operation we want to perform when we find its location in the ring ('send' or 'request')
    outstanding_file_reqs = dict()

    finger_table = []

    # Predecessor is null by default
    predecessor = None

    # Tracker creates the network, and is thus its own successor
    if is_tracker:
        successor = me
    # Every other node is joining the network after the tracker
    else:
        time.sleep(1)
        successor = None
        join()

    # Install timer to run processes
    # TODO: use threading for this, since this will prob break other things
    signal.signal(signal.SIGALRM, handle_alrm)
    signal.alarm(1)

    # Multiplexing lists
    rlist = [control_sock, file_listen_sock]
    wlist = []
    xlist = []

    # Keeps track of (sock, local_fd) pairs for each incoming file
    incoming_file_transfers = []

    # # Keeps track of (sock, local_fd) pairs for each outgoing file
    outgoing_file_transfers = []

    while True:
        # Multiplex on possible network messages
        try:
            _rlist, _wlist, _xlist = select.select(rlist, wlist, xlist)
        except:
            continue

        if control_sock in _rlist:
            ctrlMsgReceived()

        if file_listen_sock in _rlist:
            pass

        for ift in incoming_file_transfers:
            if ift[0] in _rlist:
                pass
        
