import socket
import struct

GROUP4 = '224.1.1.1'
#IGMPv3REG = '224.0.0.22'
PORT = 5554
REMOTE_IP = '192.168.1.1'
LOCAL_IP = '192.168.1.2'

def poke(remote_ip=REMOTE_IP, local_ip=LOCAL_IP, port=PORT):
    print "poking"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((local_ip, port))
    data = repr('hi')
    s.sendto(data+'\0', (remote_ip, port))

def receiver(group_ip=GROUP4, local_ip=LOCAL_IP, port=PORT):
    print "listening"
    # create the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # allow multipleprocesses to use this port
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind it to the port
    s.bind(('', port))
    #s.bind((LOCAL_IP, port))
    
    # register IGMPv2 (optional)
    group_bin = socket.inet_aton(group_ip)
    iface_bin = socket.inet_aton(LOCAL_IP)
    # join group (IPv4)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, 
                 group_bin + iface_bin)
    
#    # other variant of registering
#    group_bin = socket.inet_pton(socket.AF_INET, group)
#    any_bin = struct.pack('=I', socket.INADDR_ANY)
#    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group_bin+any_bin)
    
    while True:
        data, sender = s.recvfrom(100)
        #while data[-1:] == '\0': data = data[:-1] # strip trailing \0's
        print (str(sender) + '   ' + repr(data))

#poke()
receiver()
