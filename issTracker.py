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
import ephem, ephem.stars
import math
from issPass import ISSPass, VisualMagnitude
import logging
#import threading
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
obs.lat = '37.4388'
obs.lon = '-122.124'

tNow = datetime.utcnow()
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

#def exit():
#  print "Exit"
##  sleep(1)
#  pygame.quit()

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

# pages
#pages = enum(Demo=0,Auto=1,Info=2,Sky=3,Menu=10,Location=11,GPS=12,TLE=13)
pages = enum(Demo=0,Auto=1,Sky=2,Passes=3,Menu=10,Location=11,GPS=12,TLE=13)

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
txtColor = (255,255,0)
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
      pygame.draw.circle(screen, (255,255,255), getxy(star.alt, star.az), 1, 1)

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
      pygame.draw.circle(screen, (255,255,0), getxy(sun.alt, sun.az), 5, 0)
      txt = pFont.render('Sun', 1, (255,255,0))
      screen.blit(txt, (1,pline))
      pline += 15
    moon = ephem.Moon()
    moon.compute(obs)
    if (moon.alt>0):
      pygame.draw.circle(screen, (255,255,255), getxy(moon.alt, moon.az), 5, 0)
      txt = pFont.render('Moon', 1, (255,255,255))
      screen.blit(txt, (1,pline))
      pline += 15

#def plotplanet(planet, obs, screen, color, size):
    plotplanet(ephem.Mercury(), obs, screen, pFont, (128,255,255), 3)
    plotplanet(ephem.Venus(), obs, screen, pFont, (255,255,255), 3)
    plotplanet(ephem.Mars(), obs, screen, pFont, (255,0,0), 3)
    plotplanet(ephem.Jupiter(), obs, screen, pFont, (255,255,128), 3)
    plotplanet(ephem.Saturn(), obs, screen, pFont, (255,128,255), 3)

# ---------------------------------------------------------------------

def setupInfo():
# Setup fixed parts of screen
    global bg, bgRect

    bg = pygame.image.load("ISSTracker9.png")

    txtColor = (255,0,0)
    txtFont = pygame.font.SysFont("Arial", 30, bold=True)
    txt = 'ISS Tracker'
    if page == pages.Demo: txt = txt + ' (Demo)'
    txt = txtFont.render(txt , 1, txtColor)
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
    t2 = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)
    txt = txtFont.render(t2 , 1, txtColor)
    screen.blit(txt, (col2, line6))

    pygame.display.flip()

# ---------------------------------------------------------------------

def setupSky(tNow, issp, obs, iss, sun):
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

def showSky(tNow, issp, obs, iss, sun):
    global bg, issImg, issRect, BLST
    txtColor = (255,255,0)
    txtFont = pygame.font.SysFont("Arial", 20, bold=True)

    vmag=VisualMagnitude( iss, obs, sun)
    issalt = math.degrees(iss.alt)
    issaz = math.degrees(iss.az)

    if blinkstick_on and issalt>0:
      BLST.set(vmag, issalt, 10)
      BLST.start()

    t1 = ephem.localtime(obs.date).strftime("%T")
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
  stime = 1
  print 'Auto'
  while (page == pages.Auto):
    if checkEvent(): return

    tNow = datetime.utcnow()
    obs.date = tNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

    issp = ISSPass( iss, obs, sun, 5 ) # get data on next ISS pass
    obs.date = tNow # reset date/time after ISSPass runs

# if ISS is not up, display the Info screen and wait for it to rise
    if ephem.localtime(issp.risetime) > ephem.localtime(obs.date) : # if ISS is not up yet
        setupInfo() # set up Info display
    # wait for ISS to rise
        while page == pages.Auto and ephem.localtime(issp.risetime) > ephem.localtime(obs.date) :
            t1 = datetime.now()
            tNow = datetime.utcnow()
            obs.date = tNow
            sun = ephem.Sun(obs) # recompute the sun
            showInfo(tNow, issp, obs, iss, sun)
            while (datetime.now()-t1).total_seconds() < stime:
                if checkEvent(): return
                sleep(0.1)
# ISS is up now! Display the Pass screen with the track, then show it's position in real time
    iss.compute(obs) # recompute ISS
    setupSky(tNow, issp, obs, iss, sun) # set up the ISS Pass screen
    # show the pass
    while page == pages.Auto and ephem.localtime(issp.settime) > ephem.localtime(obs.date) :
        t1 = datetime.now()
        tNow = datetime.utcnow()
        obs.date = tNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        showSky(tNow, issp, obs, iss, sun)
        while (datetime.now()-t1).total_seconds() < stime:
            if checkEvent(): return
            sleep(0.1)
    BLST.stop() # stop blinking
  print 'end Auto'

