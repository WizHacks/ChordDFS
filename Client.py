import time
import json
import socket
import select
import sys
import os
import fcntl

from ReadLog import MyLogger
from ChordMessage import ChordMessage as c_msg

class Client():
	'''
	Client class, used to communicate with the Chord servers
	ip: ip of the client
	name: name of the client	
	'''
	def __init__(self, ip, name, control_sock, file_listen_sock):
        # Chord Nodes can be used for network nodes or files
		self.ip = ip        
		self.name = name
		self.last_request = None
		self.control_sock = control_sock
		self.file_listen_sock = file_listen_sock

		# Default parameters    
		self.tracker_node_ip = "172.1.1.1"
		self.control_port = 500
		self.file_listen_port = 501

		try:
		    # Open config file
		    configFile = open("chordDFS.config")
		    config = json.loads(configFile.read())
		    configFile.close()

		    # Load parameters from config file        
		    self.tracker_node_ip = config['tracker_node_ip']
		    self.control_port = config['control_port']
		    self.file_listen_port = config['file_listen_port']

		except:
		    pass        

		# logging
		log_file_path = "nodes/{0}/logs/{1}_c.log".format(self.name, self.ip.replace(".", "_"))
		# create logger
		self.myLogger = MyLogger(self.ip, log_file_path)

		# Announce initialization
		self.myLogger.mnPrint("Hi! I'm a chord client, my IP is {0}".format(self.ip, self.name))        

	def __str__(self):	
	    return "ip: {0}, name: {1}\nlast: {2}".format(self.ip, self.name, self.last_request)

	'''Main Methods'''
	def insert_file(self, filename):
		''' Insert a file
		'''
		content = ""
		with open("nodes/{0}/files/client/{1}".format(self.name, filename)) as f_in:
			content = f_in.read()
			msg = dict()
			msg['filename'] = filename
			msg['content'] = content
			sendMessage(c_msg.INSERT_FILE, msg)	

	def get_file(self, filename):
		'''Request a file
		'''
		msg = dict()
		msg['filename'] = filename
		sendMessage(c_msg.GET_FILE, msg)		

	def get_file_list(self):
		'''Request available files
		'''
		msg = dict()        
		sendMessage(c_msg.GET_FILE_LIST, msg)	

	'''Helper methods'''
	def processRequest(self, request, args=None):
		'''
		Have the player client make a request
		request: the request to make
		arg: arg for request
		'''
		self.myLogger.mnPrint("received request: {0}:{1}".format(request, args))
		if request == c_msg.GET_FILE:
			self.get_file(args[0])
		elif request == c_msg.INSERT_FILE:
			self.insert_file(args[0])
		elif request == c_msg.GET_FILE_LIST:
			self.get_file_list()	
		else:
			pass

	def sendMessage(self, msg_type, msg):
		'''Send message to tracker node
		'''
		# Include the type of message this is
		msg['msg_type'] = msg_type

		# Serialize the message
		msg_json = json.dumps(msg)
		if sys.version_info[0] >= 3:
		    msg_json = bytes(msg_json, encoding="utf-8")

		# Send the message to the destination's control port
		self.control_sock.sendto(msg_json, (self.tracker, self.control_port))

	def list_dir(self):
		'''
		list own directory
		'''
		pass

'''utility functions'''
def exit(arg=None):
	'''exit the application
	'''
	# close stdin so program doesnt break
	os.close(sys.stdin.fileno())
	if arg is not None:
		sys.exit(arg)
	sys.exit()

def ctrlMsgReceived():
	''''''
	global me
	pass

def processStdin():
	'''Process the stdin input and take appropriate action
	'''
	global me
	global std_input
	# read until new line
	ch = sys.stdin.read()
	if ch != "\n":
		std_input += ch
		return
	else:
		args = std_input.split(" ")
		std_input = ""
	# handle stdin
	if len(args) > 0:
		me.myLogger.mnPrint("received stdin request: {0}".format(args))
		cmd = args[0].upper().strip()		
		# HELP
		if cmd == c_msg.HELP:
			help()	
		# EXIT
		elif cmd == c_msg.EXIT:
			exit()
		# client handles itself
		else:	
			me.processRequest(cmd, args[1:])

def help():
	'''
	Prints the help menu
	'''
	print("help request")
	sys.stdout.flush()

if __name__ == "__main__":	

    # Pass in self as ip
    my_ip = ""
    my_name = ""
    if len(sys.argv) < 3:
        mnPrint("Missing self ip and name!")
        sys.exit()
    my_ip = sys.argv[1]
    my_name = sys.argv[2]    
	
    std_input = ""	
	
    # Socket specifically for communicating with other chord nodes
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Socket specifically for accepting file transfer connections
    file_listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # set up client
    me = Client(my_ip, my_name, control_sock, file_listen_sock)	

    control_sock.bind((me.ip, me.control_port))
    file_listen_sock.bind((me.ip, me.file_listen_port))
    file_listen_sock.listen(5)	        

    # Multiplexing lists	
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, fcntl.fcntl(sys.stdin, fcntl.F_GETFL) | os.O_NONBLOCK)	
    rlist = [control_sock, file_listen_sock, sys.stdin]
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

	    if sys.stdin in _rlist:
	    	processStdin()    

	    if file_listen_sock in _rlist:
	        pass		
