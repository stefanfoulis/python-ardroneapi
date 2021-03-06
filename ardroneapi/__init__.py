import socket
import struct
import pprint

class Drone(object):
    """
    Preperation:
        You must be connected to the ad-hoc network of the AR.Drone. Check if
        the drone can be pinged and if you can connect to it via telnet.
        By default the drone will be at 192.168.1.1 and will assign your
        computer the ip 192.168.1.2.
    
    If you've not changed anything you can go right ahead and create an instance 
    of ``Drone`` without any parameters:
    
    >>> d = Drone()
    >>> d.connect() # initiates the socket
    >>> d.animate_leds(13) # makes the leds blink.
    >>> d.flat_trims() # INPORTANT!: calibrate drone (make sure it is on a flat horizontal surface)
    >>> d.takeoff()
    >>> d.land()
    
    """
    cmd_port = 5556
    nav_port = 5554
    cfg_port = 5559
    
    def __init__(self, drone_ip=None, local_ip=None, multicast_ip=None):
        self._sequence = 0
        self.drone_ip = drone_ip or '192.168.1.1'
        self.local_ip = local_ip or '192.168.1.2'
        self.multicast_ip = multicast_ip or '224.1.1.1'
        
        self.cmd_socket = None
        self.nav_socket = None
    
    def connect(self):
        self.connect_cmd()
    
    def disconnect(self):
        self.disconnect_cmd()
    
    def connect_cmd(self):
        s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        s.bind( (self.local_ip, self.cmd_port))
        s.connect( (self.drone_ip, self.cmd_port) )
        self.cmd_socket = s
    
    def disconnect_cmd(self):
        self.cmd_socket.close()
        self.cmd_socket = None
    
    def connect_nav(self):
        # make sure we get detailed data
        self.activate_detailed_navdata()
        
        # this "pokes" the drone to initiate the transfer of navdata
        p = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        p.bind( (self.local_ip, self.nav_port) )
        p.sendto('\0',
                 (self.drone_ip, self.nav_port))
        p.close()
        
        # create the socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # allow multipleprocesses to use this port
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind it to the port
        s.bind(('', self.nav_port))
        # join IGMPv2 group
        group_bin = socket.inet_aton(self.multicast_ip)
        iface_bin = socket.inet_aton(self.local_ip)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, 
                     group_bin + iface_bin)
        self.nav_socket = s
        
        # TODO: this should run in a separate thread or using callbacks to
        #       prevent blocking
        while True:
            data, sender = s.recvfrom(100)
            print "<<<====="
            print str(sender)
            print repr(data)
            n = NavigationData(data)
            print "=====>>>"
        self.disconnect_nav()
    
    def disconnect_nav(self):
        # TODO: can we tell the drone to stop sending navdata somehow?
        self.nav_socket.clos()
        self.nav_socket = None
    
    
    def sequence(self):
        self._sequence += 1
        return self._sequence
    
    def raw_send(self, data):
        '''
        sends the raw data to the drone
        '''
        if not self.cmd_socket:
            raise Exception("Not connected yet!")
        print "sending..."
        print data
        self.cmd_socket.send(data)
    
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
        params_str = ','.join([str(self.sequence())] + params2)
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
    
    #===========================================================================
    # drone control commands
    #===========================================================================
    
    def takeoff(self):
        """
        If no other command is supplied, the drone enters a hovering mode and
        stays still at approximately 1 meter above ground.
        """
        #self.send('REF', ('290718208',))
        self.send('REF', ('512',))
    
    def land(self):
        """
        The drone lands and turns off its motors.
        """
        #self.send('REF', ('290717696',))
        self.send('REF', ('0',))
    
    def emergency(self):
        """
        Engines are cut-off no matter the drone state. (ie. the drone crashes, 
        potentially violently).
        
        Emergency (bit 8): 1
        Takeoff (bit 9)  : 0
        
        """
        self.send_many([('REF', ('0',)),('REF', ('256',)),('REF', ('0',))])
    
    def recover(self):
        """
        revovers from the emergency
        
        Emergency (bit 8): 0
        Takeoff (bit 9)  : 0
        """
        self.send('REF', ('0',))
    
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
    
    #===========================================================================
    # config commands
    #===========================================================================
    
    def activate_detailed_navdata(self):
        self.set_config('general:navdata_demo', True)
    
    def set_config(self, name, value):
        """
        name: the name of the value to set
        value: the value of the configuration
        """
        if value:
            value = '"TRUE"'
        else:
            value = '"FALSE"'
        self.raw_send(self.build_raw_command(
                        'CONFIG', 
                        ('"%s"' % name, value,))
        )
    
    def get_config(self):
        """
        config data is sent via TCP
        """
        NO_CONTROL_MODE = 0
        ARDRONE_UPDATE_CONTROL_MODE = 1
        PIC_UPDATE_CONTROL_MODE = 2
        LOGS_GET_CONTROL_MODE = 3
        CFG_GET_CONTROL_MODE = 4
        ACK_CONTROL_MODE = 5
        
        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        #s.bind( (self.local_ip, 5559,) )
        s.connect( (self.drone_ip, self.cfg_port,) )
        #s.send('USER anonymous')
        #s.send(self.build_raw_command('CTRL', (4,)))
        
        # tell to send config via udp
        self.send('CTRL', (CFG_GET_CONTROL_MODE,0,))
        
        config = []
        while True:
            data, address = s.recvfrom( 1024 )
            print data
            print address
            print '======'
            if not data:
                break
            config.append(data)
        config = ''.join(config)
        lines = config.split('\n')
        cfg = {}
        for line in lines:
            if '=' in line:
                key, value = line.split('=')
                key = key.strip()
                value = value.strip()
                cfg[key] = value
        pprint.pprint(cfg)

