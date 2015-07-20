import ConfigParser

class issOptions:

    def __init__(self):
        self.File = './issTracker.opt'
#        self.Location = '37.4388', '-122.1241' # note: strings for lat/lon
        self.Latitude = 0
        self.Longitude = 0
        self.BlinkStick = False
        self.GPS = False
        self.Display = 'PiTFT'
        self.Logging = False

    def load(self):

        # read & parse the configuration file
        config = ConfigParser.ConfigParser(allow_no_value=True)
        config.read(self.File)

        try:
            self.Latitude = config.getfloat('Location','latitude')
        except:
            self.Latitude = 37.4388

        try:
            self.Longitude = config.getfloat('Location','longitude')
        except:
            self.Longitude = -122.1241

        try:
            self.BlinkStick = config.getboolean('Options', 'blinkstick')
        except:
            pass

        try:
            self.GPS = config.getboolean('Options', 'gps')
        except:
            pass

        try:
            self.Logging = config.getboolean('Options', 'logging')
        except:
            pass

    def saveAll(self):

        config = ConfigParser.ConfigParser()
        config.add_section('Location')
        config.set('Location','latitude', self.Latitude)
        config.set('Location','longitude', self.Longitude)
        config.add_section('Options')
        config.set('Options','blinkstick', self.BlinkStick)
        config.set('Options','gps', self.GPS)
        config.set('Options','display', self.Display)
        config.set('Options','logging', self.Logging)
        cfgfile = open(self.File,'wb')
        config.write(cfgfile)
        cfgfile.close()

    def saveLocation(self):

        config = ConfigParser.ConfigParser()
        config.read(self.File)
#        config.add_section('Location')
        config.set('Location','latitude', self.Latitude)
        config.set('Location','longitude', self.Longitude)
        with open(self.File,'wb') as cfgfile:
            config.write(cfgfile)


if __name__ == '__main__':

  opt = issOptions()
  opt.load()
  print "Location {}".format(opt.Latitude, opt.Longitude)
  print "Logging {}".format(opt.Logging)
  print "Blinkstick {}".format(opt.BlinkStick)
  print "GPS {}".format(opt.GPS)

  opt.saveAll()

#  opt.Latitude = 37.4567
#  opt.saveLocation()
