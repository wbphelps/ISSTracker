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
#import atexit
import errno
import os, sys, signal

import pygame
from pygame.locals import *

from time import sleep
from datetime import datetime, timedelta
import calendar
import ephem, ephem.stars
import math
from issPass import ISSPass, VisualMagnitude
import logging
#import threading

from virtualKeyboard import VirtualKeyboard
#from blinkstick import blinkstick
from issTLE import issTLE
from issBlinkStick import BlinkStick
from checkNet import checkNet

#atexit.register(exit)

# -------------------------------------------------------------

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

# set up observer location
obs = ephem.Observer()
obs.lat = math.radians(37.4388)
obs.lon = math.radians(-122.124)

tNow = datetime.utcnow()
obs.date = tNow
sun = ephem.Sun(obs)

Red = pygame.Color('red')
Orange = pygame.Color('orange')
Green = pygame.Color('green')
Blue = pygame.Color('blue')
Yellow = pygame.Color('yellow')
Cyan = pygame.Color('cyan')
Magenta = pygame.Color('magenta')
White = pygame.Color('white')

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

# ---------------------------------------------------------------

def enum(**enums):
    return type('Enum', (), enums)

def signal_handler(signal, frame):
    global blinkstick_on, BLST
    print 'SIGNAL {}'.format(signal)
    sleep(1)
    pygame.quit()
    if blinkstick_on:
      BLST.stop()
    sys.exit(0)

def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def backlight(set):
    os.system("echo 252 > /sys/class/gpio/export")
    os.system("echo 'out' > /sys/class/gpio/gpio252/direction")
    if (set):
#        gpio.digitalWrite(backlightpin,gpio.LOW)
        os.system("echo '1' > /sys/class/gpio/gpio252/value")
    else:
#        gpio.digitalWrite(backlightpin,gpio.HIGH)
        os.system("echo '0' > /sys/class/gpio/gpio252/value")

def Shutdown():
    command = "/usr/bin/sudo /sbin/shutdown -f now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print output

# ---------------------------------------------------------------------

# Init framebuffer/touchscreen environment variables
os.putenv('SDL_VIDEODRIVER', 'fbcon')
os.putenv('SDL_FBDEV'      , '/dev/fb1')
os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
os.putenv('SDL_MOUSEDEV'   , '/dev/input/touchscreen')

# Set up GPIO pins
gpio = wiringpi2.GPIO(wiringpi2.GPIO.WPI_MODE_GPIO)  
#gpio.pinMode(backlightpin,gpio.OUTPUT)  

# Init pygame and screen
pygame.init() 

pygame.mouse.set_visible(False)
size = pygame.display.list_modes(16)[0] # get screen size
#print "size: {}".format(size)

#screen = pygame.display.set_mode(size, FULLSCREEN, 16)
screen = pygame.display.set_mode(size)
(width, height) = size

backlight(True)

bg = pygame.image.load("ISSTracker7.png")
bgRect = bg.get_rect()
txtColor = Yellow
txtFont = pygame.font.SysFont("Arial", 30, bold=True)
txt = txtFont.render('ISS Tracker' , 1, txtColor)
bg.blit(txt, (15, 28))
txt = txtFont.render('by' , 1, txtColor)
bg.blit(txt, (15, 64))
txt = txtFont.render('William Phelps' , 1, txtColor)
bg.blit(txt, (15, 100))
screen.blit(bg, bgRect)
pygame.display.update()
sleep(3)

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
      pygame.draw.circle(screen, White, getxy(star.alt, star.az), 1, 1)

def plotplanet( planet, obs, screen, pFont, color, size):
    global pline
#    planet = ephem.Mercury()
    planet.compute(obs)
#    print "{} alt: {} az:{}".format(planet.name, math.degrees(planet.alt), math.degrees(planet.az))
    if (planet.alt>0):
#      pFont = pygame.font.SysFont('Arial', 15, bold=True)
      txt = pFont.render(planet.name, 1, color)
      screen.blit(txt, (1,pline))
      pline += 15
      pygame.draw.circle(screen, color, getxy(planet.alt, planet.az), size, 0)

