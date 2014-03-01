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

#import atexit
import gc
import wiringpi2
import errno
import os, sys, signal
import traceback

import pygame
from pygame.locals import *

from time import sleep
from datetime import datetime, timedelta
import ephem #, ephem.stars
import math
from issPass import ISSPass, VisualMagnitude
import logging
#import threading

from virtualKeyboard import VirtualKeyboard
#from blinkstick import blinkstick
from issTLE import issTLE
from issBlinkStick import BlinkStick
from checkNet import checkNet
from pyGPS import pyGPS, satInfo

# -------------------------------------------------------------

backlightpin = 252

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
Black = (0,0,0)

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

def StopAll():
    print 'StopAll'
    global blinkstick_on, BLST, gps_on
    sleep(1)
    if gps_on:
      gps.stop()
    sleep(1)
    if blinkstick_on:
      BLST.stop()
    pygame.quit()

def Exit():
    print 'Exit'
    StopAll()
    sys.exit(0)

def signal_handler(signal, frame):
    print 'SIGNAL {}'.format(signal)
    Exit()

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

    planet.compute(obs)
#    print "{} alt: {} az:{}".format(planet.name, math.degrees(planet.alt), math.degrees(planet.az))
    if (planet.alt>0):
      pygame.draw.circle(screen, color, getxy(planet.alt, planet.az), size, 0)
      txt = pFont.render(planet.name, 1, color, Black)
      pline -= 15
      screen.blit(txt, (1,pline))

def plotSky(screen, obs, sun):

    global pline
    pline = 235
    pFont = pygame.font.SysFont('Arial', 16, bold=True)

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


    plotplanet(ephem.Saturn(), obs, screen, pFont, (255,128,255), 3)
    plotplanet(ephem.Jupiter(), obs, screen, pFont, (255,255,128), 3)
    plotplanet(ephem.Mars(), obs, screen, pFont, Red, 3)
    plotplanet(ephem.Venus(), obs, screen, pFont, White, 3)
    plotplanet(ephem.Mercury(), obs, screen, pFont, (128,255,255), 3)

    moon = ephem.Moon()
    moon.compute(obs)
    if (moon.alt>0):
      pygame.draw.circle(screen, White, getxy(moon.alt, moon.az), 5, 0)
      txt = pFont.render('Moon', 1, White)
      pline -= 15
      screen.blit(txt, (1,pline))

    if (sun.alt>0):
      pygame.draw.circle(screen, Yellow, getxy(sun.alt, sun.az), 5, 0)
      txt = pFont.render('Sun', 1, Yellow)
      pline -= 15
      screen.blit(txt, (1,pline))

# ---------------------------------------------------------------------

def pageAuto():
  from showInfo import showInfo
  from showSky import showSky
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
        sInfo = showInfo(screen) # set up Info display
    # wait for ISS to rise
        utcNow = datetime.utcnow() 
        obs.date = utcNow 
        while page == pageAuto and ephem.localtime(obs.date) < ephem.localtime(issp.risetime) :
#            utcNow = datetime.utcnow()
            obs.date = utcNow
            sun = ephem.Sun(obs) # recompute the sun
            sInfo.show(utcNow, issp, obs, iss, sun)
#            while (datetime.utcnow()-utcNow).total_seconds() < stime:
            sec = utcNow.second
            while utcNow.second == sec: # wait for the clock to tic
                if checkEvent(): return
                sleep(0.1)
                utcNow = datetime.utcnow()

# ISS is up now - Display the Pass screen with the track, then show it's position in real time
    iss.compute(obs) # recompute ISS
    sSky = showSky(screen, issp, obs, iss, sun) # set up the ISS Pass screen
    # show the pass
    while page == pageAuto and ephem.localtime(issp.settime) > ephem.localtime(obs.date) :
 #       utcNow = datetime.utcnow()
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        vmag=VisualMagnitude(iss, obs, sun)
        sSky.plot(issp, utcNow, obs, iss, sun, vmag)
        if blinkstick_on and iss.alt>0:
          BLST.start(vmag, math.degrees(iss.alt), 10)
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
  from showInfo import showInfo
  from showSky import showSky
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
        sInfo = showInfo(screen) # set up Info display
    # wait for ISS to rise
        while page == pageDemo and ephem.localtime(issp.risetime) > ephem.localtime(obs.date) :
            obs.date = utcNow
            sun = ephem.Sun(obs) # recompute the sun
            sInfo.show(utcNow, issp, obs, iss, sun)
            if checkEvent(): return
            sleep(0.1)
            utcNow = utcNow + timedelta(seconds=1)

# ISS is up now - Display the Pass screen with the track, then show it's position in real time
    iss.compute(obs) # recompute ISS
    sSky = showSky(screen, issp, obs, iss, sun) # set up the ISS Pass screen
    # show the pass
    while page == pageDemo and ephem.localtime(issp.settime) > ephem.localtime(obs.date) :
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        vmag=VisualMagnitude(iss, obs, sun)
        sSky.plot(issp, utcNow, obs, iss, sun, vmag)
        if blinkstick_on and iss.alt>0:
          BLST.start(vmag, math.degrees(iss.alt), 10)
        if checkEvent():
            break # don't forget to stop blinking
        sleep(0.1)
        utcNow = utcNow + timedelta(seconds=1)

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
  global page, pageLast
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
  global page
  print 'TLEs'
  showTLEs()
  while page == pageTLEs:
    if checkEvent():
        return
    sleep(0.1)

