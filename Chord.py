from datetime import datetime
import hashlib
import json
import os
import select
import signal
import socket
import struct
import sys
import threading
import time
import os

from ReadLog import MyLogger
from ChordMessage import ChordMessage as c_msg
from ChordMessage import newMsgDict


# Represents any object that has a place on the Chord ring
class ChordNode:
    def __init__(self, key, name="", isFile=False):
        # Chord Nodes can be used for network nodes or files
        self.ip = key
        self.filename = key
        self.name = name
        
        # Use hash to find position on ring
        if isFile:
            self.chord_id = [h % ring_size for h in get_hash(key, num_successors)]
        else:
            self.chord_id = get_hash(key) % ring_size

    def __str__(self):
        if self.name == "":
            return "key: {0}, chord id: {1}".format(self.ip, self.chord_id)
        return "key: {0}, name: {1}, chord id: {2}".format(self.ip, self.name, self.chord_id)

    def generate_fingers(self, finger_table_size):
        ''' Generate skeleton fingers
        '''
        fingers = []
        for index in range(finger_table_size):
            fingers.append(self.chord_id + (2**index))        
        return fingers    

    def print_finger_table(self, finger_table):
        ''' Print entries in finger table
        '''
        text = "\n"
        index = 0
        print(finger_table.keys())
        for key,value in sorted(finger_table.items()):
            text +="N{0} + {1}: {2}\n".format(key-(2**index),2**index,value)
            index +=1
        return text

# Get the hash of a key
def get_hash(key, numHashes=1):
    hash_func = hashlib.sha1()
    hashList = []
    for i in range(numHashes):
        # Update with key and keep first 4 bytes
        hash_func.update(key.encode())
        hash_bytes = hash_func.digest()
        hashList.append(struct.unpack("<L", hash_bytes[:4])[0])

    if numHashes == 1:
        return hashList[0]
    else:
        return hashList

# Send a UDP message to another node
def sendCtrlMsg(dst_ip, msg_type, msg):
    # Include the type of message this is
    msg['msg_type'] = msg_type

    # Serialize the message
    msg_json = json.dumps(msg)
    if sys.version_info[0] >= 3:
        msg_json = bytes(msg_json, encoding="utf-8")
    
    # Send the message to the destination's control port
    control_sock.sendto(msg_json, (dst_ip, control_port))
    myLogger.mnPrint("msg type:{0} sent to {1}: msg:{2}".format(msg_type, dst_ip, myLogger.pretty_msg(msg)))

