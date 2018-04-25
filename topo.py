"""
Topology of ChordDFS routers
"""

import inspect
import os
import sys
  
from mininext.topo import Topo
from mininext.services.quagga import QuaggaService
from collections import namedtuple

ChordDFSHost = namedtuple("ChordDFSHost", "name ip")
net = None

class ChordDFSTopo(Topo):
	"Creates a topology of ChordDFS routers"

def __init__(self, num_nodes):
	"""Initialize a ChordDFS topology with num_nodes nodes, configure their IP
	addresses and paths to their private directories"""
	Topo.__init__(self)
	self.num_nodes = num_nodes      
	chordDFSHosts = []

	# create nodes
	for node in range(num_nodes):		
		node = self.addHost(name='n{0}'.format(node+1), ip='172.1.1.{0}/24'.format(node+1))
		chordDFSHosts.append(node)
		# create corresponding directories
		if not os.path.exists("n{0}".format(node+1)):
			os.makedirs("n{0}".format(node+1))

	
	# reverse the list so that tracker is root
	chordDFSHosts = chordDFSHosts.reverse()

	switch_num = 0
	switch_connections = 0
	switches = []
	while len(chordDFSHosts) !=0:
		# Add switch for IXP fabric
		switch_num += 1
		ixpfabric = self.addSwitch('fabric-sw{0}'.format(switch_num))
		switches.append(ixpfabric)
		while switch_connections !=8 and len(chordDFSHosts) !=0: 			
			# Attach the quaggaContainer to the IXP Fabric Switch
			self.addLink(chordDFSHosts.pop(), ixpfabric)	
			switch_connections += 1
		# connect switch to parent switch
		if switch_num != 1:			
			self.addLink(ixpfabric,switches[switch_num-1])		
