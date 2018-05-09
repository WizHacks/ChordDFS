# ChordDFS
Distributed File System implementation using Chord algorithm

## Requirements
- Mininet 2.1.0
- MiniNExT
- Python 2 or 3


## Instructions
1. Run `sudo python start.py --num_nodes` where `num_nodes` is the number of nodes in your topology that you want to start. Currently, there is an issue with using `num_nodes` > 9.
2. Start Chord protocol on any of the nodes by running `node# python Chord.py node# \node#` where node# is the corresponding node; ie, `n1 python Chord.py n1 \n1`.
3. TBC

## Examples
n1 python Chord.py n1 \n1 &					# n1 run server in background
n2 python Client.py n2 \n2					# n2 run client with stdin i/o
n3 python Client.py n3 \n3 script.txt 		# n3 run client with script, no i/o


## Measurements
1) Time till stabilization vs num of nodes in network (initial)
2a) Client (single) ops avg hops vs number of nodes in network (after stabilization)
	a) insert - node that inserts file sends msg to client
	b) get - node that has file sends msg to client
	c) list - tracker node sends msg to client
2b) number of clients (multiple)
2c) compare using find successor vs using finger table
3) Avg number of keys per node vs total number of keys
4) Time till convergence after stabilization (new node joins) vs num of nodes in network (initial)

## Visualization
1) Chord Ring