# Received a UDP message
def ctrlMsgReceived():
    global successor, predecessor, entries, outstanding_file_reqs, finger_table, tracker_node_ip, inNetwork

    # Get data from socket
    try:
        data, addr = control_sock.recvfrom(1024)
    except socket.error as e:
        print(e)
        return
    
    # Drop all packets if we are not participating in the network
    if not inNetwork:
        return

    # Parse message type, update hops, and respond accordingly
    msg = json.loads(str(data))
    msg_type = msg['msg_type']
    msg["hops"] += 1
    myLogger.mnPrint("msg type:{0} rcvd from {1}: msg:{2}".format(msg_type, addr[0], myLogger.pretty_msg(msg)))

    # We are supposed to find target's successor
    if msg_type == c_msg.FIND_SUCCESSOR:
        key = msg['key']
        target = msg['target']
        #filename = msg['filename']
        findSuccessor(key, target, msg)
    # Someone returned our find successor query
    # TODO: since have 1 successor, ie, other nodes in ring, try to find rest of successors for successor list
    elif msg_type == c_msg.RETURN_SUCCESSOR:
        suc_ip = msg['suc_ip']
        filename = msg['filename']
        finger = msg['finger']
        # No filename indicates we wanted to find our successor
        if filename is None:
	        # Finger update
            if finger is not None:
                finger_table[finger] = suc_ip                
                myLogger.mnPrint(me.print_finger_table(finger_table))
            # Successor update
            else:
                successor = ChordNode(suc_ip)
                myLogger.mnPrint("Successor updated by find successor: {0}".format(successor))
        # Filename indicates we wanted to find a file's location
        else:
            fileNode = ChordNode(filename)
            myLogger.mnPrint("Found " + str(fileNode) + " at " + suc_ip)
            if outstanding_file_reqs[filename] == c_msg.OP_SEND_FILE:
                sendFile(suc_ip, msg)
            elif outstanding_file_reqs[filename] == c_msg.OP_REQ_FILE:
                sendCtrlMsg(suc_ip, c_msg.REQUEST_FILE, msg)
    # Someone wants to know who our predecessor is
    elif msg_type == c_msg.GET_PREDECESSOR:
        msg = newMsgDict()
        msg['pred_ip'] = None if predecessor is None else predecessor.ip
        sendCtrlMsg(addr[0], c_msg.RETURN_PREDECESSOR, msg)
    # Our successor told us who their predecessor is
    elif msg_type == c_msg.RETURN_PREDECESSOR:
        pred_ip = msg['pred_ip']
        stabilize(None if pred_ip == None else ChordNode(pred_ip))
    # Someone told us that they are our predecessor
    elif msg_type == c_msg.NOTIFY_PREDECESSOR:
        pred_ip = msg['pred_ip']
        if pred_ip is not None:
            notify(ChordNode(pred_ip))
    # Someone wants to know we are alive
    elif msg_type == c_msg.CHECK_ALIVE:
        sendCtrlMsg(addr[0], c_msg.AM_ALIVE, msg)
    # Someone told us they were alive
    elif msg_type == c_msg.AM_ALIVE:
        waiting_for_alive_resp[addr[0]] = False
    # Someone sent us a file
    elif msg_type == c_msg.SEND_FILE:
        filename = msg['filename']
        content = msg['content']
        with open("{0}/{1}".format(file_dir_path, filename), "w") as newFile:
            newFile.write(content)
        entries[filename] = ChordNode(filename)
        myLogger.mnPrint("Received file " + filename + " from " + str(addr[0]))
        # is file from the client -> tell them insertion was successful
        if msg["client_ip"] != None:
            sendCtrlMsg(msg["client_ip"], c_msg.INSERT_FILE, msg)
        # current responsible entries
        myLogger.mnPrint("Entries: {0}".format(entries.keys()))
    # Someone wants a file from us
    elif msg_type == c_msg.REQUEST_FILE:
        # Send directly to client
        if msg["client_ip"] is not None:
            sendFile(msg["client_ip"], msg, readFromFile=True)
            myLogger.mnPrint(msg['filename'] + " requested from " + msg["client_ip"])
        # Send to node who requested it
        else:
            sendFile(addr[0], msg, readFromFile=True, rmEntry=True)
            myLogger.mnPrint(msg['filename'] + " requested from " + addr[0])
    # We were informed of the death of a node
    elif msg_type == c_msg.SOMEONE_DIED:
        dead_node = ChordNode(msg['target'])
        # TODO: check dead_node's chord_id and compare it with the file table
        #           if we find that they were supposed to be in charge of a file,
        #           tell another holder of that file to insert it back into the network
    # We were informed that a node is leaving
    elif msg_type == c_msg.LEAVING:
        suc_ip = msg['suc_ip']
        pred_ip = msg['pred_ip']
        if suc_ip is not None:
            successor = ChordNode(suc_ip)
        elif pred_ip is not None:
            predecessor = ChordNode(pred_ip)

    # We are supposed to insert a file into the network
    elif msg_type == c_msg.INSERT_FILE:
        filename = msg['filename']
        outstanding_file_reqs[filename] = c_msg.OP_SEND_FILE
        fileNode = ChordNode(filename, isFile=True)
        myLogger.mnPrint("Inserting " + str(fileNode))       
        # TODO: check client_ip, if it exists then this is from the client, else is for reinserting a file on node failure
        for chord_id in fileNode.chord_id:
            findSuccessor(fileNode.chord_id, me.ip, msg)
    # We are supposed to retrieve a file from the network
    elif msg_type == c_msg.GET_FILE:
        filename = msg['filename']
        outstanding_file_reqs[filename] = c_msg.OP_REQ_FILE
        fileNode = ChordNode(filename, isFile=True)
        myLogger.mnPrint("Retrieving " + str(fileNode))
        # TODO: do a timeout, and if we don't get a response go onto next id
        findSuccessor(fileNode.chord_id[0], me.ip, msg)
    # send all known entries back to client if tracker
    elif msg_type == c_msg.GET_FILE_LIST:
        if me.ip == tracker_node_ip:
            msg["file_list"] = entries.keys()
            sendCtrlMsg(msg["client_ip"], c_msg.GET_FILE_LIST, msg)
    # TODO: when will this happen?
    elif msg_type == c_msg.ERR:
        pass

