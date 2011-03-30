# SERVER
import socket
#IP = '10.23.42.16'
IP = '192.168.1.2'
PORT = 6666
ADDR = (IP, PORT)
BUF = 1024

s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(ADDR)
while 1:
    data,addr = s.recvfrom(BUF)
    if not data:
        print "Client has exited"
        break
    else:
        print """Received message"""
        print data
        print "from %s:%s" % addr
        print "======="

s.close()