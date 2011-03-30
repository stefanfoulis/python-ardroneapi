from circuits.core.components import Component
from circuits.core.debugger import Debugger
from circuits.core.events import Event
from circuits.core.handlers import handler
from circuits.io import stdin
from circuits.net.sockets import UDPClient, Connect, Write, Disconnect
import socket


GROUP_IP = '224.1.1.1'
DRONE_IP = '192.168.1.1'
LOCAL_IP = '192.168.1.2'
PORT = 5554


class UDPMulticastClient(UDPClient):
    def __init__(self, bind, group, iface, **kwargs):
        self.group = group
        self.iface = iface
        super(UDPMulticastClient, self).__init__(bind, **kwargs)
        
    def _create_socket(self):
        sock = super(UDPMulticastClient, self)._create_socket()
        
        # register via IGMPv2
        group_bin = socket.inet_aton(self.group)
        iface_bin = socket.inet_aton(self.iface)
        # join group (IPv4)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, 
                     group_bin + iface_bin)
        return sock


class RawNavdataReceived(Event):
    """
    A set of *raw* navigation data has been received from a drone
    """

class RawNavdataHandler(Component):
    
    @handler('rawnavdatareceived')
    def handle_raw_navdata(self, data):
        print "HANDLE DATA:"
        print data
        print "===="
    

class NavdataComponent(Component):
    """
    Handles receiving navigation data from a drone
    """
    channel = 'navdata'
    
    def __init__(self):
        super(NavdataComponent, self).__init__()
        # register the UDP client to us
        Debugger().register(self)
        udp_client = UDPMulticastClient(bind=('', PORT), group=GROUP_IP, iface=LOCAL_IP, channel=self.channel)
        udp_client.register(self)
        RawNavdataHandler().register(self)
        
    
#    @handler("write")
#    def write(self, data):
#        print "WRITE:"
#        print data.strip()
#        print "======"
    
    def read(self, sock, data):
#        print "READ:"
#        print data.strip()
#        print "======"
        self.push(RawNavdataReceived(data=data))
    
#    @handler("read", target=stdin)
#    def stdin_read(self, data):
#        #self.push(Write(('224.0.0.22', 5554), data))
#        print "INPUT: '%s'" % data
#        if data.strip()=='disconnect':
#            self.push(Disconnect())
#        else:
#            self.push(Write(('192.168.1.1', 5554), data))
    
    def started(self, component, mode):
        print "NavdataComponent started"

NavdataComponent().run()