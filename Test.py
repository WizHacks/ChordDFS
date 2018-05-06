import json
import socket
import sys
from ChordMessage import ChordMessage as c_msg

# Send a UDP message to another node
def sendCtrlMsg(dst_ip, msg_type, msg):
    # Include the type of message this is
    msg['msg_type'] = msg_type

    # Serialize the message
    msg_json = json.dumps(msg)
    if sys.version_info[0] >= 3:
        msg_json = bytes(msg_json, encoding="utf-8")
    
    # Send the message to the destination's control port
    control_sock.sendto(msg_json, (dst_ip, 500))

if __name__ == "__main__":
    op = sys.argv[1]
    filename = sys.argv[2]

    control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control_sock.bind(("172.1.1.1", 600))

    if op == "insert":
        msg = dict()
        msg['filename'] = filename
        sendCtrlMsg("172.1.1.1", c_msg.INSERT_FILE, msg)
    elif op == "get":
        msg = dict()
        msg['filename'] = filename
        sendCtrlMsg("172.1.1.1", c_msg.GET_FILE, msg)
        
