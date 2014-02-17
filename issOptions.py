import ConfigParser

class isspitftOptions:

    def __init__(self):
        self.configFile = '/home/pi/isspitft/isspitft.conf'
        self.minAlt = 0.0
        self.metric = False
        self.location = 'Palo Alto, CA', '37.4388', '-122.1241' # note: strings for lat/lon
        self.daysToRefresh = 1
        self.blinkstick = False
        self.displayDevices = []
        self.tletype = "NASA"
        self.tleurl = "http://spaceflight.nasa.gov/realdata/sightings/SSapplications/Post/JavaSSOP/orbit/ISS/SVPOST.html"
        self.logging = False


    def load(self):
        # read & parse the main issoptions file.
        options = ConfigParser.ConfigParser(allow_no_value=True)
        options.read( self.configFile )

        try :
            self.location = options.get('Location','city',0), options.get('Location','lat', 0), options.get('Location','lon', 0)
        except :
            self.location = 'unspecified location', '37.4388', '-122.1241'

        try :
             self.issTleType = options.get('isstle', 'isstletype', 0)
             #print 'ISS TLE Type: ', self.isstletype
        except :
             pass

        try :
             self.issTleUrl = options.get('isstle', 'isstleurl', 0)
             #print 'ISS TLE URL: ', self.isstleurl
        except :
             pass

        try :
             self.daysToRefresh = options.getint('options','daystorefresh')
        except :
             self.daysToRefresh = 5

        try:
            self.minAlt = options.getfloat('options','minalt')
            #print 'Minimum Altitude to process: ', self.minAlt
        except :
            pass

        try :
            self.metric = options.getboolean('options', 'metric')
        except :
            pass

        try :
            self.logging = options.getboolean('options', 'logging')
        except :
            pass

        try:
            self.displayDevices = options.items('DisplayDevices')
            #print 'display Devices: ', self.displayDevices
            for display, value in self.displayDevices :
                elif display == 'blinkstick' :
                    self.blinkstick = True
                    #print 'BlinkStick'
        except:
            pass

