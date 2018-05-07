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