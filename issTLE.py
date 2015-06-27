#!/usr/bin/python
import ConfigParser
import urllib2
from datetime import datetime, timedelta
from checkNet import checkNet

class issTLE:

    def __init__(self):
        self.tleFile = './isstle.tle'
        self.dataFile = './isstle.data'
        self.tle = ('no data', '', '')
        self.date = datetime(1999, 1, 1)
        self.type = "NASA"
        self.url = "http://spaceflight.nasa.gov/realdata/sightings/SSapplications/Post/JavaSSOP/orbit/ISS/SVPOST.html"

    def load_default(self) :
        self.tle = ('ISS (ZARYA)',
          '1 25544U 98067A   14036.54124330  .00016717  00000-0  10270-3 0  9003',
          '2 25544  51.6460  32.1708 0003756 100.5179 259.6395 15.50067791 30901')
        self.date = datetime(2014, 2, 6) + timedelta(days=0.54124330)

    def load(self) :

        # parse the TLE data from isstle.tle file
        config = ConfigParser.ConfigParser()
        config.read(self.tleFile)

        try :
            self.tle = config.get('TLE','line1',0), config.get('TLE','line2',0), config.get('TLE','line3',0)

        except :
            print "Error loading TLE data from file. recreating " + self.tleFile
#            logging.warning( 'Error loading TLE data from file.  recreating ' + self.tleFile )
            self.load_default()
            self.save()

        try :
#            self.date = datetime.strptime(config.get( 'TLE', 'date', 0), '%b %d %Y')
            self.date = datetime.strptime(config.get( 'TLE', 'date', 0), '%Y-%m-%d %H:%M:%S')
        except :
            print "old TLE data"
#            logging.warning('The ISS TLE data is the default and could be very old')
            self.date = datetime.now() + timedelta(days=-30)

    def save(self) :  # save a single TLE file
        config = ConfigParser.ConfigParser()
        config.add_section('TLE')
        config.set('TLE', 'line1', self.tle[0])
        config.set('TLE', 'line2', self.tle[1])
        config.set('TLE', 'line3', self.tle[2])
        config.set('TLE', 'date', self.date.strftime('%Y-%m-%d %H:%M:%S'))
        with open(self.tleFile, 'wb') as file:
            config.write(file)

    def clear(self) :  # empty the TLE data file
        config = ConfigParser.ConfigParser()
        with open(self.dataFile, 'wb') as file:
            config.write(file)

    def append(self) :  # append TLE to the data file
        config = ConfigParser.ConfigParser()
        config.add_section('TLE')
        config.set('TLE', 'line1', self.tle[0])
        config.set('TLE', 'line2', self.tle[1])
        config.set('TLE', 'line3', self.tle[2])
        config.set('TLE', 'date', self.date.strftime('%Y-%m-%d %H:%M:%S'))
        with open(self.dataFile, 'a+b') as file:
            config.write(file)


    def fetch(self, date=datetime.now()) :  # fetch TLE data from web

        try:
            net = checkNet()
#            print 'net.up {}'.format(net.up)
            if not net.up:
                print "issTLE: No available network"
                return False

            page = urllib2.urlopen(self.url, None, 30) # 30 second timeout
            data = page.read()

            if (self.type == 'NASA'):
                self.clear()  # clear TLE data file
                i1 = 1
#                doy = datetime.now().strftime("%y%j") # epoch year and day for today
                doy = date.strftime("%y%j") # epoch year and day for today
                print "day={}".format(doy)

                while (i1>0) and i1 < len(data):
                    i1 = data.find('TWO LINE MEAN ELEMENT SET', i1)
                    print "i1={}".format(i1)
                    if i1<0: break # we probably went off the end, use the last one
                    i1 = data.find('ISS', i1)
                    if i1<0: break # we probably went off the end, use the last one
                    tle = data[i1:i1+200]
                    tle = tle.split("\n") # then split it into lines
                    print tle
                    tle[0] = tle[0] + ' (NASA)' # show where data is from
                    tle = [s.lstrip() for s in tle]
                    toks = tle[1].split() # split line 2 into tokens
                    tdoy = toks[3].split('.')[0]  # get epoch year and day
                    print tdoy
                    td = toks[3].split('.')
                    print td
                    self.date = datetime.strptime(td[0],"%y%j") + timedelta(days=float('.'+td[1]))
                    print self.date
                    self.tle = tle[0], tle[1], tle[2] # first three lines are what we need
                    self.append()
                    print "appended..."

                    if (tdoy == doy): # if it matches, we found what we came for
                        print "saving..."
                        self.save()

            else: # assume 'celestrak', just take the first set
                tle = data.split("\n") # then split it into lines

            self.tle = tle[0], tle[1], tle[2] # first three lines are what we need
            toks = tle[1].split() # split line 2 into tokens
            td = toks[3].split('.')
            self.date = datetime.strptime(td[0],"%y%j") + timedelta(days=float('.'+td[1]))
            return True

        except:
            print "Error"
            self.tle = ('no data', '', '')
            self.date = datetime(1999, 1, 1)
            return False

if __name__ == '__main__':
    
    import ephem, math

    # set up observer location
    obs = ephem.Observer()
    obs.lat = math.radians(37.4388)
    obs.lon = math.radians(-122.124)

    tNow = datetime.utcnow()
    obs.date = tNow

    ISS_TLE = issTLE()
    ISS_TLE.load()

    print 'fetching TLEs'
    rc = ISS_TLE.fetch()
    if rc:
        ISS_TLE.load()
        ISS_TLE.save()

    iss = ephem.readtle(ISS_TLE.tle[0], ISS_TLE.tle[1], ISS_TLE.tle[2] )
    iss.compute(obs)
    print obs.next_pass(iss)