#  ----------------------------------------------------------------

def pageDateTime():
  global page
  print 'DateTime'
  while page == pageDateTime:
    if checkEvent(): return
    mykeys = VirtualKeyboard()
    if gps_on and gps.statusOK:
      tn = gps.datetime + timedelta(seconds=5) # set ahead a bit
    else:
      tn = datetime.now() + timedelta(seconds=5) # set ahead a bit
    txt = tn.strftime('%Y-%m-%d %H:%M:%S')
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
    if gps_on and gps.statusOK:
        txt = '{:6.4f}, {:6.4f}'.format(math.degrees(gps.lat),math.degrees(gps.lon))
    else:
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
  from showSky import showSky
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
    sSky = showSky(screen, issp, obs, iss, sun) # set up the Sky screen
    # show the sky
    while page == pageSky :
#        utcNow = datetime.utcnow()
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        vmag=VisualMagnitude(iss, obs, sun)
        sSky.plot(issp, utcNow, obs, iss, sun, vmag)
        if blinkstick_on and iss.alt>0:
          BLST.start(vmag, math.degrees(iss.alt), 10)
        sec = utcNow.second
        while sec == utcNow.second: # wait for clock to tic
            if checkEvent(): break
            sleep(0.1)
            utcNow = datetime.utcnow()

# todo: if ISS was up and has set, find next pass
#    print 'ending'
    BLST.stop() # stop blinking

#  print 'end Sky'

# ---------------------------------------------------------------------

def pageGPS():
  from showGPS import showGPS
  global page, gps
  print 'GPS'

  utcNow = datetime.utcnow()
  obs.date = utcNow
  sun = ephem.Sun(obs)
  iss.compute(obs)

  sGPS = showGPS(screen, gps, obs, iss, sun) # set up the GPS display screen
  # show the sky with GPS positions & signal
  while page == pageGPS:
#    utcNow = datetime.utcnow()
    obs.date = utcNow # update observer time
    iss.compute(obs) # compute new position
    sun = ephem.Sun(obs) # recompute the sun
    sGPS.plot(gps, utcNow, obs, iss, sun)
#    while (datetime.utcnow()-utcNow).total_seconds() < stime:
    sec = utcNow.second
    while sec == utcNow.second: # wait for clock to tic
      if checkEvent(): break
      sleep(0.1)
      utcNow = datetime.utcnow()
    gc.collect()

  gc.collect()

#  ----------------------------------------------------------------

def pageWifi():
  global page
  print 'Wifi'
  page = pageMenu # temp
  return # temp
  while (page == pageWifi):
    if checkEvent():
      return
      sleep(0.5)

#  ----------------------------------------------------------------

def pageExit():
    # confirm with a prompt?
    Exit()

def pageShutdown():
    # confirm with a prompt?
    Shutdown()

def pageSleep():
    global page
    print 'Sleep'
    backlight(False)
    while (page == pageSleep):
        if checkEvent():
            backlight(True)
            break
        sleep(1)

#  ----------------------------------------------------------------

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
    Menu.append(menuItem('GPS',    (lx,ly),txtFont,Yellow,pageGPS)) # temp
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
    gc.collect()

#  ----------------------------------------------------------------
global menuScrn,  Menu

def checkEvent():
    global page
    global menuScrn, menuRect, Menu, pageLast

#    ev = pygame.event.poll()
    ret = False
    evl = pygame.event.get()
    for ev in evl:
        if (ev.type == pygame.NOEVENT):
            print 'NOEVENT' # ???
            pass
#    print "ev: {}".format(ev)

        if (ev.type == pygame.MOUSEBUTTONDOWN):
#          print "mouse dn, x,y = {}, page={}".format(ev.pos,page)
          x,y = ev.pos
          if page == pageMenu: # what numerical value ???
            for item in Menu:
              if item.rect.collidepoint(x,y):
                pygame.draw.rect(menuScrn, Cyan, item.rect, 1)
            screen.blit(menuScrn, menuRect)
            pygame.display.update()

        if (ev.type == pygame.MOUSEBUTTONUP):
#          print "mouse up, x,y = {}".format(ev.pos)
          x,y = ev.pos

#          print "page {}".format(page)
          if page != pageMenu: # other menu pages???
              pageLast = page # for escape key
              page = pageMenu
              ret = True
          else:
#              print "check xy {},{}".format(x,y)
            for item in Menu:
              if item.rect.collidepoint(x,y):
                if item.escapekey:
                    page = pageLast
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

#atexit.register(Exit)

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

gps = pyGPS()
gps.start()
gps_on = True

#    if opt.blinkstick:
if True:
    blinkstick_on = True
    BLST = BlinkStick()
    BLST.start(-3, 90, 3)
    sleep(2)
    BLST.stop()

setMenu() # set up menu
page = pageAuto

while(True):

  try:
    page()
    gc.collect()

  except SystemExit:
    print 'SystemExit'
    sys.exit(0)
  except:
    print '"Except:', sys.exc_info()[0]
    page = None
#    print traceback.format_exc()
    StopAll()
    raise
