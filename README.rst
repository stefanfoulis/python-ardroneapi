=================
python-ardroneapi
=================

A standalone pure python api to control the Parrot AR.Drone.

.. Warning::
   This is highly EXPERIMENTAL and has not been fully tested!


Preperation
===========

You must be connected to the ad-hoc network of the AR.Drone. Check if
the drone can be pinged and if you can connect to it via telnet.
By default the drone will be at 192.168.1.1 and will assign your
computer the up 192.168.1.2.

If you've not changed anything you can go right ahead and instanciate 
the Drone without any parameters:

    >>> from ardroneapi import Drone
    >>> from ardroneapi.constants import ARDRONE_LED_ANIMATION_DOUBLE_MISSILE
    >>> d = Drone()
    >>> d.connect() # initiates the socket
    >>> d.animate_leds(ARDRONE_LED_ANIMATION_DOUBLE_MISSILE) # makes the leds blink.
    >>> d.flat_trims() # calibrate drone (make sure it is on a flat horizontal surface first)
    >>> d.takeoff()
    >>> d.land()
