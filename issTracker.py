#!/usr/bin/python

# PiTFT display engine for ISS-Tracker
# This must run as root (sudo python lapse.py) due to framebuffer, etc.
#
# http://www.adafruit.com/products/998  (Raspberry Pi Model B)
# http://www.adafruit.com/products/1601 (PiTFT Mini Kit)
#
# Prerequisite tutorials: aside from the basic Raspbian setup and PiTFT setup
# http://learn.adafruit.com/adafruit-pitft-28-inch-resistive-touchscreen-display-raspberry-pi
#
# (c) Copyright 2014 William B. Phelps

import wiringpi2
import atexit
import errno
import os, sys, signal
import pygame
from pygame.locals import *
from time import sleep
from datetime import datetime, timedelta
import ephem, ephem.stars
import math
from issPass import ISSPass, VisualMagnitude
import logging
import threading
from blinkstick import blinkstick
from issTLE import issTLE

atexit.register(exit)

# -------------------------------------------------------------

iconPath = 'icons' # Subdirectory containing UI bitmaps (PNG format)
backlightpin = 252

col1 = 16
col2 = 115

lsize = 28
line0 = 15
line1 = 20+lsize
line2 = line1+lsize
line3 = line2+lsize
line4 = line3+lsize
line5 = line4+lsize
line6 = line5+lsize

#iss = { "Type": 'Daytime', "Mag": -3.2, "Range": 1234, "Time": datetime.now()+timedelta(seconds=300) }

obs = ephem.Observer()
obs.lat = '37.4388'
obs.lon = '-122.124'

realTime = True
realTime = False
stime = 1
#stime = 0.5  # 2x normal speed
#stime = 0.2 # 5x speed
stime = 0.1 # 10x speed

tNow = datetime.utcnow()
tNow = datetime(2014, 2, 6, 3, 3, 0) # 1 minute before ISS is due
#tNow = datetime(2014, 2, 6, 3, 0, 0) # 2 minutes before ISS is due
#tNow = datetime(2014, 2, 13, 0, 34, 39) # 1 minute before ISS is due
#tNow = datetime(2014, 2, 13, 22, 13, 40) # 1 minute before ISS is due
#tNow = datetime(2014, 2, 13, 0, 35, 9) # 1 minute before ISS is due
#tNow = datetime(2014, 2, 14, 1, 22, 0) # 1 minute before ISS is due
#tNow = datetime(2014, 2, 14, 6, 18, 0) # test midpass startup
#tNow = datetime(2014, 2, 16, 23, 1, 0) # just before ISS is due
#tNow = datetime(2014, 2, 16, 23, 1, 0) # just before ISS is due

obs.date = tNow
sun = ephem.Sun(obs)

#iss_tle = ('ISS (ZARYA)', 
#  '1 25544U 98067A   14043.40180105  .00016203  00000-0  28859-3 0  6670',
#  '2 25544  51.6503 358.1745 0004087 127.2033  23.9319 15.50263757871961')

#iss_tle = ('ISS (NASA)',
#  '1 25544U 98067A   14044.53508303  .00016717  00000-0  10270-3 0  9018',
#  '2 25544  51.6485 352.5641 0003745 129.1118 231.0366 15.50282351 32142')
#date = Feb 13 2014

#iss_tle = ('ISS (NASA)',
#   '1 25544U 98067A   14047.37128447  .00016717  00000-0  10270-3 0  9021',
#   '2 25544  51.6475 338.5079 0003760 140.1188 220.0239 15.50386824 32582')
#date = Feb 16 2014

tle = issTLE()
tle.load()
if (datetime.now()-tle.date) > timedelta(days=1):
    tle.fetch()
    tle.save()


iss = ephem.readtle(tle.tle[0], tle.tle[1], tle.tle[2] )
iss.compute(obs)
print obs.next_pass(iss)

#print "alt: {}".format(math.degrees(iss.alt))
#print "azi: {}".format(math.degrees(iss.az))

#obs.date = datetime(2014, 2, 13, 0, 36, 30) # 1 minute later
#obs.date = tNow + timedelta(seconds=30)
#iss.compute(obs)
#print "alt: {}".format(math.degrees(iss.alt))
#print "azi: {}".format(math.degrees(iss.az))


