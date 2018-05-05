class ChordMessage():
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
	INSERT_FILE = "10"
	GET_FILE = "11"
	GET_FILE_LIST = "12"
	ERR = "13"

	# Network file operations
	OP_SEND_FILE = "SEND"
	OP_REQ_FILE = "REQUEST"

	# MISC
	EXIT = "EXIT"
	HELP = "HELP"