"""
Topology of Quagga routers
"""

import inspect
import os
import sys
import inspect
import os

from mininext.topo import Topo
from mininext.services.quagga import QuaggaService
from mininext.topo import Topo
from mininext.services.quagga import QuaggaService
from collections import namedtuple
from collections import namedtuple

QuaggaHost = namedtuple("QuaggaHost", "name ip")
net = None

class QuaggaTopo(Topo):

    "Creates a topology of Quagga routers"

    def __init__(self, num_nodes):
        """Initialize a Quagga topology with num_nodes nodes, configure their IP
           addresses and paths to their private
           configuration directories."""
        Topo.__init__(self)
        self.num_nodes = num_nodes

        # Directory where this file / script is located"
        selfPath = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))  # script directory

        # Initialize a service helper for Quagga with default options
        quaggaSvc = QuaggaService(autoStop=False)

        # Path configurations for mounts
        quaggaBaseConfigPath = selfPath + '/configs/'

        # List of Quagga host configs
        quaggaHosts = []
        for node in range(num_nodes):
          quaggaHosts.append(QuaggaHost(name='n{0}'.format(node+1), ip='172.1.1.{0}/24'.format(node+1)))

        # Add switch for IXP fabric
        ixpfabric = self.addSwitch('fabric-sw')

        # Setup each Quagga router, add a link between it and the IXP fabric
        for host in quaggaHosts:

            # Create an instance of a host, called a quaggaContainer
            quaggaContainer = self.addHost(name=host.name,
                                           ip=host.ip,
                                           hostname=host.name,
                                           privateLogDir=True,
                                           privateRunDir=True,
                                           inMountNamespace=True,
                                           inPIDNamespace=True,
                                           inUTSNamespace=True)

            # Configure and setup the Quagga service for this node
            quaggaSvcConfig = \
                {'quaggaConfigPath': quaggaBaseConfigPath + host.name}
            self.addNodeService(node=host.name, service=quaggaSvc,
                                nodeConfig=quaggaSvcConfig)

            # Attach the quaggaContainer to the IXP Fabric Switch
            self.addLink(quaggaContainer, ixpfabric)