# ---------------------------------------------------------------
def signal_handler(signal, frame):
    global blinkstick_on, blt
    print 'SIGNAL {}'.format(signal)
    sleep(1)
    pygame.quit()
    if blinkstick_on:
      blt.stop()
    sys.exit(0)

def exit():
  print "Exit"
  sleep(1)
  pygame.quit()

def backlight(set):
    os.system("echo 252 > /sys/class/gpio/export")
    os.system("echo 'out' > /sys/class/gpio/gpio252/direction")
    if (set):
#        gpio.digitalWrite(backlightpin,gpio.LOW)
        os.system("echo '1' > /sys/class/gpio/gpio252/value")
    else:
#        gpio.digitalWrite(backlightpin,gpio.HIGH)
        os.system("echo '0' > /sys/class/gpio/gpio252/value")

def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;


class BlinkStick():

  def __init__(self, mag, alt, count=1):
    self.mag = mag
    self.alt = alt
    self.bstick = blinkstick.find_first()
    self.running = False
    self.thread = 0
    self.count = 10
    self._run = False

  def blink(self, count=-1):
    if self.running:
      print "bl: error already running"
    self.running = True
    repeat=1
    steps = 10
    if count>0:
      self.count = count
#    print "blink {}".format(self.count)
    while self._run and self.count>0:
      dm = map(self.mag, 0, -6, 4, 255)
      if (dm>255): dm = 255
      if (dm<0): dm = 4
      da = map(self.alt, 0, 90, 500, 33)
#      print "bl mag: {:3.1f} alt: {:3.1f} dm:{:3.0f} da:{:3.0f}".format(self.mag,self.alt,dm,da)
      self.bstick.pulse(dm,0,0,None,None,repeat,da,steps)
      self.bstick.pulse(0,dm,0,None,None,repeat,da,steps)
      self.bstick.pulse(0,0,dm,None,None,repeat,da,steps)
      self.count -= 1
    self.bstick.turn_off()
    self.running = False
#    print "bl: stop"

  def set(self, mag, alt, count=1):
    self.alt = alt
    self.mag = mag
    self.count = count

  def start(self):
    if self.running == False:
#      print "bl: start thread"
      self._run = True
      self.thread = threading.Thread(target = self.blink)
      self.thread.start()

  def stop(self):
    self._run = False # stop loop
    while self.running :
      sleep(0.1)

# ---------------------------------------------------------------------

# Init framebuffer/touchscreen environment variables
os.putenv('SDL_VIDEODRIVER', 'fbcon')
os.putenv('SDL_FBDEV'      , '/dev/fb1')
os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
os.putenv('SDL_MOUSEDEV'   , '/dev/input/touchscreen')


# Set up GPIO pins
print "Init GPIO pins..."
gpio = wiringpi2.GPIO(wiringpi2.GPIO.WPI_MODE_GPIO)  
#gpio.pinMode(backlightpin,gpio.OUTPUT)  

# Init pygame and screen
print "Initting..."
pygame.init() 

print "Setting Mouse invisible..."
pygame.mouse.set_visible(False)
print "Setting fullscreen..."
size = pygame.display.list_modes(16)[0] # get screen size
print "size:"
print size

#screen = pygame.display.set_mode(size, FULLSCREEN, 16)
screen = pygame.display.set_mode(size)
(width, height) = size
print "set mode"

backlight(True)
print "backlight"

bg = pygame.image.load("ISSTracker.png")
bgRect = bg.get_rect()
screen.blit(bg, bgRect)
pygame.display.update()
sleep(1)