class NavigationData(object):
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.unpack()
    
    def unpack_state(self, state):
        '''
        state is a bit field representing ARDrone' state
        
        Define masks for ARDrone state
        31                                                             0
         x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x -> state
         | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
         | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | FLY MASK : (0) ardrone is landed, (1) ardrone is flying
         | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | VIDEO MASK : (0) video disable, (1) video enable
         | | | | | | | | | | | | | | | | | | | | | | | | | | | | | VISION MASK : (0) vision disable, (1) vision enable
         | | | | | | | | | | | | | | | | | | | | | | | | | | | | CONTROL ALGO : (0) euler angles control, (1) angular speed control
         | | | | | | | | | | | | | | | | | | | | | | | | | | | ALTITUDE CONTROL ALGO : (0) altitude control inactive (1) altitude control active
         | | | | | | | | | | | | | | | | | | | | | | | | | | USER feedback : Start button state
         | | | | | | | | | | | | | | | | | | | | | | | | | Control command ACK : (0) None, (1) one received
         | | | | | | | | | | | | | | | | | | | | | | | | Trim command ACK : (0) None, (1) one received
         | | | | | | | | | | | | | | | | | | | | | | | Trim running : (0) none, (1) running
         | | | | | | | | | | | | | | | | | | | | | | Trim result : (0) failed, (1) succeeded
         | | | | | | | | | | | | | | | | | | | | | Navdata demo : (0) All navdata, (1) only navdata demo
         | | | | | | | | | | | | | | | | | | | | Navdata bootstrap : (0) options sent in all or demo mode, (1) no navdata options sent
         | | | | | | | | | | | | | | | | | | | | Motors status : (0) Ok, (1) Motors Com is down
         | | | | | | | | | | | | | | | | | |
         | | | | | | | | | | | | | | | | | Bit means that there's an hardware problem with gyrometers
         | | | | | | | | | | | | | | | | VBat low : (1) too low, (0) Ok
         | | | | | | | | | | | | | | | VBat high (US mad) : (1) too high, (0) Ok
         | | | | | | | | | | | | | | Timer elapsed : (1) elapsed, (0) not elapsed
         | | | | | | | | | | | | | Power : (0) Ok, (1) not enough to fly
         | | | | | | | | | | | | Angles : (0) Ok, (1) out of range
         | | | | | | | | | | | Wind : (0) Ok, (1) too much to fly
         | | | | | | | | | | Ultrasonic sensor : (0) Ok, (1) deaf
         | | | | | | | | | Cutout system detection : (0) Not detected, (1) detected
         | | | | | | | | PIC Version number OK : (0) a bad version number, (1) version number is OK
         | | | | | | | ATCodec thread ON : (0) thread OFF (1) thread ON
         | | | | | | Navdata thread ON : (0) thread OFF (1) thread ON
         | | | | | Video thread ON : (0) thread OFF (1) thread ON
         | | | | Acquisition thread ON : (0) thread OFF (1) thread ON
         | | | CTRL watchdog : (1) delay in control execution (> 5ms), (0) control is well scheduled // Check frequency of control loop
         | | ADC Watchdog : (1) delay in uart2 dsr (> 5ms), (0) uart2 is good // Check frequency of uart2 dsr (com with adc)
         | Communication Watchdog : (1) com problem, (0) Com is ok // Check if we have an active connection with a client
         Emergency landing : (0) no emergency, (1) emergency
        '''
        
        desc = {
            0: ('flying', 'ardrone is landed', 'ardrone is flying'),
            1: ('video', 'video disabled', 'video enabled'),
            2: ('vision', 'vision disabled', 'vision enabled'),
            10: ('navdata_demo', 'all navdata', 'only navdata demo'),
            26: ('navdata', 'navdata thread is ON', 'navdata thread is OFF'),
            31: ('emergency', 'no emergency', 'emergency'),
        }
        values = {}
        bits = str(bin(state)).lstrip('-b0')
        # reverse the bitmask
        print bits
        bits = bits[::-1]
        print bits
        for thebit in range(0,31):
            try:
                s = bits[thebit]
                if s == '1':
                    s = True
                else:
                    s = False
                d = desc.get(thebit, None)
                if not d is None:
                    if s:
                        print d[0], d[2]
                    else:
                        print d[0], d[1]
            except IndexError:
                pass
    
    
    def unpack(self):
        '''
        Exact-width integer types
        
        Integer types having exactly the specified width
        typedef signed char int8_t
        typedef unsigned char uint8_t
        typedef signed int int16_t
        typedef unsigned int uint16_t
        typedef signed long int int32_t
        typedef unsigned long int uint32_t
        typedef signed long long int int64_t
        typedef unsigned long long int uint64_t
        
        
        Header:
        HEADER      State     Seq       Vision
        uint32_t    uint32_t  uint32_t  bool_t
        
        
        
        Checksum:
        TAG        SIZE        CKS
        uint16_t   uint16_t    uint32_t
        
        
        
        '''
        r = self.raw_data
        header = r[:13]
        checksum = r[-12:]
        options = r[13:-12]
        print 'length: %s (header: %s, options: %s, checksum: %s)' % (len(r), 
                                                                      len(header), 
                                                                      len(options),
                                                                      len(checksum),)
        print 'correct?: ', len(r), '==', len(header)+len(options)+len(checksum)
        
        h, state, seq, vision = struct.unpack('<LLL?', header)
        print 'header: %s %s %s %s' % (hex(h), bin(state), seq, vision)
        self.unpack_state(state)
        cks_id, size, chks_data = struct.unpack('<IIL', checksum)
        print 'checksum: %s %s %s' % (cks_id, size, chks_data)
        has_more = True
        o = options[:]
        while has_more:
            tag, size = struct.unpack('<II', o[:8])
            size_bytes = size/8
            rest = o[4:size_bytes]
            print tag, size, repr(rest)
            o = o[4+size_bytes:]
            if not len(o):
                has_more = False
#        opt1, s1 = struct.unpack('<hh', options[:4])
#        print 'id: %s size: %s' % (opt1, s1)

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
