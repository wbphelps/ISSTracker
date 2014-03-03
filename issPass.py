# compute info about next ISS pass
# (c) Copyright 2014 William B. Phelps

from datetime import datetime, timedelta
import ephem
import math

au = 149597871 # Astronimical Unit (km)
    
def VisualMagnitude(iss, obs, sun):
  #iss.compute(self.obs)
  if iss.eclipsed or iss.alt<0: # eclipsed or not up
    return (100) #no valid mag data as the ISS is eclipsed (in the earths shadow)
  sun.compute(obs)
  # SSA Triangle.  We have side a and b and angle C.  Need to solve to find side c
  a = sun.earth_distance * au - ephem.earth_radius #distance sun from observer (Km)
  b = iss.range / 1000 # distance to ISS from observer (Km)
  angle_c = ephem.separation( (iss.az, iss.alt), ( sun.az, sun.alt) )
  c = math.sqrt( math.pow(a,2) + math.pow(b,2) - 2*a*b*math.cos( angle_c) )
  # now we find the "missing" angles (of which angle A is the one we need)
  angle_a = math.acos((math.pow(b,2) + math.pow( c,2) - math.pow(a,2)) / (2 * b * c)) # I think angle_a is the phase angle
  angle_b = math.pi - angle_a - angle_c #note: this is basically ZERO - not a big surprise really.
  phase_angle = angle_a # This is the angle we need.  BINGO!!
  
  # This is the MAGIC equation (Author: Matson, Robert)
  mag = -1.3 - 15 + 5*math.log10(iss.range/1000) - 2.5*math.log10(math.sin(phase_angle)+((math.pi-phase_angle)*math.cos(phase_angle)))
  return (mag)

class ISSPass:
# find the next ISS Pass and calculate the path for plotting

  def __init__(self, iss, obs, sun, interval = 15):

    self.iss = iss
    self.obs = obs
    self.sun = sun

    self.nightpass = False
    self.daytimepass = False
    self.beforesunrise = False
    self.aftersunset = False
    self.alwayseclipsed = True # in this pass is the ISS always eclipsed (in shadow)
    self.maxalt = 0 # max altitude for this pass
    self.maxmag = 100 # brightest magnitude for this pass
    self.visible = False  # is this a visible pass
    self.minrange = 20000  #will hold the closest distance to the observer

    self.iss.compute(self.obs)
#    print "self.obs.date: {}".format(self.obs.date)
#    print "iss alt: {}".format(math.degrees(self.iss.alt))

    if (self.iss.alt > 0): # is ISS up now?
      # ISS is up now - back up a bit so we can find this pass
      self.obs.date = ephem.Date(self.obs.date - 30.0 * ephem.minute)
      self.iss.compute(self.obs) # recompute ISS

    xtr, xazr, xtt, xaltt, xts, xazs = self.obs.next_pass(self.iss)
    self.risetime = xtr
    self.riseazi = xazr
    self.transittime = xtt
    self.transitalt = xaltt
    self.settime = xts
    self.setazi = xazs

    self.path = []

    self.obs.date = ephem.date(xtr) # set to time iss rises
#    print "self.obs.date: {}".format(self.obs.date)
    self.iss.compute(self.obs)
    #obs.horizon = '0'

    #self.obs.date = tr

    sr_prev = self.obs.previous_rising(ephem.Sun())
    ss_prev = self.obs.previous_setting(ephem.Sun())
    sr_next = self.obs.next_rising(ephem.Sun())
    ss_next = self.obs.next_setting(ephem.Sun())

    if ss_next < sr_next : # next sunset comes before next sun rise
      self.daytimepass = True # this does not account for twilight passes!
    elif sr_next < ss_next :
      self.nightpass = True
      if xtr-ss_prev > sr_next-xtr :
        self.beforesunrise = True
      else :
        self.aftersunset = True

    path = []

#    print "issPass: interval={}".format(interval)
    while xtr < xts : # get stats on this pass
      if not self.iss.eclipsed  :
        self.alwayseclipsed = False
      if self.iss.range/1000 < self.minrange:
        self.minrange = self.iss.range/1000
      if self.iss.alt > self.maxalt:
        self.maxalt = self.iss.alt
#      if self.daytimepass :
#         mag=100
#      else :
      mag=VisualMagnitude(self.iss, self.obs, self.sun)
      if mag < self.maxmag :
        self.maxmag = mag
        magLt = ephem.localtime(xtr)
        magLalt = self.iss.alt

      path.append((self.iss.alt,self.iss.az,mag))

      xtr = ephem.Date(xtr + ephem.second * interval) #wbp check every interval seconds
      self.obs.date = xtr
      self.iss.compute(self.obs)

    self.path = path
    del path

    if not self.alwayseclipsed and self.nightpass:
      self.visible = True