def getxy(alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r90 = math.radians(90) # 90 degrees in radians
    r = (r90 - alt)/r90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    x = int(160 - x * 120) # flip E/W, scale to radius, center on plot
    y = int(120 - y * 120) # scale to radius, center on plot
    return (x,y)

def plotstar(name, screen, obs):
    star = ephem.star(name)
    star.compute(obs)
    if star.alt > 0:
      pygame.draw.circle(screen, (255,255,255), getxy(star.alt, star.az), 1, 1)

def plotplanet( planet, obs, screen, color, size):
#    planet = ephem.Mercury()
    planet.compute(obs)
#    print "{} alt: {} az:{}".format(planet.name, math.degrees(planet.alt), math.degrees(planet.az))
    if (planet.alt>0):
      pygame.draw.circle(screen, color, getxy(planet.alt, planet.az), size, 0)


def setupInfo():
# Setup fixed parts of screen
    global bg, bgRect

    bg = pygame.image.load("ISSTrackerDim.png")

    txtColor = (255,0,0)
    txtFont = pygame.font.SysFont("Arial", 30, bold=True)
    txt = txtFont.render("ISS Tracker" , 1, txtColor)
    bg.blit(txt, (15, line0))

    txtColor = (255,63,0)
    txtFont = pygame.font.SysFont("Arial", 26, bold=True)
    txt = txtFont.render("Start: " , 1, txtColor)
    bg.blit(txt, (col1, line1))
    txt = txtFont.render("Type:  " , 1, txtColor)
    bg.blit(txt, (col1, line2))
    txt = txtFont.render("Mag:   " , 1, txtColor)
    bg.blit(txt, (col1, line3))
    txt = txtFont.render("Alt:   " , 1, txtColor)
    bg.blit(txt, (col1, line4))
    txt = txtFont.render("Range: " , 1, txtColor)
    bg.blit(txt, (col1, line5))
    txt = txtFont.render("Due in:" , 1, txtColor)
    bg.blit(txt, (col1, line6))

    screen.blit(bg, bgRect)
    pygame.display.update()

def showInfo(tNow, issp, obs, iss, sun):
    global bg, bgRect

    txtColor = (255,0,0)
    txtFont = pygame.font.SysFont("Arial", 26, bold=True)
    screen.blit(bg, bgRect) # write background image

    t1 = ephem.localtime(tr).strftime('%b %d %H:%M:%S')
    txt = txtFont.render(t1 , 1, txtColor)
    screen.blit(txt, (col2, line1))

    if issp.daytimepass:
        txt = "Daytime"
    elif issp.nightpass and issp.beforesunrise:
        txt = "Morning"
    elif issp.nightpass and issp.aftersunset:
        txt = "Evening"
    txt = txtFont.render(txt , 1, txtColor)
    screen.blit(txt, (col2, line2))

    if (issp.maxmag>99):
      txt = '---'
    else:
      txt = "{:0.1f}".format(issp.maxmag)
    txt = txtFont.render(txt, 1, txtColor)
    screen.blit(txt, (col2, line3))

    txt = txtFont.render("{:0.0f}".format(math.degrees(issp.maxalt)), 1, txtColor)
    screen.blit(txt, (col2, line4))

    txt = txtFont.render("{:0.0f} km".format(issp.minrange) , 1, txtColor)
    screen.blit(txt, (col2, line5))

#    time_until_pass= ephem.localtime(tr)-datetime.now()
#    text='Pass in %s ' % timedelta(seconds=time_until_pass.seconds)

    td = issp.risetime - obs.date
    tds = timedelta(td).total_seconds()
    t2 = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)
    txt = txtFont.render(t2 , 1, txtColor)
    screen.blit(txt, (col2, line6))

    pygame.display.flip()


def plotSky(screen, obs, sun):

    if (sun.alt>0):
      pygame.draw.circle(screen, (255,255,0), getxy(sun.alt, sun.az), 5, 0)
    moon = ephem.Moon()
    moon.compute(obs)
    if (moon.alt>0):
      pygame.draw.circle(screen, (255,255,255), getxy(moon.alt, moon.az), 5, 0)