def plotSky(screen, obs, sun):

    global pline
    pline = 24
    pFont = pygame.font.SysFont('Arial', 15, bold=True)

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

    if (sun.alt>0):
      pygame.draw.circle(screen, Yellow, getxy(sun.alt, sun.az), 5, 0)
      txt = pFont.render('Sun', 1, Yellow)
      screen.blit(txt, (1,pline))
      pline += 15
    moon = ephem.Moon()
    moon.compute(obs)
    if (moon.alt>0):
      pygame.draw.circle(screen, White, getxy(moon.alt, moon.az), 5, 0)
      txt = pFont.render('Moon', 1, White)
      screen.blit(txt, (1,pline))
      pline += 15

#def plotplanet(planet, obs, screen, color, size):
    plotplanet(ephem.Mercury(), obs, screen, pFont, (128,255,255), 3)
    plotplanet(ephem.Venus(), obs, screen, pFont, White, 3)
    plotplanet(ephem.Mars(), obs, screen, pFont, Red, 3)
    plotplanet(ephem.Jupiter(), obs, screen, pFont, (255,255,128), 3)
    plotplanet(ephem.Saturn(), obs, screen, pFont, (255,128,255), 3)

# ---------------------------------------------------------------------

def setupInfo():
# Setup fixed parts of screen
    global bg, bgRect

    bg = pygame.image.load("ISSTracker9.png")

    txtColor = Red
    txtFont = pygame.font.SysFont("Arial", 30, bold=True)
    txt = 'ISS Tracker'
#    if page == pageDemo: txt = txt + ' (Demo)'
    txt = txtFont.render(txt , 1, txtColor)
    bg.blit(txt, (15, line0))

    txtColor = Red
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

def showInfo(utcNow, issp, obs, iss, sun):
    global bg, bgRect

    txtColor = Red
    txtFont = pygame.font.SysFont("Arial", 26, bold=True)
    screen.blit(bg, bgRect) # write background image

    tn = utc_to_local(utcNow).strftime('%T')
    tn = txtFont.render(tn, 1, Orange) # show current time
    rect = tn.get_rect()
    screen.blit(tn, (320 - rect.width, line0))

    t1 = ephem.localtime(issp.risetime).strftime('%b %d %H:%M:%S')
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

#    time_until_pass= ephem.localtime(issp.risetime)-datetime.now()
#    text='Pass in %s ' % timedelta(seconds=time_until_pass.seconds)

    td = issp.risetime - obs.date
    tds = timedelta(td).total_seconds()

    if tds > 3600: tnc = Red
    elif tds > 100: tnc = Yellow
    else: tnc = Green

    t2 = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)
    txt = txtFont.render(t2 , 1, tnc)
    screen.blit(txt, (col2, line6))

    pygame.display.flip()

# ---------------------------------------------------------------------

def setupSky(issp, obs, iss, sun):
    global bg, issImg, issRect

    bg = pygame.image.load("ISSTracker7Dim.png")
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
        viscolor = Yellow # yellow
    else:
        viscolor = White # white
    if (len(nvis)>0):  pygame.draw.lines(bg, (0,127,255), False, nvis, 1)
    if (len(vis)>0):  pygame.draw.lines(bg, viscolor, False, vis, 1)

    txtColor = Cyan
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

def showSky(utcNow, issp, obs, iss, sun):
    global bg, issImg, issRect, BLST

    txtColor = Yellow
    txtFont = pygame.font.SysFont("Arial", 20, bold=True)

    vmag=VisualMagnitude( iss, obs, sun)
    issalt = math.degrees(iss.alt)
    issaz = math.degrees(iss.az)

    if blinkstick_on and issalt>0:
      BLST.set(vmag, issalt, 10)
      BLST.start()