# This calls all methods that need to be called frequently to keep the network synchronized
def refresh():
    global successor, predecessor, refresh_rate, inNetwork

    counter = 0

    while True:
        if successor != None:
            # If we were waiting on a response from our successor and never got one, assume they died
            if waitingForAlive(successor.ip):
                myLogger.mnPrint("Our successor {0} has died!".format(successor))
                successor = me
            # Will get our successor's predecessor and call stabilize on return
            else:
                waiting_for_alive_resp[successor.ip] = True
                sendCtrlMsg(successor.ip, c_msg.GET_PREDECESSOR, newMsgDict())

        # Update our finger table
        if using_finger_table:
            fixFingers()

        # Handle predecessor death
        if predecessor != None:
            # If we were waiting on a response from our predecessor and never got one, assume they died
            if waitingForAlive(predecessor.ip):
                myLogger.mnPrint("Our predecessor {0} has died!".format(predecessor))
                msg = newMsgDict()
                msg['target'] = predecessor.ip
                sendCtrlMsg(tracker.ip, c_msg.SOMEONE_DIED, msg)
                predecessor = None
            # Check to see if the predecessor is still alive
            else:
                waiting_for_alive_resp[predecessor.ip] = True
                sendCtrlMsg(predecessor.ip, c_msg.CHECK_ALIVE, newMsgDict())

        '''
        counter += 1
        if me.name == "n4" and counter >= 10:
            counter = 0
            if inNetwork:
                leave()
            else:
                join()
        '''

        # Wait for short time
        time.sleep(refresh_rate)

# Return if we are waiting for an alive response from the given ip
def waitingForAlive(ip):
    return ip in waiting_for_alive_resp and waiting_for_alive_resp[ip]

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
    global inNetwork

    inNetwork = True
    myLogger.mnPrint("Joining the network...")
    findSuccessor(me.chord_id, me.ip)

# Leave the network gracefully
def leave():
    global inNetwork, predecessor, successor

    inNetwork = False
    myLogger.mnPrint("Leaving the network...")

    # Send all of our current files to our successor
    if successor is not None:
        msg = newMsgDict()
        for f in list(entries.keys()):
            msg['filename'] = f
            sendFile(successor.ip, msg, readFromFile=True, rmEntry=True)

    if successor is not None and predecessor is not None:
        # Tell our successor we are leaving and pass them our predecessor
        msg = newMsgDict()
        msg['pred_ip'] = predecessor.ip
        sendCtrlMsg(successor.ip, c_msg.LEAVING, msg)

        # Tell our predecessor we are leaving and pass them our successor
        msg = newMsgDict()
        msg['suc_ip'] = successor.ip
        sendCtrlMsg(predecessor.ip, c_msg.LEAVING, msg)

    successor = None
    predecessor = None

# Find the ip of the chord node that should succeed the given key
# If filename is specified, this is for finding a file location
def findSuccessor(key, target, msg=None):
    global successor

    # If key is somewhere between self and self.successor, then self.successor directly succeeds key
    if successor != None and keyInRange(key, me.chord_id, successor.chord_id, inc_end=True):
        # Build and send response
        if msg is None:
            msg = newMsgDict()                       
        msg['suc_ip'] = successor.ip
        sendCtrlMsg(target, c_msg.RETURN_SUCCESSOR, msg)
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
        if msg is None:
            msg = newMsgDict()       
        msg['key'] = key
        msg['target'] = target
        sendCtrlMsg(dst.ip, c_msg.FIND_SUCCESSOR, msg)

# Find the node in { {me} U finger_table } that preceeds the given key closest
def closestPreceedingNode(key):
    global finger_table, finger_table_size

    # Starting at furthest point in table, moving closer, see if table entry preceeds the given key
    for i in range(finger_table_size, -1, -1):
        if keyInRange(finger_table[fingers[i]], me.chord_id, key):
            return finger_table[fingers[i]]
    
    # Otherwise, we are the closest node we know of
    return me

# Given the returned predecessor of our successor, update if necessary and touch base with successor
def stabilize(x):
    global successor

    waiting_for_alive_resp[successor.ip] = False

    # If x is closer than our current successor, it is our new successor
    if x != None and keyInRange(x.chord_id, me.chord_id, successor.chord_id):
        successor = x
        waiting_for_alive_resp[successor.ip] = False
        myLogger.mnPrint("Successor updated by stabilize: " + str(successor))

    # Notify successor that we are its predecessor
    msg = newMsgDict()
    msg['pred_ip'] = me.ip
    sendCtrlMsg(successor.ip, c_msg.NOTIFY_PREDECESSOR, msg)

# Node told us that it is our predecessor
def notify(node):
    global predecessor

    # If the given id is between our current predecessor and us (or if we had no predecessor)
    #   then set it to be our predecessor
    if predecessor == None or keyInRange(node.chord_id, predecessor.chord_id, me.chord_id):
        predecessor = node
        waiting_for_alive_resp[predecessor.ip] = False
        myLogger.mnPrint("Predecessor updated by notify: " + str(predecessor))

        # Transfer all necessary files to predecessor
        for f, cn in list(entries.items()):
            msg = newMsgDict()
            # TODO: check all hashes of cn, transfer if any id in range, and rm if all ids in range
            # If file was not in range between us and predecessor, should go to predecessor
            if keyInRange(cn.chord_id, me.chord_id, predecessor.chord_id, inc_end=True):
                myLogger.mnPrint("Transferring {0} to {1}".format(f, predecessor))
                msg['filename'] = f
                sendFile(predecessor.ip, msg, readFromFile=True, rmEntry=True)

