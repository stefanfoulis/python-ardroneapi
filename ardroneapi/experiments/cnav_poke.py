import socket
import struct

GROUP4 = '224.1.1.1'
PORT = 5554

def poke(group, port=PORT):
    # create the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # allow multipleprocesses to use this port
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind it to the port
    s.bind(('192.168.1.2', port))
    
    group_bin = socket.inet_pton(socket.AF_INET, group)
    # join group (IPv4)
    mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    while True:
        data, sender = s.recvfrom(1500)
        #while data[-1:] == '\0': data = data[:-1] # strip trailing \0's
        print (str(sender) + '   ' + repr(data))

receiver(GROUP4, PORT)