#    stars = ['Polaris','Sirius','Canopus','Arcturus','Vega','Capella','Rigel','Procyon','Achernar','Betelgeuse','Agena',
#      'Altair','Aldebaran','Spica','Antares','Pollux','Fomalhaut','Mimosa','Deneb','Regulus','Adara','Castor','Shaula',
#      'Bellatrix','Elnath','Alnilam','Alnair','Alnitak','Alioth','Kaus Australis','Dubhe','Wezen','Alcaid','Menkalinan',
#      'Alhena','Peacock','Mirzam','Alphard','Hamal','Algieba','Nunki','Sirrah','Mirach','Saiph','Kochab','Rasalhague',
#      'Algol','Almach','Denebola','Naos','Alphecca','Mizar','Sadr','Schedar','Etamin','Mintaka','Caph','Merak','Izar',
#      'Enif','Phecda','Scheat','Alderamin','Markab','Menkar','Arneb','Gienah Corvi','Unukalhai','Tarazed','Cebalrai',
#      'Rasalgethi','Nihal','Nihal','Algenib','Alcyone','Vindemiatrix','Sadalmelik','Zaurak','Minkar','Albereo',
#      'Alfirk','Sulafat','Megrez','Sheliak','Atlas','Thuban','Alshain','Electra','Maia','Arkab Prior','Rukbat','Alcor',
#      'Merope','Arkab Posterior','Taygeta']
      
    for star in ephem.stars.db.split("\n"):
        name = star.split(',')[0]
        if len(name)>0:
            plotstar(name, screen, obs)

# plot 5 circles to test plot
#    pygame.draw.circle(screen, (0,255,0), getxy(math.radians(90), math.radians(0)), 5, 1) # center
#    pygame.draw.circle(screen, (255,0,0), getxy(math.radians(45), math.radians(0)), 5, 1) # red N
#    pygame.draw.circle(screen, (0,255,0), getxy(math.radians(45), math.radians(90)), 5, 1) # green E
#    pygame.draw.circle(screen, (0,0,255), getxy(math.radians(45), math.radians(180)), 5, 1) # blue S
#    pygame.draw.circle(screen, (255,255,0), getxy(math.radians(45), math.radians(270)), 5, 1) # yellow W

#def plotplanet(planet, obs, screen, color, size):
    plotplanet(ephem.Mercury(), obs, screen, (128,255,255), 3)
    plotplanet(ephem.Venus(), obs, screen, (255,255,255), 4)
    plotplanet(ephem.Mars(), obs, screen, (255,0,0), 3)
    plotplanet(ephem.Jupiter(), obs, screen, (255,255,128), 4)


def setupPass(tNow, tr, ts, obs, iss, sun):
    global bg, issImg, issRect

    bg = pygame.image.load("ISSTrackerDim.png")
    bgRect = bg.get_rect()

    vis = []
    for altaz in issp.vispath:
        vis.append(getxy(altaz[0],altaz[1]))
#    print "vis:"
#    print vis

    nvis = []
    for altaz in issp.nvispath:
        nvis.append(getxy(altaz[0],altaz[1]))
#    print "nvis:"
#    print nvis

#    print "sun.alt {}".format(math.degrees(sun.alt))
#    if (math.degrees(sun.alt>0)):  "Sun is up"

    sunaltd = math.degrees(sun.alt)
#    print "sun alt {}".format(sunaltd)
    if (sunaltd > 0):
        bgcolor = (96,96,128)
    elif (sunaltd > -15): # twilight ???
        bgcolor = (64,64,128)
    else:
        bgcolor = (0,0,0)

    pygame.draw.circle(bg, bgcolor, (160,120), 120, 0)
    pygame.draw.circle(bg, (0,255,255), (160,120), 120, 1)

    if issp.daytimepass:
        viscolor = (255,255,0) # yellow
    else:
        viscolor = (255,255,255) # white
    if (len(nvis)>0):  pygame.draw.lines(bg, (0,127,255), False, nvis, 1)
    if (len(vis)>0):  pygame.draw.lines(bg, viscolor, False, vis, 1)

    txtColor = (0,255,255)
    txtFont = pygame.font.SysFont("Arial", 14, bold=True)
    txt = txtFont.render("N" , 1, txtColor)
    bg.blit(txt, (155, 0))
    txt = txtFont.render("S" , 1, txtColor)
    bg.blit(txt, (155, 222))
    txt = txtFont.render("E" , 1, txtColor)
    bg.blit(txt, (43, 112))
    txt = txtFont.render("W" , 1, txtColor)
    bg.blit(txt, (263, 112))

    issImg = pygame.image.load("ISSWm.png")
    issRect = issImg.get_rect()

    pygame.display.update()