#    t1 = ephem.localtime(obs.date).strftime("%T")
    t1 = utc_to_local(utcNow).strftime('%T')
    t1 = txtFont.render(t1, 1, txtColor)

    if (issalt>0): # if ISS is up, show the time left before it  will set
      td = issp.settime - obs.date
      tds = timedelta(td).total_seconds()
      t2 = "%02d:%02d" % (tds//60, tds%60)
    else: # show how long before it will rise
      td = issp.risetime - obs.date
      tds = timedelta(td).total_seconds()
      t2 = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)

    t2 = txtFont.render(t2, 1, txtColor)

    if (vmag<99):
      tmag = "{:5.1f}".format(vmag)
    else:
      tmag = " - - -"
    tmag = txtFont.render(tmag, 1, txtColor)
    if (issp.maxmag>99):
      txt = '---'
    else:
      txt = "{:5.1f}".format(issp.maxmag)
    tmaxmag = txtFont.render(txt, 1, txtColor)

    trng = txtFont.render("{:5.0f} km".format(iss.range/1000) , 1, txtColor)
    tminrng = txtFont.render("{:5.0f} km".format(issp.minrange) , 1, txtColor)

    talt = txtFont.render("{:0>3.0f}".format(issalt) , 1, txtColor)
    tazi = txtFont.render("{:0>3.0f}".format(issaz) , 1, txtColor)
    tmaxalt = txtFont.render("{:0.0f}".format(math.degrees(issp.maxalt)) , 1, txtColor)

    screen.blit(bg, bgRect)

    plotSky(screen, obs, sun)

    screen.blit(tmag, (0,180))
    screen.blit(talt, (6,200))
    screen.blit(tazi, (6,220))

    screen.blit(t1, (0, 0))
    rect = t2.get_rect()
    screen.blit(t2, (320 - rect.width, 0))
    rect = tminrng.get_rect()
    screen.blit(tminrng, (320 - rect.width, 20))
    rect = tmaxmag.get_rect()
    screen.blit(tmaxmag, (320 - rect.width, 40))
    rect = tmaxalt.get_rect()
    screen.blit(tmaxalt, (320 - rect.width, 60))

    rect = trng.get_rect()
    screen.blit(trng, (320 - rect.width, 220))

#    moveISS(iss.alt, iss.az)
    if (issalt>0):
      (issW, issH) = issImg.get_size()
      (x,y) = getxy(iss.alt,iss.az)
      issRect.left = x - issW/2
      issRect.top = y - issH/2
      screen.blit(issImg, issRect)

    pygame.display.flip()

#  ----------------------------------------------------------------

def pageAuto():
  global page
#  stime = 1
  print 'Auto'
  while (page == pageAuto):
    if checkEvent(): return

    utcNow = datetime.utcnow()
    obs.date = utcNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

    issp = ISSPass( iss, obs, sun, 5 ) # get data on next ISS pass
    obs.date = utcNow # reset date/time after ISSPass runs

# if ISS is not up, display the Info screen and wait for it to rise
    if ephem.localtime(issp.risetime) > ephem.localtime(obs.date) : # if ISS is not up yet
        setupInfo() # set up Info display
    # wait for ISS to rise
        utcNow = datetime.utcnow() 
        obs.date = utcNow 
        while page == pageAuto and ephem.localtime(obs.date) < ephem.localtime(issp.risetime) :
#            utcNow = datetime.utcnow()
            obs.date = utcNow
            sun = ephem.Sun(obs) # recompute the sun
            showInfo(utcNow, issp, obs, iss, sun)
#            while (datetime.utcnow()-utcNow).total_seconds() < stime:
            sec = utcNow.second
            while utcNow.second == sec: # wait for the clock to tic
                if checkEvent(): return
                sleep(0.1)
                utcNow = datetime.utcnow()

# ISS is up now - Display the Pass screen with the track, then show it's position in real time
    iss.compute(obs) # recompute ISS
    setupSky(issp, obs, iss, sun) # set up the ISS Pass screen
    # show the pass
    while page == pageAuto and ephem.localtime(issp.settime) > ephem.localtime(obs.date) :
 #       utcNow = datetime.utcnow()
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        showSky(utcNow, issp, obs, iss, sun)
        sec = utcNow.second