def fixFingers():
    '''Refresh the finger table entries periodicially'''
    global finger_table, finger_table_size
   
    for key in finger_table.keys():
        msg = newMsgDict()
        msg["finger"] = key
        findSuccessor(key, me.ip, msg)

def checkPredecessor():
    pass

# Send a file to a node
def sendFile(dst_ip, msg, readFromFile=False, rmEntry=False):    
    filename = msg['filename']
    if readFromFile:
        try:
            with open(file_dir_path+filename) as f:
                msg['content'] = f.read()
        except IOError as e:
            sendCtrlMsg(dst_ip, c_msg.ERR, msg)
            self.myLogger.mnPrint("Error: {0} not found!".format(filename))
            self.myLogger.mnPrint(e)
            return
    if rmEntry:
        if filename in entries:
            del entries[filename]
            # TODO: delete file
        else:
            mnPrint(filename + " not found in entries")
    myLogger.mnPrint("Sending " + filename + " to " + dst_ip)    
    sendCtrlMsg(dst_ip, c_msg.SEND_FILE, msg)

def exit(arg=None):
    '''exit the application
    '''
    if arg is not None:
        sys.exit(arg)
    sys.exit()     

if __name__ == "__main__":
    # Default parameters
    finger_table_size = 6
    tracker_node_ip = "172.1.1.1"
    control_port = 500
    using_finger_table = False
    num_successors = 1
    refresh_rate = 1

    try:
        # Open config file
        configFile = open("chordDFS.config")
        config = json.loads(configFile.read())
        configFile.close()

        # Load parameters from config file
        finger_table_size = config['finger_table_size']
        tracker_node_ip = config['tracker_node_ip']
        control_port = config['control_port']        
        using_finger_table = config['using_finger_table']
        num_successors = config['num_successors']
        refresh_rate = config["refresh_rate"]
    except:
        pass

    # Ring size is relative to finger table size s.t.
    #   the last entry on the finger table will cross half the ring
    ring_size = 2**finger_table_size # m

    # Pass in self as ip (getpeername gets localhost as ip)
    my_ip = ""
    my_name = ""
    if len(sys.argv) < 3:
        myLogger.mnPrint("Missing self ip and name!")
        exit()
    my_ip = sys.argv[1]
    my_name = sys.argv[2]
    me = ChordNode(my_ip, name=my_name)

    # Set relative file paths
    log_file_path = "nodes/{0}/logs/{1}.log".format(me.name, me.ip.replace(".", "_"))
    node_directory = "nodes/" + me.name    
    file_dir_path = node_directory + "/files/chord/"    

    # Get tracker based on ip from config
    tracker = ChordNode(tracker_node_ip)

    # If we are the tracker node
    is_tracker = me.ip == tracker_node_ip

    # create logger
    myLogger = MyLogger(me.ip, me.chord_id, log_file_path)

    # Announce initialization
    myLogger.mnPrint("Hi! I'm a chord node, my IP is {0}, my chord_id is {1}, my name is {2}".format(me.ip, me.chord_id, me.name))
    if is_tracker:
        myLogger.mnPrint("Oh, and I'm the tracker!")
    
    # Socket specifically for communicating with other chord nodes
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control_sock.bind((me.ip, control_port))

    # Every file that we are responsible for (name->ChordNode)
    entries = dict()

    # Maps filename to operation we want to perform when we find its location in the ring ('send' or 'request')
    outstanding_file_reqs = dict()

    # If we are waiting for a certain node to tell us that it is alive
    waiting_for_alive_resp = dict()

    # Predecessor is null by default
    predecessor = None

    # If this node is part of the network
    inNetwork = False

    # Tracker creates the network, and is thus its own successor
    if is_tracker:
        inNetwork = True
        successor = me
    # Every other node is joining the network after the tracker
    else:
        '''
        if me.name == "n4":
            time.sleep(15)
        else:
            time.sleep(1)
        '''
        time.sleep(1)
        successor = None
        join()

    # up to m entries; me.name + 2^i
    if using_finger_table:
        fingers = me.generate_fingers(finger_table_size)
        finger_table = {key: None for key in fingers}
        fixFingers()    

    # Install timer to run processes
    timer = threading.Thread(target=refresh)
    timer.start()

    # Multiplexing lists
    rlist = [control_sock]
    wlist = []
    xlist = []

    while True:
        # Multiplex on possible network messages
        try:
            _rlist, _wlist, _xlist = select.select(rlist, wlist, xlist)
        except:
            continue

        if control_sock in _rlist:
            ctrlMsgReceived()