#  ----------------------------------------------------------------

def pageDemo():
  global page
  stime = 0.1 # 10x normal speed
  print 'Demo'

  tNow = datetime(2014, 2, 6, 3, 3, 0) # 1 minute before ISS is due
#  tNow = datetime(2014, 2, 6, 3, 0, 0) # 2 minutes before ISS is due
#  tNow = datetime(2014, 2, 13, 0, 34, 39) # 1 minute before ISS is due
#  tNow = datetime(2014, 2, 13, 22, 13, 40) # 1 minute before ISS is due
#  tNow = datetime(2014, 2, 13, 0, 35, 9) # 1 minute before ISS is due
#  tNow = datetime(2014, 2, 14, 1, 22, 0) # 1 minute before ISS is due
#  tNow = datetime(2014, 2, 14, 6, 18, 0) # test midpass startup
#  tNow = datetime(2014, 2, 16, 23, 1, 0) # just before ISS is due
#  tNow = datetime(2014, 2, 16, 23, 1, 0) # just before ISS is due

  while (page == pages.Demo):
    if checkEvent(): return

    obs.date = tNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

    issp = ISSPass( iss, obs, sun ) # get data on next ISS pass
    obs.date = tNow # reset date/time after ISSPass runs

# if ISS is not up, display the Info screen and wait for it to rise
    if ephem.localtime(issp.risetime) > ephem.localtime(obs.date) : # if ISS is not up yet
        setupInfo() # set up Info display
    # wait for ISS to rise
        while page == pages.Demo and ephem.localtime(issp.risetime) > ephem.localtime(obs.date) :
            t1 = datetime.now()
            tNow = tNow + timedelta(seconds=1)
            obs.date = tNow
            sun = ephem.Sun(obs) # recompute the sun
            showInfo(tNow, issp, obs, iss, sun)
            if checkEvent(): return
            while (datetime.now()-t1).total_seconds() < stime:
                if checkEvent(): return
                sleep(0.1)

# ISS is up now! Display the Pass screen with the track, then show it's position in real time
    iss.compute(obs) # recompute ISS
    setupSky(tNow, issp, obs, iss, sun) # set up the ISS Pass screen
    # show the pass
    while page == pages.Demo and ephem.localtime(issp.settime) > ephem.localtime(obs.date) :
        t1 = datetime.now()
        tNow = tNow + timedelta(seconds=1)
        obs.date = tNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        showSky(tNow, issp, obs, iss, sun)
        if checkEvent(): return
        while (datetime.now()-t1).total_seconds() < stime:
            if checkEvent(): return
            sleep(0.1)
    BLST.stop() # stop blinking

# after one demo, switch to Auto
    page = pages.Auto
  
  print 'end Demo'

#  ----------------------------------------------------------------

def showPasses(iss, obs, sun):

    scr = pygame.Surface((320,240))
    scrRect = scr.get_rect()

    txtFont = pygame.font.SysFont('Courier', 16, bold=True)
    txtColor = (255,255,255)

    txt = txtFont.render('PASS            MAG  ALT  RANGE', 1, txtColor)
    scr.blit(txt, (0,0))

    count = 0
    line = 24 # starting line #
    while count < 8: # show next 8 passes
      count += 1
# find next ISS pass and compute position of ISS
      issp = ISSPass( iss, obs, sun ) # find next ISS pass
      if issp.daytimepass:
        txtColor = (192,192,0) # dim yellow
      else:
        if issp.visible:
          txtColor = (255,255,255) # bright white
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

      line += 24

    screen.blit(scr, scrRect) # write background image
    pygame.display.update()


def pagePasses():
  global page
  stime = 1
  print 'Passes'

  while (page == pages.Passes):

    if checkEvent(): return

    tNow = datetime.utcnow()
    obs.date = tNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

    showPasses(iss, obs, sun)

    while (page == pages.Passes):
      if checkEvent(): return
      sleep(0.1)


#  ----------------------------------------------------------------

def pageSky():
  global page
  stime = 1
  print 'Sky'
  while (page == pages.Sky):
    if checkEvent(): break

    tNow = datetime.utcnow()
    obs.date = tNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

# find next ISS pass and compute position of ISS in case it is visible
    issp = ISSPass( iss, obs, sun ) # find next ISS pass
    obs.date = tNow # reset date/time after ISSPass runs
    iss.compute(obs) # recompute ISS
    setupSky(tNow, issp, obs, iss, sun) # set up the ISS Pass screen
    # show the sky
    while page == pages.Sky :
        t1 = datetime.now()
        tNow = datetime.utcnow()
        obs.date = tNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        showSky(tNow, issp, obs, iss, sun)
        while (datetime.now()-t1).total_seconds() < stime:
            if checkEvent(): break
            sleep(0.1)