#        while (datetime.utcnow()-utcNow).total_seconds() < stime:
        while utcNow.second == sec: # wait for the clock to tic
            if checkEvent(): return
            sleep(0.1)
            utcNow = datetime.utcnow()

    BLST.stop() # stop blinking
  print 'end Auto'

#  ----------------------------------------------------------------

def pageDemo():
  global page
  stime = 0.1 # 10x normal speed
  print 'Demo'

  utcNow = datetime(2014, 2, 6, 3, 3, 30) # 1 minute before ISS is due
#  utcNow = datetime(2014, 2, 6, 3, 0, 0) # 2 minutes before ISS is due
#  utcNow = datetime(2014, 2, 13, 0, 34, 39) # 1 minute before ISS is due
#  utcNow = datetime(2014, 2, 13, 22, 13, 40) # 1 minute before ISS is due
#  utcNow = datetime(2014, 2, 13, 0, 35, 9) # 1 minute before ISS is due
#  utcNow = datetime(2014, 2, 14, 1, 22, 0) # 1 minute before ISS is due
#  utcNow = datetime(2014, 2, 14, 6, 18, 0) # test midpass startup
#  utcNow = datetime(2014, 2, 16, 23, 1, 0) # just before ISS is due
#  utcNow = datetime(2014, 2, 16, 23, 1, 0) # just before ISS is due

  while (page == pageDemo):
    if checkEvent(): return

    obs.date = utcNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

    issp = ISSPass( iss, obs, sun ) # get data on next ISS pass
    obs.date = utcNow # reset date/time after ISSPass runs

# if ISS is not up, display the Info screen and wait for it to rise
    if ephem.localtime(issp.risetime) > ephem.localtime(obs.date) : # if ISS is not up yet
        setupInfo() # set up Info display
    # wait for ISS to rise
        while page == pageDemo and ephem.localtime(issp.risetime) > ephem.localtime(obs.date) :
            utcNow = utcNow + timedelta(seconds=1)
            obs.date = utcNow
            sun = ephem.Sun(obs) # recompute the sun
            showInfo(utcNow, issp, obs, iss, sun)
            if checkEvent(): return
            sleep(0.1)

# ISS is up now - Display the Pass screen with the track, then show it's position in real time
    iss.compute(obs) # recompute ISS
    setupSky(issp, obs, iss, sun) # set up the ISS Pass screen
    # show the pass
    while page == pageDemo and ephem.localtime(issp.settime) > ephem.localtime(obs.date) :
        utcNow = utcNow + timedelta(seconds=1)
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        showSky(utcNow, issp, obs, iss, sun)
        if checkEvent():
            break # don't forget to stop blinking
        sleep(0.1)

    BLST.stop() # stop blinking

# after one demo, switch to Auto
    if page == pageDemo: page = pageAuto # could also be menu...
  
  print 'end Demo'

#  ----------------------------------------------------------------

def showPasses(iss, obs, sun):

    scr = pygame.Surface((320,240))
    scrRect = scr.get_rect()

    txtFont = pygame.font.SysFont('Courier', 16, bold=True)
    txtColor = White

    txt = txtFont.render('PASS START      MAG  ALT  RANGE', 1, txtColor)
    scr.blit(txt, (0,0))

    count = 0
    line = 24 # starting line #
    while count < 9: # show next 9 passes
      count += 1
# find next ISS pass and compute position of ISS
      issp = ISSPass( iss, obs, sun ) # find next ISS pass
      if issp.daytimepass:
        txtColor = (192,192,0) # dim yellow
      else:
        if issp.visible:
          txtColor = White # bright white
        else:
          txtColor = (0,192,192) # dim cyan

      t1 = ephem.localtime(issp.risetime).strftime('%b %d %H:%M:%S')
      txt = txtFont.render(t1 , 1, txtColor)
      txtPos = txt.get_rect(left=0,top=line)
      scr.blit(txt, txtPos)

      if (issp.maxmag>99):
        txt = '  ---'
      else:
        txt = "{:>5.1f}".format(issp.maxmag)
      txt = txtFont.render(txt, 1, txtColor)
      txtPos = txt.get_rect(left=txtPos.left+txtPos.width+4,top=line)
      scr.blit(txt, txtPos)

      txt = txtFont.render("{:>3.0f}".format(math.degrees(issp.maxalt)), 1, txtColor)