def showPass(tNow, ts, obs, iss, sun):
    global bg, issImg, issRect, blt
    txtColor = (255,255,0)
    txtFont = pygame.font.SysFont("Arial", 20, bold=True)

    vmag=VisualMagnitude( iss, obs, sun)
    issalt = math.degrees(iss.alt)
    issaz = math.degrees(iss.az)

    if blinkstick_on:
      blt.set(vmag, issalt, 10)
      blt.start()

    t1 = ephem.localtime(obs.date).strftime("%T")
    t1 = txtFont.render(t1, 1, txtColor)

    td = ts - obs.date
    tds = timedelta(td).total_seconds()
    t2 = "%02d:%02d" % (tds//60, tds%60)
    t2 = txtFont.render(t2, 1, txtColor)

    if (vmag<99):
      tmag = "{:5.1f}".format(vmag)
    else:
      tmag = " - - -"
    tmag = txtFont.render(tmag, 1, txtColor)

    trng = txtFont.render("{:5.0f} km".format(iss.range/1000) , 1, txtColor)

    talt = txtFont.render("{:0>3.0f}".format(issalt) , 1, txtColor)
    tazi = txtFont.render("{:0>3.0f}".format(issaz) , 1, txtColor)

    screen.blit(bg, bgRect)

    plotSky(screen, obs, sun)

    screen.blit(t1, (0, 0))
    rect = t2.get_rect()
    screen.blit(t2, (320 - rect.width, 0))
    screen.blit(tmag, (0, 220))
    rect = trng.get_rect()
    screen.blit(trng, (320 - rect.width, 220))
    screen.blit(talt, (6,180))
    screen.blit(tazi, (6,200))

#    moveISS(iss.alt, iss.az)
    (issW, issH) = issImg.get_size()
    (x,y) = getxy(iss.alt,iss.az)
    issRect.left = x - issW/2
    issRect.top = y - issH/2
    screen.blit(issImg, issRect)

    pygame.display.flip()

#  ----------------------------------------------------------------

shown = False
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)
print "sigterm handler set"
logging.basicConfig(filename='/home/pi/isstracker/isstracker.log',filemode='w',level=logging.DEBUG)
logging.info("ISS-Tracker System Startup")

#    if opt.blinkstick:
if True:
    blinkstick_on = True
    blt = BlinkStick(-3, 90, 10)
    blt.start()
    sleep(1)
    blt.stop()

#    blt.set(0, 45, 10)
#    blt.start()
#    sleep(1)
#    blt.stop()

while(True):

    if (realTime):
      tNow = datetime.utcnow()
    else:
      tNow = tNow + timedelta(seconds=1)

    obs.date = tNow
    sun = ephem.Sun(obs)
#    print "sun: {},{}".format(sun.alt,sun.az)
    iss.compute(obs)

    issp = ISSPass( iss, obs, sun ) # find next ISS pass
    tr = issp.risetime # rise time
    ts = issp.settime # set time

    obs.date = tNow # reset date/time after ISSPass runs

# if ISS is not up, display the Info screen and wait for it to rise

    if ephem.localtime(tr) > ephem.localtime(obs.date) : # if ISS is not up yet
        setupInfo() # set up Info display

    # wait for ISS to rise
        while ephem.localtime(tr) > ephem.localtime(obs.date) :
            if (realTime):
              tNow = datetime.utcnow()
            else:
              tNow = tNow + timedelta(seconds=1)
            obs.date = tNow
            showInfo(tNow, issp, obs, iss, sun)
            sleep(stime)

# ISS is up now! Ddisplay the Pass screen with the track, then show it's position in real time

    sun = ephem.Sun(obs) # recompute the sun
#    print "sun: {},{}".format(sun.alt,sun.az)
    iss.compute(obs) # recompute ISS
    setupPass(tNow, tr, ts, obs, iss, sun) # set up the ISS Pass screen

    # show the pass
    while ephem.localtime(ts) > ephem.localtime(obs.date) :
        t1 = datetime.now()
        if (realTime):
          tNow = datetime.utcnow()
        else:
          tNow = tNow + timedelta(seconds=1)
        obs.date = tNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        showPass(tNow, ts, obs, iss, sun)
        dt = (datetime.now()-t1).total_seconds()
        if (dt<stime):
            sleep(stime-dt)

    blt.stop()
    # after 1 demo, switch to real time
    stime = 1
    realTime = True

    sleep(stime)

