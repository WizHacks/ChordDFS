# ChordDFS
Distributed File System implementation using Chord algorithm

## Requirements
- Mininet 2.1.0
- MiniNExT
- Python 2 or 3


## Instructions
1. Run `sudo python start.py --num_nodes` where `num_nodes` is the number of nodes in your topology that you want to start. Currently, there is an issue with using `num_nodes` > 9.
2. Start Chord protocol on any of the nodes by running `node# python Chord.py node#` where node# is the corresponding node; ie, `n1 python Chord.py n1`.
3. TBC