#      scr.blit(txt, (190, line))
      txtPos = txt.get_rect(left=txtPos.left+txtPos.width+4,top=line)
      scr.blit(txt, txtPos)

      txt = txtFont.render("{:>5.0f}Km".format(issp.minrange) , 1, txtColor)
#      scr.blit(txt, (230, line))
      txtPos = txt.get_rect(left=txtPos.left+txtPos.width+4,top=line)
      scr.blit(txt, txtPos)

      screen.blit(scr, scrRect) # write background image
      pygame.display.update()

      obs.date = ephem.Date(issp.settime + ephem.minute * 30) # start search a little after this pass
      line += 24

#    screen.blit(scr, scrRect) # write background image
#    pygame.display.update()


def pagePasses():
  global page, pageHist
  stime = 1
  print 'Passes'

  while (page == pagePasses):

    if checkEvent(): return

    tNow = datetime.utcnow()
    obs.date = tNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

    showPasses(iss, obs, sun)

    while (page == pagePasses): # wait for a menu selection
      if checkEvent():
#        page = pageHist[-1:][0] # last item in list
        pageHist = pageHist[:-1] # remove this item from history
        return
      sleep(0.1)

#  ----------------------------------------------------------------

def showTLEs():

    scr = pygame.Surface((320,240))
    scrRect = scr.get_rect()

    txtFont = pygame.font.SysFont('Courier', 15, bold=True)

    ll = 34
    txt = tle.tle[0]
    txtr = txtFont.render(txt[:ll], 1, White)
    scr.blit(txtr, (0,10))
#    txtr = txtFont.render(txt[ll:], 1, White)
#    scr.blit(txtr, (0,30))

    txt = tle.tle[1]
    txtr = txtFont.render(txt[:ll], 1, White)
    scr.blit(txtr, (0,35))
    txtr = txtFont.render(txt[ll:], 1, White)
    scr.blit(txtr, (0,55))

    txt = tle.tle[2]
    txtr = txtFont.render(txt[:ll], 1, White)
    scr.blit(txtr, (0,80))
    txtr = txtFont.render(txt[ll:], 1, White)
    scr.blit(txtr, (0,100))

    txt = tle.date.strftime('%Y-%m-%d %H:%M:%S')
    txtr = txtFont.render(txt, 1, White)
    scr.blit(txtr, (0,125))

    screen.blit(scr, scrRect) # display the new surface
    pygame.display.update()

def pageTLEs():
  global page, pageHist
  print 'TLEs'
  showTLEs()
  while page == pageTLEs:
    if checkEvent():
#        page = pageHist[-1:][0] # last item in list
        pageHist = pageHist[:-1] # remove last item
        return
    sleep(0.1)

#  ----------------------------------------------------------------

def pageDateTime():
  global page
  print 'DateTime'
  while page == pageDateTime:
    if checkEvent(): return
    mykeys = VirtualKeyboard()
    txt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    txt = mykeys.run(screen, txt)
    print 'datetime: ' + txt
    try:
        dt = datetime.strptime(txt, '%Y-%m-%d %H:%M:%S') # check format
        print 'dt: {}'.format(dt)
        os.system('sudo date -s "{}"'.format(dt))
    except:
        pass

    page = pageMenu
    return

#  ----------------------------------------------------------------

def pageLocation():
  global page
  print 'Location'
  while page == pageLocation:
    if checkEvent(): return
    mykeys = VirtualKeyboard()
    txt = '{:6.4f}, {:6.4f}'.format(math.degrees(obs.lat),math.degrees(obs.lon))
    txt = mykeys.run(screen, txt)
    try:
        print 'Location: {}'.format(txt)
        loc = txt.split(',')
        print 'loc: {:6.4f},{:6.4f}'.format(float(loc[0]),float(loc[1]))
        obs.lat = math.radians(float(loc[0]))
        obs.lon = math.radians(float(loc[1]))
        print 'obs set: {:6.4f}, {:6.4f}'.format(math.degrees(obs.lat),math.degrees(obs.lon))
        sun = ephem.Sun(obs) # recompute
        iss.compute(obs) # recompute
    except:
        pass

    page = pageMenu
    return


