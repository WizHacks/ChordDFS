#!/usr/bin/python

"""
ChordDFS Nodes
"""

import sys
import atexit

import mininet.util
import mininext.util
mininet.util.isShellBuiltin = mininext.util.isShellBuiltin
sys.modules['mininet.util'] = mininet.util

from mininet.util import dumpNodeConnections
from mininet.node import OVSController
from mininet.log import setLogLevel, info

from mininext.cli import CLI
from mininext.net import MiniNExT

from topo import ChordDFSTopo

net = None


def startNetwork(num_nodes):
    "instantiates a topo, then starts the network and prints debug information"

    info('** Creating ChordDFS network topology\n')
    topo = ChordDFSTopo(num_nodes)

    info('** Starting the network\n')
    global net
    net = MiniNExT(topo, controller=OVSController)
    net.start()

    info('** Dumping host connections\n')
    dumpNodeConnections(net.hosts)
 
    '''info('** Testing network connectivity\n')
    net.ping(net.hosts)'''

    '''info('** Dumping host processes\n')
    for host in net.hosts:
        host.cmdPrint("ps aux")'''

    info('** Running Chord on hosts\n')
    for host in net.hosts[:-1]:
        host.cmdPrint("python Chord.py {0} {1} &".format(host.IP(), host.name))
    #net.hosts[-1].cmdPrint("python Client.py {0} {1} &".format(host.IP(), host.name))

    info('** Running CLI\n')
    CLI(net)


def stopNetwork():
    "stops a network (only called on a forced cleanup)"

    if net is not None:
        info('** Tearing down ChordDFS network\n')
        net.stop()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        num_nodes = int(sys.argv[1])
    else:
        num_nodes = 5
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork(num_nodes)

	


