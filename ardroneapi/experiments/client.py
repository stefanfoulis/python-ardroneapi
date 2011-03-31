import socket
RIP = '192.168.1.1'
RPORT = 5556

LIP = '192.168.1.2'
LPORT = 5556

#RIP = '10.23.42.16'
#RPORT = 6666
#
#LIP = '10.23.42.16'
#LPORT = 5556

CTAKEOFF = 'AT*REF=101,290718208\r'
CLAND = 'AT*REF=102,290717696\r'


s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM)
s.bind((LIP, LPORT))
s.connect( (RIP, RPORT) )

s.getsockname()
s.getpeername()

s.send(CTAKEOFF)
s.send(CLAND)
s.close()