#  ----------------------------------------------------------------

def pageSky():
  global page
  stime = 1
  print 'Sky'
  while (page == pageSky):
    if checkEvent(): break

    utcNow = datetime.utcnow()
    obs.date = utcNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

# find next ISS pass and compute position of ISS in case it is visible
    issp = ISSPass( iss, obs, sun ) # find next ISS pass
#    utcNow = datetime.utcnow()
    obs.date = utcNow # reset date/time after ISSPass runs
    iss.compute(obs) # recompute ISS
    setupSky(issp, obs, iss, sun) # set up the ISS Pass screen
    # show the sky
    while page == pageSky :
#        utcNow = datetime.utcnow()
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        showSky(utcNow, issp, obs, iss, sun)
#        while (datetime.utcnow()-utcNow).total_seconds() < stime:
        sec = utcNow.second
        while sec == utcNow.second: # wait for clock to tic
            if checkEvent(): break
            sleep(0.1)
            utcNow = datetime.utcnow()

# todo: if ISS was up and has set, find next pass
    print 'ending'
    BLST.stop() # stop blinking

  print 'end Sky'

#  ----------------------------------------------------------------

def pageWifi():
    global page, pageHist
    print 'Wifi'
    while (page == pageWifi):
        if checkEvent():
            pageHist = pageHist[:-1] # remove subment item
            return
        sleep(0.5)

#  ----------------------------------------------------------------

def pageExit():
    # confirm with a prompt?
    sys.exit(0)

def pageShutdown():
    # confirm with a prompt?
    Shutdown()

def pageSleep():
    global page, pageHist
    print 'Sleep'
    backlight(False)
    while (page == pageSleep):
        if checkEvent():
            backlight(True)
            pageHist = pageHist[:-1] # remove submenu item
            break
        sleep(0.5)

#  ----------------------------------------------------------------

#pages = enum(Auto=0,Demo=1,Sky=2,Passes=3,GPS=4,Keybd=5,Menu=10,Location=11,Date=12,Exit=13,Shutdown=14)

class menuItem():
    def __init__(self,caption,position,font,color,page,escapeKey=False,subMenu=False):
        self.caption = caption
        self.position = position
        self.font = font
        self.color = color
        self.page = page
        self.escapekey = escapeKey
        self.subMenu = subMenu

def setMenu():
    global menuScrn, Menu
    Menu = []

    txtFont = pygame.font.SysFont('Courier', 24, bold=True)
    item = menuItem('X',(295,5),txtFont,Red,None,True) # escape key
#    item.escapekey = True # tag special key
    Menu.append(item)

    txtFont = pygame.font.SysFont("Arial", 24, bold=True)

    lx = 20 # left side
    ly = 30 # line position
    lh = 30 # line height
    Menu.append(menuItem('Auto',   (lx,ly),txtFont,Yellow,pageAuto))
    ly += lh
    Menu.append(menuItem('Demo',   (lx,ly),txtFont,Yellow,pageDemo))
    ly += lh
    Menu.append(menuItem('Sky',    (lx,ly),txtFont,Yellow,pageSky))
    ly += lh
    Menu.append(menuItem('Passes', (lx,ly),txtFont,Yellow,pagePasses))
    ly += lh
    Menu.append(menuItem('GPS',    (lx,ly),txtFont,Yellow,pageMenu))
    ly += lh
    ly += lh
    Menu.append(menuItem('Wifi',   (lx,ly),txtFont,Yellow,pageWifi,False,True))

    lx = 160 # right side
    ly = 30 # line position
    lh = 30 # line height
    Menu.append(menuItem('DateTime', (lx,ly),txtFont,Yellow,pageDateTime,False,True))
    ly += lh
    Menu.append(menuItem('Location', (lx,ly),txtFont,Yellow,pageLocation,False,True))
    ly += lh
    Menu.append(menuItem('TLEs',     (lx,ly),txtFont,Yellow,pageTLEs,False,True))
    ly += lh
    ly += lh
    Menu.append(menuItem('Sleep',    (lx,ly),txtFont,(0,127,255),pageSleep,False,True))
    ly += lh
    Menu.append(menuItem('Exit',     (lx,ly),txtFont,Orange,pageExit))
    ly += lh
    Menu.append(menuItem('Shutdown', (lx,ly),txtFont,Red,pageShutdown))

