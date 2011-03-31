from ardroneapi import Drone

d = Drone(local_ip='192.168.1.3') #'192.168.1.2', 6666)
d.connect()
d.animate_leds(1)
d.flat_trims()
d.connect_nav()
#d.takeoff()
#d.land()


#d.takeoff()
#d.land()