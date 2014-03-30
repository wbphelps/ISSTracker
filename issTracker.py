#!/usr/bin/python

# Display engine for ISS-Tracker
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
import errno
import os, sys, signal
import traceback

import pygame
from pygame.locals import *

from time import sleep
from datetime import datetime, timedelta
import ephem #, ephem.stars
import math
from issData import ISSData, VisualMagnitude
import logging
#import threading

from virtualKeyboard import VirtualKeyboard
from issTLE import issTLE
from checkNet import checkNet
from pyGPS import pyGPS, satInfo
from pyColors import pyColors

R90 = math.radians(90) # 90 degrees in radians

# -------------------------------------------------------------

# display choices
Display = 'PiTFT'
#Display = 'HDMI'
#Display = 'LCD3.3'

GPS_On = True
#GPS_On = False

BlinkStick_On = True
#BlinkStick_On = False

# -------------------------------------------------------------

if BlinkStick_On:
  from pyBlinkStick import BlinkStick

if Display == 'PiTFT':

  import wiringpi2 as wiringpi

  switch_1 = 1 # GPIO pin 18 - left to right with switches on the top
  switch_2 = 2 # GPIO pin 21/27
  switch_3 = 3 # GPIO pin 22
  switch_4 = 4 # GPIO pin 23

  backlightpin = 252

# Init framebuffer/touchscreen environment variables
  os.putenv('SDL_VIDEODRIVER', 'fbcon')
  os.putenv('SDL_FBDEV'      , '/dev/fb1')
  os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
  os.putenv('SDL_MOUSEDEV'   , '/dev/input/touchscreen')

# Set up GPIO pins
#  gpio = wiringpi.GPIO(wiringpi.GPIO.WPI_MODE_GPIO)
#  gpio.pinMode(backlightpin,gpio.OUTPUT)

#  wiringpi.wiringPiSetupGpio() # use GPIO pin numbers
  wiringpi.wiringPiSetup() # use wiringpi pin numbers

  wiringpi.pinMode(switch_1,0) # input
  wiringpi.pullUpDnControl(switch_1, 2)
  wiringpi.pinMode(switch_2,0) # input
  wiringpi.pullUpDnControl(switch_2, 2)
  wiringpi.pinMode(switch_3,0) # input
  wiringpi.pullUpDnControl(switch_3, 2)
  wiringpi.pinMode(switch_4,0) # input
  wiringpi.pullUpDnControl(switch_4, 2)

if Display == 'LCD3.3':

  from lcdButtons import lcdButtons

  os.putenv('SDL_VIDEODRIVER', 'fbcon')
  os.putenv('SDL_FBDEV'      , '/dev/fb1')
  os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
  os.putenv('SDL_MOUSEDEV'   , '/dev/input/event0')

# ---------------------------------------------------------------

def enum(**enums):
    return type('Enum', (), enums)

def StopAll():
    print 'StopAll'
    global BlinkStick_on, BLST, gps_on
    pygame.quit()
    sleep(1)
    if GPS_On:
      GPS.stop()
    sleep(1)
    if BlinkStick_on:
      BLST.stop()

def Exit():
    print 'Exit'
    StopAll()
    sys.exit(0)

def signal_handler(signal, frame):
    print 'SIGNAL {}'.format(signal)
    Exit()

def osCmd(cmd):
    out = os.popen(cmd).read()
    logging.info(cmd)
    logging.info(out)
#    logging.error(err)

def backlight(set):
  if Display == 'PiTFT':
    os.system("echo 252 > /sys/class/gpio/export")
    os.system("echo 'out' > /sys/class/gpio/gpio252/direction")
    if (set):
#        gpio.digitalWrite(backlightpin,gpio.LOW)
        os.system("echo '1' > /sys/class/gpio/gpio252/value")
    else:
#        gpio.digitalWrite(backlightpin,gpio.HIGH)
        os.system("echo '0' > /sys/class/gpio/gpio252/value")

def Shutdown():
    print 'Shutdown'
    StopAll()
    sleep(1)
#    command = "/usr/bin/sudo /sbin/shutdown -h now"
#    import subprocess
#    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
#    output = process.communicate()[0]
#    print output
    os.system("/usr/bin/sudo /sbin/shutdown -h now")
    sys.exit(0)