def pageMenu():
    global menuScrn, menuRect, Menu

    menuScrn = pygame.Surface((320,240)) # use the entire screen for the menu
    menuRect = menuScrn.get_rect()

    for item in Menu:
        txt = item.font.render(item.caption, 1, item.color)
        item.rect = menuScrn.blit(txt, item.position)
        if item.escapekey:
            item.rect.x, item.rect.y, item.rect.width, item.rect.height = 288, 4, 28, 28 # make the X easier to hit
            pygame.draw.rect(menuScrn, Red, item.rect, 1)

    screen.blit(menuScrn, menuRect)
    pygame.display.update()

    while page == pageMenu:
        if checkEvent(): break

#  ----------------------------------------------------------------
global menuScrn,  Menu

def checkEvent():
    global page
    global menuScrn, menuRect, Menu, pageHist

#    ev = pygame.event.poll()
    ret = False
    evl = pygame.event.get()
    for ev in evl:
        if (ev.type == pygame.NOEVENT):
            print 'NOEVENT' # ???
            pass
#    print "ev: {}".format(ev)

        if (ev.type == pygame.MOUSEBUTTONDOWN):
          print "mouse dn, x,y = {}, page={}".format(ev.pos,page)
          x,y = ev.pos
          if page == pageMenu: # what numerical value ???
            for item in Menu:
              if item.rect.collidepoint(x,y):
                pygame.draw.rect(menuScrn, Cyan, item.rect, 1)
            screen.blit(menuScrn, menuRect)
            pygame.display.update()

        if (ev.type == pygame.MOUSEBUTTONUP):
          print "mouse up, x,y = {}".format(ev.pos)
          x,y = ev.pos

#          print "page {}".format(page)
          if page != pageMenu: # other menu pages???
#              lastPage = page # save for escape
              pageHist.append(page) # add current page to history
              page = pageMenu
              ret = True
          else:
#              print "check xy {},{}".format(x,y)
            for item in Menu:
              if item.rect.collidepoint(x,y):
                if item.escapekey:
                    page = pageHist[-1:][0] # last item in list
                    pageHist = pageHist[:-1] # remove last item
                    ret = True
#                if item.subMenu:
#                    item.page() # call it now
#                    break
                elif item.page == None:
                    pass
                else:
                    page = item.page
                    ret = True
                break

    return ret


#  ----------------------------------------------------------------

logging.basicConfig(filename='/home/pi/isstracker/isstracker.log',filemode='w',level=logging.DEBUG)
logging.info("ISS-Tracker System Startup")

net = checkNet()
if net.up:
    logging.info("Network up {}".format(net.interface))
else:
    logging.info("Network down")

tle = issTLE()
tle.load()
if (datetime.now()-tle.date) > timedelta(days=1): # if TLE data more than 3 days old
    print 'fetching TLEs'
    logging.info("Fetching updated TLE data")
    tle.fetch()
    tle.save()

iss = ephem.readtle(tle.tle[0], tle.tle[1], tle.tle[2] )
iss.compute(obs)
#print obs.next_pass(iss)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)
#print "sigterm handler set"

#    if opt.blinkstick:
if True:
    blinkstick_on = True
    BLST = BlinkStick(-3, 90, 3)
    BLST.start()
    sleep(2)
    BLST.stop()

setMenu() # set up menu
page = pageAuto
pageHist = [pageAuto]

while(True):
    page()
