import socket
import struct


class Drone(object):
    """
    Preperation:
        You must be connected to the ad-hoc network of the AR.Drone. Check if
        the drone can be pinged and if you can connect to it via telnet.
        By default the drone will be at 192.168.1.1 and will assign your
        computer the up 192.168.1.2.
    
    If you've not changed anything you can go right ahead and instanciate 
    the Drone without any parameters:
    
    >>> d = Drone()
    >>> d.connect() # initiates the socket
    >>> d.animate_leds(13) # makes the leds blink.
    >>> d.flat_trims() # calibrate drone (make sure it is on a flat horizontal surface)
    >>> d.takeoff()
    >>> d.land()
    
    """
    
    def __init__(self, drone_ip=None, drone_port=None, local_ip=None, local_port=None):
        self._sequence = 0
        self.drone_ip = drone_ip or '192.168.1.1'
        self.drone_port = drone_port or 5556
        self.local_ip = local_ip or '192.168.1.2'
        self.local_port = local_port or 5556
        
        self.socket = None
    
    @property
    def sequence(self):
        self._sequence += 1
        return self._sequence
    
    def raw_send(self, data):
        '''
        sends the raw data to the drone
        '''
        if not self.socket:
            raise Exception("Not connected yet!")
        self.socket.send(data)
    
    def build_raw_command(self, method, params=None):
        '''
        construct the low level AT command and add the squence number
        '''
        if not params:
            params = []
        params2 = []
        for param in params:
            if type(param) == float:
                params2.append(str(float2int(param)))
            else:
                params2.append(str(param))
        params_str = ','.join([str(self.sequence)] + params2)
        return 'AT*' + method + '=' + params_str + '\r'
    
    def build_raw_commands(self, commands):
        '''
        TODO: logic to prevent UDP Packets that are larger than 1024 characters
        '''
        r = []
        for command in commands:
            r.append(self.build_command(*command))
        return [''.join(r)]
    
    def send(self, method, params=None):
        self.raw_send(self.build_raw_command(method, params))
    
    def send_many(self, commands):
        for data in self.build_raw_commands(commands):
            self.raw_send(data)
    
    def connect(self):
        self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.socket.bind( (self.local_ip, self.local_port))
        self.socket.connect( (self.drone_ip, self.drone_port) )
    
    def disconnect(self):
        self.socket.close()
        self.socket = None
    
    #===========================================================================
    # drone control commands
    #===========================================================================
    
    def takeoff(self):
        """
        If no other command is supplied, the drone enters a hovering mode and
        stays still at approximately 1 meter above ground.
        """
        #self.send('REF', '290718208')
        self.send('REF', '512')
    
    def land(self):
        """
        The drone lands and turns off its motors.
        """
        #self.send('REF', '290717696')
        self.send('REF', '0')
    
    def emergency(self):
        """
        Engines are cut-off no matter the drone state. (ie. the drone crashes, 
        potentially violently).
        
        Emergency (bit 8): 1
        Takeoff (bit 9)  : 0
        
        """
        self.send('REF', '256')
    
    def recover(self):
        """
        revovers from the emergency
        
        Emergency (bit 8): 0
        Takeoff (bit 9)  : 0
        """
        self.send('REF', '0')
    
    def hover(self):
        """
        Tells the drone to hold its position
        """
        self.send_many(
            ('COMWDG',),
            ('PCMD', (0,0,0,0,0)),
        )
    
    def move(self, roll, pitch, gaz, yaw):
        """
        Tell the drone to move. All values are percentages of the configured
        maximum values.
        
        roll: left/right tilt [-1..1] (negative: left, positive: right)
        pitch: forwards/backwards tilt [-1..1] (negative: frontward, positive: backward)
        gaz: vertical speed [-1..1]  (negative: down, positive: up)
        yaw: angular speed [-1..1] (negative: spin left, positive: spin right)
        
        """
        if all(not bool(roll), not bool(pitch), not bool(gaz), not bool(yaw)):
            # if they are all 0, then this is actually a hover command
            self.hover()
            return
        self.send_many([
            ('COMWDG',),
            # the first value means move. 0 would mean "hover"
            ('PCMD', (1, float(roll), float(pitch), float(gaz), float(yaw))),
        ])
    
    def flat_trims(self):
        """
        This command sets a reference of the horizontal plane for the drones 
        internal control system.
        
        It must be called after each drone start up, while making sure the 
        drone actually sits on a horizontal ground. Not doing so before 
        taking-off will result in the drone not being able to stabilize itself 
        when flying, as it would not be able to know its actual tilt.
        
        When receiving this command, the drone will automatically adjust the 
        trim on pitch and roll controls.
        """
        self.send('FTRIM',)
    
    def select_video_channel(self, mode):
        """
        ZAP_CHANNEL_HORI [0]:
            Broadcast video from the front camera
        ZAP_CHANNEL_LARGE_VERT_SMALL_HORI [1]:
            Broadcast video from the belly camera, with the front camera picture
            encrusted in the top-left corner
        ZAP_CHANNEL_VERT [2]:
            Broadcast video from the belly camera, showing the ground
        ZAP_CHANNEL_LARGE_HORI_SMALL_VERT [3]:
            Broadcast video from the front camera, with the belly camera
            encrusted in the top-left corner
        ZAP_CHANNEL_NEXT [4]:
            Switch to the next possible camera combination
        """
        self.send('ZAP', (mode,))
    
    def enable_autonomous_flight(self):
        """
        This makes the drone fly around and follow 2D tags the camera can detect.
        """
        self.send('AFLIGHT', (1,))
    
    def disable_autonomous_flight(self):
        """
        This makes the drone fly around and follow 2D tags the camera can detect.
        """
        self.send('AFLIGHT', (0,))
    
    def animate_leds(self, animation, frequency=0.5, duration=2):
        """
        This command makes the four motors leds blink with a predetermined
        sequence. The leds cannot be freely controlled by the user.
        
        0: ARDRONE_LED_ANIMATION_BLINK_GREEN_RED,
        1: ARDRONE_LED_ANIMATION_BLINK_GREEN,
        2: ARDRONE_LED_ANIMATION_BLINK_RED,
        3: ARDRONE_LED_ANIMATION_BLINK_ORANGE,
        4: ARDRONE_LED_ANIMATION_SNAKE_GREEN_RED,
        5: ARDRONE_LED_ANIMATION_FIRE,
        6: ARDRONE_LED_ANIMATION_STANDARD,
        7: ARDRONE_LED_ANIMATION_RED,
        8: ARDRONE_LED_ANIMATION_GREEN,
        9: ARDRONE_LED_ANIMATION_RED_SNAKE,
        10:ARDRONE_LED_ANIMATION_BLANK,
        11:ARDRONE_LED_ANIMATION_RIGHT_MISSILE,
        12:ARDRONE_LED_ANIMATION_LEFT_MISSILE,
        13:ARDRONE_LED_ANIMATION_DOUBLE_MISSILE,
        14:ARDRONE_LED_ANIMATION_FRONT_LEFT_GREEN_OTHERS_RED,
        15:ARDRONE_LED_ANIMATION_FRONT_RIGHT_GREEN_OTHERS_RED,
        16:ARDRONE_LED_ANIMATION_REAR_RIGHT_GREEN_OTHERS_RED,
        17:ARDRONE_LED_ANIMATION_REAR_LEFT_GREEN_OTHERS_RED,
        18:ARDRONE_LED_ANIMATION_LEFT_GREEN_RIGHT_RED,
        19:ARDRONE_LED_ANIMATION_LEFT_RED_RIGHT_GREEN,
        20:ARDRONE_LED_ANIMATION_BLINK_STANDARD,
        """
        self.send('LED', (animation, float(frequency), duration,))
    
    def animate(self, animation, duration=1):
        """
        Plays an animation, ie. a predetermined sequence of movements.
        Most of these movements are small movements (shaking for example)
        superposed to the user commands.
        
        0: ARDRONE_ANIMATION_PHI_M30_DEG,
        1: ARDRONE_ANIMATION_PHI_30_DEG,
        2: ARDRONE_ANIMATION_THETA_M30_DEG,
        3: ARDRONE_ANIMATION_THETA_30_DEG,
        4: ARDRONE_ANIMATION_THETA_20DEG_YAW_200DEG,
        5: ARDRONE_ANIMATION_THETA_20DEG_YAW_M200DEG,
        6: ARDRONE_ANIMATION_TURNAROUND,
        7: ARDRONE_ANIMATION_TURNAROUND_GODOWN,
        8: ARDRONE_ANIMATION_YAW_SHAKE,
        """
        self.send('ANIM', (animation, duration,))
    
    def reset_communications_watchdog(self):
        self.send('COMWDG')

def float2int(f):
    """
    Converts a float to a 32bit integer representation following IEEE-754
    
    >>> float2int(-0.8)
    -1085485875
    
    """
    return struct.unpack("=i", struct.pack("=f",f) )[0]
def int2float(i):
    """
    Converts a IEEE-754 32bit int representation of a float back to a float
    TODO: the reverse fails... maube just normal float rounding issues?
    >>> int2float(-1085485875)
    -0.800000011920929
    
     but should be
     
     -0.8
    """
    return struct.unpack("=f", struct.pack("=i",i) )[0]