# ---------------------------------------------------------------------

def getxy(alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r = (R90 - alt)/R90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    x = int(160 - x * 120) # flip E/W, scale to radius, center on plot
    y = int(120 - y * 120) # scale to radius, center on plot
    return (x,y)

# ---------------------------------------------------------------------

def pageAuto():
  from showInfo import showInfo
  from showSky import showSky
  global page, Screen
#  stime = 1
  print 'Auto'
  while (page == pageAuto):
    if checkEvent(): return

    utcNow = datetime.utcnow()
    obs.date = utcNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

#    print 'Auto: before issdata date {}'.format(obs.date)
    issdata = ISSData( iss, obs, 15 ) # get data on next ISS pass, at 15 second intervals
#    print 'Auto: after issdata date {}'.format(obs.date)
#    obs.date = utcNow # reset date/time after ISSData runs
#    sun = ephem.Sun(obs)

# if ISS is not up, display the Info screen and wait for it to rise
    if ephem.localtime(issdata.risetime) > ephem.localtime(obs.date) : # if ISS is not up yet
        sInfo = showInfo(Screen, Colors) # set up Info display
    # wait for ISS to rise
        utcNow = datetime.utcnow() 
        obs.date = utcNow 
        while page == pageAuto and ephem.localtime(obs.date) < ephem.localtime(issdata.risetime) :
#            utcNow = datetime.utcnow()
            obs.date = utcNow
            sun = ephem.Sun(obs) # recompute the sun
            sInfo.show(utcNow, issdata, obs, iss, sun)
            sec = utcNow.second
            while utcNow.second == sec: # wait for the clock to tic
                if checkEvent(): return
                sleep(0.1)
                utcNow = datetime.utcnow()

# ISS is up now - Display the Pass screen with the track, then show it's position in real time
    iss.compute(obs) # recompute ISS
    sun = ephem.Sun(obs)
    sSky = showSky(Screen, Colors, issdata, obs, iss, sun) # set up the ISS Pass screen
    # show the pass
    while page == pageAuto and ephem.localtime(issdata.settime) > ephem.localtime(obs.date) :
 #       utcNow = datetime.utcnow()
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        vmag=VisualMagnitude(iss, obs, sun)
        sSky.plot(issdata, utcNow, obs, iss, sun, vmag)
        if BlinkStick_On and iss.alt>0:
          BLST.start(vmag, math.degrees(iss.alt), 10)
        sec = utcNow.second
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

  iss_tle = ('ISS (ZARYA)', 
    '1 25544U 98067A   14043.40180105  .00016203  00000-0  28859-3 0  6670',
    '2 25544  51.6503 358.1745 0004087 127.2033  23.9319 15.50263757871961')
#date = Feb 12 2014

#iss_tle = ('ISS (NASA)',
#  '1 25544U 98067A   14044.53508303  .00016717  00000-0  10270-3 0  9018',
#  '2 25544  51.6485 352.5641 0003745 129.1118 231.0366 15.50282351 32142')
#date = Feb 13 2014

#iss_tle = ('ISS (NASA)',
#   '1 25544U 98067A   14047.37128447  .00016717  00000-0  10270-3 0  9021',
#   '2 25544  51.6475 338.5079 0003760 140.1188 220.0239 15.50386824 32582')
#dat2e = Feb 16 2014
  issDemo = ephem.readtle(iss_tle[0], iss_tle[1], iss_tle[2] )

  utcNow = datetime(2014, 2, 6, 2, 59, 30) # about 2 minutes before ISS is due
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
    issDemo.compute(obs)

    issdata = ISSData( issDemo, obs, 15 ) # get data on next ISS pass, at 15 second intervals
    obs.date = utcNow # reset date/time after ISSData runs

# if ISS is not up, display the Info screen and wait for it to rise
    if ephem.localtime(issdata.risetime) > ephem.localtime(obs.date) : # if ISS is not up yet
        sInfo = showInfo(Screen, Colors) # set up Info display
    # wait for ISS to rise
        while page == pageDemo and ephem.localtime(issdata.risetime) > ephem.localtime(obs.date) :
            obs.date = utcNow
            sun = ephem.Sun(obs) # recompute the sun
            sInfo.show(utcNow, issdata, obs, issDemo, sun)
            if checkEvent(): return
            sleep(0.1)
            utcNow = utcNow + timedelta(seconds=1)

# ISS is up now - Display the Pass screen with the track, then show it's position in real time
    issDemo.compute(obs) # recompute ISS
    sSky = showSky(Screen, Colors, issdata, obs, issDemo, sun) # set up the ISS Pass screen
    # show the pass
    while page == pageDemo and ephem.localtime(issdata.settime) > ephem.localtime(obs.date) :
        obs.date = utcNow # update observer time
        issDemo.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        vmag=VisualMagnitude(issDemo, obs, sun)
        sSky.plot(issdata, utcNow, obs, issDemo, sun, vmag)
        if BlinkStick_On and issDemo.alt>0:
          BLST.start(vmag, math.degrees(issDemo.alt), 10)
        if checkEvent():
            break # don't forget to stop blinking
        sleep(0.1)
        utcNow = utcNow + timedelta(seconds=1)

    BLST.stop() # stop blinking

# after one demo, switch to Auto
    if page == pageDemo: page = pageAuto # could also be menu...
  
  print 'end Demo'

#  ----------------------------------------------------------------

def pageCrew():
  global Screen, page, pageLast
  from showCrew import showCrew
  print 'Crew'

  while (page == pageCrew):

    if checkEvent(): return

    tNow = datetime.utcnow()
#    obs.date = tNow
#    sun = ephem.Sun(obs)
#    iss.compute(obs)

    showCrew(Screen, Colors)

    while (page == pageCrew): # wait for a menu selection
      if checkEvent():
        return
      sleep(0.1)

#  ----------------------------------------------------------------

def showPasses(iss, obs, sun): 
    global Screen

    scr = pygame.Surface((320,240))
    scrRect = scr.get_rect()

    fName = 'Monospac821 BT' # lovely fixed width font
    test = pygame.font.match_font(fName, bold=True) # check to see if it's installed
#    print 'test {}'.format(test)
    if test == None:
        fName = 'DejaVuSansMono' # use this one instead

    txtFont = pygame.font.SysFont(fName, 16, bold=True)
    txtColor = Colors.White

    txt = txtFont.render('PASS START      MAG  ALT RANGE', 1, txtColor)
    scr.blit(txt, (0,0))

    count = 0
    line = 24 # starting line #
    while count < 9: # show next 9 passes
      count += 1
# find next ISS pass and compute position of ISS
      issdata = ISSData( iss, obs, 15, 0 ) # find next ISS pass (even low ones)
      txtFont = pygame.font.SysFont(fName, 16, bold=False)
      if issdata.daytimepass:
        txtColor = Colors.DarkYellow # dim yellow
      else:
        if issdata.visible:
#          txtColor = Colors.White # bright white
          txtFont = pygame.font.SysFont(fName, 16, bold=True)
          txtColor = Colors.Green # green for visible passes
        else:
          txtColor = Colors.DarkCyan # dim cyan for night time passes that are not visible

#      t1 = ephem.localtime(issdata.risetime).strftime('%b %d %H:%M:%S')
      t1 = ephem.localtime(issdata.risetime).strftime('%m/%d %H:%M:%S')
      txt = txtFont.render(t1 , 1, txtColor)
      txtPos = txt.get_rect(left=0,top=line)
      scr.blit(txt, txtPos)

      if (issdata.maxmag>99):
        txt = '  ---'
      else:
        txt = "{:>5.1f}".format(issdata.maxmag)
      txt = txtFont.render(txt, 1, txtColor)
      txtPos = txt.get_rect(left=txtPos.left+txtPos.width+4,top=line)
      scr.blit(txt, txtPos)

      txt = txtFont.render("{:>3.0f}".format(math.degrees(issdata.maxalt)), 1, txtColor)
#      scr.blit(txt, (190, line))
      txtPos = txt.get_rect(left=txtPos.left+txtPos.width+4,top=line)
      scr.blit(txt, txtPos)

      txt = txtFont.render("{:>5.0f}Km".format(issdata.minrange) , 1, txtColor)
#      scr.blit(txt, (230, line))
      txtPos = txt.get_rect(left=txtPos.left+txtPos.width+4,top=line)
      scr.blit(txt, txtPos)

      Screen.blit(scr, scrRect) # write background image
      pygame.display.update()

      obs.date = ephem.Date(issdata.settime + ephem.minute * 30) # start search a little after this pass
      line += 24

#    screen.blit(scr, scrRect) # write background image
#    pygame.display.update()


def pagePasses():
  global Screen, page, pageLast
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

def showTLEs(iss_tle):

    scr = pygame.Surface((320,240))
    scrRect = scr.get_rect()

    txtFont = pygame.font.SysFont('Courier', 15, bold=True)

    ll = 34
    txt = iss_tle.tle[0]
    txtr = txtFont.render(txt[:ll], 1, Colors.White)
    scr.blit(txtr, (0,10))
#    txtr = txtFont.render(txt[ll:], 1, Colors.White)
#    scr.blit(txtr, (0,30))

    txt = iss_tle.tle[1]
    txtr = txtFont.render(txt[:ll], 1, Colors.White)
    scr.blit(txtr, (0,35))
    txtr = txtFont.render(txt[ll:], 1, Colors.White)
    scr.blit(txtr, (0,55))

    txt = iss_tle.tle[2]
    txtr = txtFont.render(txt[:ll], 1, Colors.White)
    scr.blit(txtr, (0,80))
    txtr = txtFont.render(txt[ll:], 1, Colors.White)
    scr.blit(txtr, (0,100))

    txt = iss_tle.date.strftime('%Y-%m-%d %H:%M:%S')
    txtr = txtFont.render(txt, 1, Colors.White)
    scr.blit(txtr, (0,125))

    Screen.blit(scr, scrRect) # display the new surface
    pygame.display.update()

def pageTLEs():
  global page, ISS_TLE
  print 'TLEs'
  showTLEs(ISS_TLE)
  while page == pageTLEs:
    if checkEvent():
        return
    sleep(0.1)

#  ----------------------------------------------------------------

def pageDateTime():
  global Screen, page
  print 'DateTime'
  while page == pageDateTime:
    if checkEvent(): return
    vkey = VirtualKeyboard(Screen,Colors.White,Colors.Yellow) # create a virtual keyboard
    if GPS_On and GPS.statusOK:
      tn = GPS.datetime + timedelta(seconds=3) # set ahead a bit
    else:
      tn = datetime.now() + timedelta(seconds=3) # set ahead a bit
    txt = vkey.run(tn.strftime('%Y-%m-%d %H:%M:%S'))
    print 'datetime: {}'.format(txt)
    if len(txt)>0:
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
  global Screen, page
  print 'Location'
  while page == pageLocation:
    if checkEvent(): return
    vkey = VirtualKeyboard(Screen,Colors.White,Colors.Yellow) # create a virtual keyboard
    if GPS_On and GPS.statusOK:
        txt = '{:6.4f}, {:6.4f}'.format(math.degrees(GPS.avg_latitude),math.degrees(GPS.avg_longitude))
    else:
        txt = '{:6.4f}, {:6.4f}'.format(math.degrees(obs.lat),math.degrees(obs.lon))
    txt2 = vkey.run(txt)
    print 'Location: {}'.format(txt2)
    if len(txt2)>0:
      try:
          loc = txt2.split(',')
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

def pageSaveScreen():
  global Screen, page
  print 'SaveScreen'

  vkey = VirtualKeyboard(Screen,Colors.White,Colors.Yellow) # create a virtual keyboard
  txt = vkey.run(datetime.now().strftime('screen-%y%m%d-%H%M%S.jpg'))
  if len(txt)>0:
    pygame.image.save(screen_copy, txt)

  page = pageMenu
  return

#  ----------------------------------------------------------------

def pageSky():
  from showSky import showSky
  global Screen, page
  stime = 1
  print 'Sky'
  while (page == pageSky):
    if checkEvent(): break

    utcNow = datetime.utcnow()
    obs.date = utcNow
    sun = ephem.Sun(obs)
    iss.compute(obs)

# find next ISS pass and compute position of ISS in case it is visible
    issdata = ISSData( iss, obs, 15 ) # find next ISS pass, using 15 second intevals for path
#    utcNow = datetime.utcnow()
    obs.date = utcNow # reset date/time after ISSData runs
    iss.compute(obs) # recompute ISS
    sSky = showSky(Screen, Colors, issdata, obs, iss, sun) # set up the Sky screen
    # show the sky
    while page == pageSky :
#        utcNow = datetime.utcnow()
        obs.date = utcNow # update observer time
        iss.compute(obs) # compute new position
        sun = ephem.Sun(obs) # recompute the sun
        vmag=VisualMagnitude(iss, obs, sun)
        sSky.plot(issdata, utcNow, obs, iss, sun, vmag)
        if BlinkStick_On and iss.alt>0:
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
  global Screen, page, GPS
  print 'GPS'

  utcNow = datetime.utcnow()
  obs.date = utcNow
  sun = ephem.Sun(obs)
#  iss.compute(obs)

  sGPS = showGPS(Screen, Colors, GPS, obs, sun) # set up the GPS display screen
  # show the sky with GPS positions & signal
  while page == pageGPS:
#    utcNow = datetime.utcnow()
    obs.date = utcNow # update observer time
#    iss.compute(obs) # compute new position
    sun = ephem.Sun(obs) # recompute the sun
    sGPS.plot(GPS, obs, sun)
#    while (datetime.utcnow()-utcNow).total_seconds() < stime:
    sec = utcNow.second
    while sec == utcNow.second: # wait for clock to tic
      if checkEvent(): break
      sleep(0.1)
      utcNow = datetime.utcnow()
    gc.collect()

  del sGPS
  gc.collect()

#  ----------------------------------------------------------------

def pageWifi():
  global page
  print 'Wifi'
  page = pageMenu # temp
  return # temp
#  while (page == pageWifi):
#    if checkEvent():
#      return
#      sleep(0.5)

#  ----------------------------------------------------------------

def pageRedOnly():
  global Menu, page, Colors
  print 'RedOnly'

  if Colors.RedOnly:
    Colors.setNormal()
    BLST.Green = True
    BLST.Blue = True
  else:
    Colors.setRed()
    BLST.Green = False
    BLST.Blue = False

  Menu = setMenu()
  page = pageMenu # temp
  return # temp

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

def pageCalibrate():
    global page
    print 'Calibrate'

    if Display == 'PiTFT':
#      osCmd('sudo rmmod stmpe_ts; sudo modprobe stmpe_ts') # remove and re-install touchscreen?
      osCmd('sudo TSLIB_FBDEVICE=/dev/fb1 TSLIB_TSDEVICE=/dev/input/touchscreen ts_calibrate')
    if Display == 'LCD3.3':
      osCmd('sudo TSLIB_FBDEVICE=/dev/fb1 TSLIB_TSDEVICE=/dev/input/event0 ts_calibrate')

    page = pageMenu
    return

#  ----------------------------------------------------------------

class menuItem():
    def __init__(self,caption,position,font,color,page,escapeKey=False,subMenu=False,screenCap=False):
        self.caption = caption
        self.position = position
        self.font = font
        self.color = color
        self.page = page
        self.escapeKey = escapeKey
        self.subMenu = subMenu
        self.screenCap = screenCap

def setMenu():
#    global menuScrn, Menu
    Menu = []

    txtFont = pygame.font.SysFont('Courier', 23, bold=True)
    item = menuItem('X',(295,5),txtFont,Colors.Red,None,escapeKey=True) # escape key
#    item.escapekey = True # tag special key
    Menu.append(item)

    txtFont = pygame.font.SysFont("Arial", 23, bold=True)
    txt = txtFont.render('XXXX', 1, Colors.Yellow)
    txtR = txt.get_rect()

    lx = 5 # left side
    ly = 5 # line position
#    lh = 28 # line height
    lh = txtR.height # line height

    Menu.append(menuItem('Auto',   (lx,ly),txtFont,Colors.Yellow,pageAuto))
    ly += lh
    Menu.append(menuItem('Demo',   (lx,ly),txtFont,Colors.Yellow,pageDemo))
    ly += lh
    Menu.append(menuItem('Sky',    (lx,ly),txtFont,Colors.Yellow,pageSky))
    ly += lh
    Menu.append(menuItem('Crew', (lx,ly),txtFont,Colors.Yellow,pageCrew))
    ly += lh
    Menu.append(menuItem('Passes', (lx,ly),txtFont,Colors.Yellow,pagePasses))
    ly += lh
    Menu.append(menuItem('GPS',    (lx,ly),txtFont,Colors.Yellow,pageGPS)) # temp
    ly += lh/2
    ly += lh
    if Colors.RedOnly:
      Menu.append(menuItem('FullColor', (lx,ly),txtFont,Colors.Red,pageRedOnly))
    else:
      Menu.append(menuItem('RedOnly',   (lx,ly),txtFont,Colors.Red,pageRedOnly))
    ly += lh
    Menu.append(menuItem('Wifi',   (lx,ly),txtFont,Colors.Yellow,pageWifi))

    lx = 160 # right side
    ly = 5 # line position
#    lh = 28 # line height
    Menu.append(menuItem('DateTime', (lx,ly),txtFont,Colors.Yellow,pageDateTime))
    ly += lh
    Menu.append(menuItem('Location', (lx,ly),txtFont,Colors.Yellow,pageLocation))
    ly += lh
    Menu.append(menuItem('TLEs',     (lx,ly),txtFont,Colors.Yellow,pageTLEs))
    ly += lh
    ly += lh/2
    Menu.append(menuItem('Calibrate',(lx,ly),txtFont,Colors.LightBlue,pageCalibrate))
    ly += lh
    Menu.append(menuItem('Save',     (lx,ly),txtFont,Colors.LightBlue,pageSaveScreen,screenCap=True))
    ly += lh
    Menu.append(menuItem('Sleep',    (lx,ly),txtFont,Colors.LightBlue,pageSleep))
    ly += lh

    Menu.append(menuItem('Exit',     (lx,ly),txtFont,Colors.Red,pageExit))
    ly += lh
    ly += lh/2
    Menu.append(menuItem('Shutdown', (lx,ly),txtFont,Colors.Red,pageShutdown))

    drawMenu(Menu)
    return Menu

def drawMenu(Menu):
    global Screen,  menuScrn, menuRect

    menuScrn = pygame.Surface((320,240)) # use the entire screen for the menu
    menuRect = menuScrn.get_rect()

    for item in Menu:
        txt = item.font.render(item.caption, 1, item.color)
        item.rect = menuScrn.blit(txt, item.position)
        if item.escapeKey:
            item.rect.x, item.rect.y, item.rect.width, item.rect.height = 288, 4, 28, 28 # make the X easier to hit
            pygame.draw.rect(menuScrn, Colors.Red, item.rect, 1)

    return Menu

def pageMenu():
    global Screen, menuScrn, menuRect
    global screen_copy
    print 'Menu'

    Screen.blit(menuScrn, menuRect)
    pygame.display.update()

    while page == pageMenu:
        if checkEvent(): break
    gc.collect()

#  ----------------------------------------------------------------

global menuScrn,  Menu

def checkEvent():
    global Screen, page
    global menuScrn, menuRect, Menu, pageLast
    global screen_copy
    global tGPSupdate
    global mouseX, mouseY

    if Display == 'PiTFT':
      sw1 = not wiringpi.digitalRead(switch_1) # Read switch
      if sw1: print 'switch 1'
      sw2 = not wiringpi.digitalRead(switch_2) # Read switch
      if sw2: print 'switch 2'
      sw3 = not wiringpi.digitalRead(switch_3) # Read switch
      if sw3: print 'switch 3'
      sw4 = not wiringpi.digitalRead(switch_4) # Read switch
      if sw4: print 'switch 4'
    
    if Display == 'LCD3.3':
      buttons = Buttons.get()
      if Buttons.keybits:
        print 'buttons {} {}'.format(Buttons.keybits, buttons)
      if Buttons.keybits == 17:
        Exit()

    # if GPS status is good, update Observer location and system date/time from GPS
    if GPS_On and GPS.statusOK:
      if (datetime.now()-tGPSupdate).total_seconds() > 15: # check four times a minute
        tGPS = GPS.datetime
        tDelta = abs(tGPS-datetime.now()).total_seconds()
        if tDelta > 3:
            print 'gps-now {}'.format(tDelta)
            osCmd('sudo date -s "{}"'.format(tGPS))
            print 'time set {}'.format(tGPS)
        if (abs(obs.lat-GPS.avg_latitude)>math.radians(0.001)) or (abs(obs.lon-GPS.avg_longitude)>math.radians(0.001)):
            print 'gps location update {:6.4f} {:6.4f}'.format(math.degrees(GPS.avg_latitude), math.degrees(GPS.avg_longitude))
            obs.lat = GPS.avg_latitude # use averaged values
            obs.lon = GPS.avg_longitude
        tGPSupdate = datetime.now()

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
          mouseX,mouseY = ev.pos # remember position
          if page == pageMenu: # what numerical value ???
            for item in Menu:
              if item.rect.collidepoint(mouseX,mouseY):
                pygame.draw.rect(Screen, Colors.Cyan, item.rect, 1)
            pygame.display.update()
          else:
            screen_copy = Screen.copy() # don't capture menu screen

        if (ev.type == pygame.MOUSEBUTTONUP):
          print "mouse up, x,y = {}".format(ev.pos)
          x,y = ev.pos # use mouse down positions for menu selection

#          print "page {}".format(page)
          if page != pageMenu: # other menu pages???
              pageLast = page # for escape key
              page = pageMenu
              Screen.blit(menuScrn, menuRect)
              ret = True
          else:
#            print "check xy {},{}".format(mouseX,mouseY)
            for item in Menu:
              if item.rect.collidepoint(mouseX,mouseY):
                if item.escapeKey:
                    page = pageLast
                    ret = True
#                if item.subMenu:
#                    item.page() # call it now
#                    break
#                elif item.screenCap:
#                    pygame.image.save(screen_copy, "screenshot.jpg")
#                    page = pageLast
#                    ret = True
                elif item.page == None:
                    pass
                else:
#                    print "--> page {}".format(item.caption)
                    page = item.page
                    ret = True
                break

    return ret

#  ----------------------------------------------------------------

# set up observer location
obs = ephem.Observer()
obs.lat = math.radians(37.4388)
obs.lon = math.radians(-122.124)

tNow = datetime.utcnow()
obs.date = tNow
sun = ephem.Sun(obs)

Colors = pyColors()

# Init pygame and screen
pygame.display.init()
pygame.font.init()
pygame.mouse.set_visible(False)

size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
print "Framebuffer size: %d x %d" % (size[0], size[1])
#screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
Screen = pygame.display.set_mode(size)

bg = Screen.copy()
bg.fill((0,0,0))
bgRect = bg.get_rect()
img = pygame.image.load("ISSTracker9cr.png").convert()
bg.blit(img,(160,120))
txtColor = Colors.Yellow
txtFont = pygame.font.SysFont("Arial", 30, bold=True)
txt = txtFont.render('ISS Tracker' , 1, txtColor)
bg.blit(txt, (15, 28))
txt = txtFont.render('by' , 1, txtColor)
bg.blit(txt, (15, 64))
txt = txtFont.render('William Phelps' , 1, txtColor)
bg.blit(txt, (15, 100))
Screen.blit(bg, bgRect)
pygame.display.update()
sleep(3)

logging.basicConfig(filename='/home/pi/isstracker/isstracker.log',filemode='w',level=logging.DEBUG)
logging.info("ISS-Tracker System Startup")

#atexit.register(Exit)

net = checkNet()
if net.up:
    logging.info("Network up {}".format(net.interface))
else:
    logging.info("Network down")

ISS_TLE = issTLE()
ISS_TLE.load()
if (datetime.now()-ISS_TLE.date) > timedelta(days=1): # if TLE data more than 3 days old
    print 'fetching TLEs'
    logging.info("Fetching updated TLE data")
    ISS_TLE.fetch()
    ISS_TLE.save()

iss = ephem.readtle(ISS_TLE.tle[0], ISS_TLE.tle[1], ISS_TLE.tle[2] )
iss.compute(obs)
#print obs.next_pass(iss)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)
#print "sigterm handler set"

if GPS_On:
    GPS = pyGPS()
    GPS.start()
    tGPSupdate = datetime.now() # time of last GPS update

if Display == 'LCD3.3':
    Buttons = lcdButtons()

#    if opt.blinkstick:
if BlinkStick_On:
    BLST = BlinkStick()
    BLST.start(-3, 90, 3)
    sleep(2)
    BLST.stop()

Menu = setMenu() # set up menu
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