# todo: if ISS was up and has set, find next pass
    print 'ending'
    BLST.stop() # stop blinking
  print 'end Sky'

#  ----------------------------------------------------------------

def doShutdown():
    # confirm with a prompt?
    Shutdown()

#  ----------------------------------------------------------------

def pageMenu():
    global page
    global menu, menuRect, bAuto, bDemo, bPasses, bSky, bExit, bShutdown

#    menuNames   = { 1:'Auto', 2:'Demo', 3:'Sky', 4:'Exit', 5:'Shutdown' }
#    menuActions = { 1:pageAuto, 2:pageDemo, 3:pageSky, 4:doExit, 5:doShutdown }

    menu = pygame.Surface((160,240))
    menuRect = menu.get_rect()
#    menuRect.left = 40
#    menuRect.top = 20

    txtColor = (255,255,0)
    txtFont = pygame.font.SysFont("Arial", 24, bold=True)

    txtAuto = txtFont.render('Auto' , 1, txtColor)
    bAuto = menu.blit(txtAuto, (20, 10))
    txtDemo = txtFont.render('Demo' , 1, txtColor)
    bDemo = menu.blit(txtDemo, (20, 50))
    txtSky  = txtFont.render('Sky' , 1, txtColor)
    bSky = menu.blit(txtSky , (20, 90))
    txtPasses  = txtFont.render('Passes' , 1, txtColor)
    bPasses = menu.blit(txtPasses , (20, 130))
    txtExit  = txtFont.render('Exit' , 1, txtColor)
    bExit = menu.blit(txtExit, (20, 170))

    txtColor = (255,0,0)
    txtShut  = txtFont.render('Shutdown' , 1, txtColor)
    bShutdown = menu.blit(txtShut, (20, 210))

    screen.blit(menu, menuRect)
    pygame.display.update()

    while page == pages.Menu:
        if checkEvent(): break

#  ----------------------------------------------------------------

def checkEvent():
    global page
    global menu, menuRect, bAuto, bDemo, bSky, bExit, bShutdown
#    ev = pygame.event.poll()
    ret = False
    evl = pygame.event.get()
    for ev in evl:
        if (ev.type == pygame.NOEVENT):
            print 'NOEVENT' # ???
            pass
#    print "ev: {}".format(ev)

        if (ev.type == pygame.MOUSEBUTTONDOWN):
#          print "mouse dn, x,y = {}".format(ev.pos)
          x,y = ev.pos
          if page >= pages.Menu:
            if bAuto.collidepoint(x,y):
              pygame.draw.rect(menu, (0,255,255), bAuto, 1)
            if bDemo.collidepoint(x,y):
              pygame.draw.rect(menu, (0,255,255), bDemo, 1)
            if bSky.collidepoint(x,y):
              pygame.draw.rect(menu, (0,255,255), bSky, 1)
            if bPasses.collidepoint(x,y):
              pygame.draw.rect(menu, (0,255,255), bPasses, 1)
            if bExit.collidepoint(x,y):
              pygame.draw.rect(menu, (0,255,255), bExit, 1)
            if bShutdown.collidepoint(x,y):
              pygame.draw.rect(menu, (0,255,255), bShutdown, 1)
            screen.blit(menu, menuRect)
            pygame.display.update()


        if (ev.type == pygame.MOUSEBUTTONUP):
#          print "mouse up, x,y = {}".format(ev.pos)
          x,y = ev.pos

#          print "page {}".format(page)
          if page < pages.Menu:
              page = pages.Menu
              ret = True
          else:
#              print "check xy {},{}".format(x,y)
              if bAuto.collidepoint(x,y):
                page = pages.Auto
                ret = True
              if bDemo.collidepoint(x,y):
                page = pages.Demo
                ret = True
              if bSky.collidepoint(x,y):
                page = pages.Sky
                ret = True
              if bPasses.collidepoint(x,y):
                page = pages.Passes
                ret = True
              if bExit.collidepoint(x,y):
                 pygame.quit()
                 sys.exit(0)
              if bShutdown.collidepoint(x,y):
#                page = pages.Sky
#                ret = True # just redraw current screen
                 Shutdown()

#          print "page {}".format(page)

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

page = pages.Auto

while(True):

    if page == pages.Demo:
        pageDemo()
    elif page == pages.Sky:
        pageSky()
    elif page == pages.Passes:
        pagePasses()
    elif page == pages.Menu:
        pageMenu()
    else:
        pageAuto()


