import time, serial, sys
from datetime import datetime, timedelta
import threading
import math

''' NMEA Message formats

  $GPRMC,225446.000,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3,E*68\r\n
  225446       Time of fix 22:54:46 UTC
  A            Navigation receiver warning A = OK, V = warning
  4916.45,N    Latitude 49 deg. 16.45 min North
  12311.12,W   Longitude 123 deg. 11.12 min West
  000.5        Speed over ground, Knots
  054.7        Course Made Good, True
  191194       Date of fix 19 November 1994
  020.3,E      Magnetic variation 20.3 deg East
  *68          mandatory checksum

  $GPGSV,3,1,11,03,03,111,00,04,15,270,00,06,01,010,00,13,06,292,00*74
  $GPGSV,3,2,11,14,25,170,00,16,57,208,39,18,67,296,40,19,40,246,00*74
  $GPGSV,3,3,11,22,42,067,42,24,14,311,43,27,05,244,00,,,,*4D

  1    = Total number of messages of this type in this cycle
  2    = Message number
  3    = Total number of SVs in view
  4    = SV PRN number
  5    = Elevation in degrees, 90 maximum
  6    = Azimuth, degrees from true north, 000 to 359
  7    = SNR, 00-99 dB (null when not tracking)
  8-11 = Information about second SV, same as field 4-7
  12-15= Information about third SV, same as field 4-7
  16-19= Information about fourth SV, same as field 4-7

'''

def tz_offset():
  #Return offset of local zone from GMT
  t = time.time()
  if time.localtime(t).tm_isdst and time.daylight:
    return -time.altzone
  else:
    return -time.timezone

# check serial port???
#port = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=3.0)
#port = serial.Serial("/dev/ttyUSB0", baudrate=4800, timeout=3.0)

class satInfo():
  def __init__(self,svn,alt,azi,snr):
    self.svn = svn # SV PRN
    self.alt = alt # altitude
    self.azi = azi # azimuth
    self.snr = snr # S/N ratio

class pyGPS():

  def __init__(self,device='/dev/ttyAMA0',baudrate=9600,timeout=3.0):
    self.device = device
    self.baudrate = baudrate
    self.timeout = timeout
    self.running = False
    self._run = False
    self.statusOK = False
    self.status = 'x' # 'A' or 'V'
    self.satellites = []
    self.lock = threading.Lock()
    self.latitude = 0
    self.longitude = 0
    self.datetime = None
    self.port = serial.Serial(self.device,baudrate=self.baudrate, timeout=self.timeout)
    self.rcv = '' # buffer
    self.i = 0 # buffer index
    self.error = ''

  def check(self,rcv):
    # calculate checksum
    chk1 = 0
    i = 0
    for ch in rcv:
      if (ch == '*'):
        break
      chk1 = chk1 ^ ord(ch)
      i += 1
    chk2 = int(rcv[i+1:i+3],16)
#    print("chk1:" + hex(chk1) + " chk2:" + hex(chk2))
    if (chk1 != chk2):
      print "Checksum error"
      return False
    else:
      return True

  def ntok(self):
    i2 = self.rcv.find(',', self.i) # find next comma
    if (i2 < 0): return ''
    tk = self.rcv[self.i:i2]
    self.i = i2 + 1
    return tk

  def getGPS(self):
    with self.lock:
      if self.running:
        print "bl: error already running"
        return
      self.running = True
    sats = []
    while self._run:
      self.rcv = self.port.readline()
      try:
        if (self.rcv[:7] == '$GPGSV,'): # satellite info
          self.rcv = self.rcv[1:] # remove $
#          print("rcv:" + repr(self.rcv))
          if self.check(self.rcv):
            self.i = 6 # start at 1st token
            nmsgs = self.ntok()
            msgn = self.ntok()
            nsats = self.ntok()
            if (msgn == "1"):
              sats = []
            while True:
              svn = self.ntok()
              if (not svn.isdigit()):
                break;
#              print 'i: {}, svn: {}'.format(self.i,svn)
              alt, azi, snr = 0,0,0
              talt = self.ntok()
              if talt.isdigit(): alt = int(talt)
              tazi = self.ntok()
              if tazi.isdigit(): azi = int(tazi)
              tsnr = self.ntok()
              if tsnr.isdigit(): snr = int(tsnr)
              sats.append(satInfo(svn,math.radians(alt),math.radians(azi),snr))
            if (msgn == nmsgs): # last gpgsv message?
#              s1 = ""
#              ns = 0
#              for sat in sats:
#                if (sat.snr>0):
#                  ns += 1
#                  s1 = s1 + "{}:{},{},{}, ".format(sat.svn,sat.alt,sat.azi,sat.snr)
#              print('{:0>2}/{:2} sats {!s}'.format(ns, nsats, s1))
              with self.lock:
                self.satellites = sats
        if (self.rcv[:7] == '$GPRMC,'): # required miminum 
          self.rcv = self.rcv[1:] # remove $
#          print("rcv:" + repr(self.rcv))
          if self.check(self.rcv): # check checksum
            self.i = 6 # start at 1st token
            gtime = self.ntok()[:6]
            self.status = self.ntok()
#            print ("status: " + self.status)
            lat = self.ntok()
            if lat.replace('.','',1).isdigit():
              lat = float(lat)
              lat = lat//100 + (lat%100)/60.0
            else:
              lat = 0
            latD = self.ntok()
            if latD == 'S': lat = -lat
            lon = self.ntok()
            if lon.replace('.','',1).isdigit():
              lon = float(lon)
              lon = lon//100 + (lon%100)/60.0
            else:
              lon = 0
            lonD = self.ntok()
            if lonD == 'W': lon = -lon
            spd = self.ntok()
            crs = self.ntok()
            gdate = self.ntok()
            mag = self.ntok()
            dt = datetime.strptime(gdate+gtime, "%d%m%y%H%M%S") + timedelta(seconds=tz_offset())
#            print("status: {}, lat: {}, lon: {}, time: {}".format(self.status, lat, lon, dt))
            with self.lock:
              self.statusOK = False
              self.lat = math.radians(lat)
              self.lon = math.radians(lon)
              self.datetime = dt
              if self.status == 'A':
                self.statusOK = True
      except:
        print self.rcv
        print ("Error: "),sys.exc_info()[0]
        self.error = format(sys.exc_info()[0])
        raise
    print 'GPS stop'  

  def start(self):
    with self.lock:
      if self.running == False:
#        print "bl: start thread"
        self._run = True
        self.thread = threading.Thread(target = self.getGPS)
        self.thread.start()

  def stop(self):
    with self.lock:
      self._run = False # stop loop

