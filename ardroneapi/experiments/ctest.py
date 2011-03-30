from ardroneapi import Drone

d = Drone()#'192.168.1.2', 6666)
d.connect()
d.animate_leds(1)
d.flat_trims()
#d.takeoff()
#d.land()


#d.takeoff()
#d.land()