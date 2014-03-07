# show Sky page

import pygame
from pygame.locals import *
import math
from datetime import datetime, timedelta
import calendar

from plotSky import plotStars, plotPlanets

import os
# Init framebuffer/touchscreen environment variables
os.putenv('SDL_VIDEODRIVER', 'fbcon')
os.putenv('SDL_FBDEV'      , '/dev/fb1')
os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
os.putenv('SDL_MOUSEDEV'   , '/dev/input/touchscreen')

Red = pygame.Color('red')
Orange = pygame.Color('orange')
Green = pygame.Color('green')
Blue = pygame.Color('blue')
Yellow = pygame.Color('yellow')
Cyan = pygame.Color('cyan')
Magenta = pygame.Color('magenta')
White = pygame.Color('white')
Black = (0,0,0)
R90 = math.radians(90) # 90 degrees in radians

def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def getxy(alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r = (R90 - alt)/R90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    x = int(160 - x * 120 + 0.5) # flip E/W, scale to radius, center on plot
    y = int(120 - y * 120 + 0.5) # scale to radius, center on plot
    return (x,y)

class showSky():

  def __init__(self, screen, issp, obs, iss, sun, x=0, y=0):

    self.screen = screen
    self.pos = (x,y)

    self.window = screen.copy() # make a copy of the screen

    issImg = pygame.image.load("ISSWm52x52.png")
    self.issImg  = pygame.transform.scale(issImg, (30,30))
    self.issRect = self.issImg.get_rect()

    self.BG = screen.copy() # make another copy for the background
    self.BGupdate = datetime.now() - timedelta(seconds=61) # force BG update

    self.drawBG(issp, obs, sun) # fill in the background & draw it

# this draws the entire background & sky plot each time
# it doesn't need to be run so often - once a minute is plenty...

  def drawBG(self, issp, obs, sun):

#    if (datetime.now() - self.BGupdate).total_seconds() > 60:

      self.BGupdate = datetime.now()

      self.BG.fill((0,0,0)) # clear window
#      self.BG = pygame.image.load("ISSTracker7Dim.png") # load a background image
      image = pygame.Surface.convert(pygame.image.load("ISSTracker7Dim.png"))
#      image  = pygame.transform.scale(image, (320,240))
      self.BG.blit(image, (0,0))

      self.bgColor = (0,0,0)
      sunaltd = math.degrees(sun.alt)
      if (sunaltd > 0):
        self.bgColor = (32,32,92) # daytime
      elif (sunaltd > -15): # twilight ???
        self.bgColor = (16,16,64)
      else:
        self.bgColor = (0,0,0)

      pygame.draw.circle(self.BG, self.bgColor, (160,120), 120, 0)
      pygame.draw.circle(self.BG, (0,255,255), (160,120), 120, 1)

      if issp.daytimepass:
        visColor = Yellow # yellow
      else:
        visColor = White # white

      txtColor = Cyan
      txtFont = pygame.font.SysFont("Arial", 14, bold=True)
      txt = txtFont.render("N" , 1, txtColor)
      self.BG.blit(txt, (155, 0))
      txt = txtFont.render("S" , 1, txtColor)
      self.BG.blit(txt, (155, 222))
      txt = txtFont.render("E" , 1, txtColor)
      self.BG.blit(txt, (43, 112))
      txt = txtFont.render("W" , 1, txtColor)
      self.BG.blit(txt, (263, 112))

      plotStars(self.BG, obs, sun)
      plotPlanets(self.BG, obs, sun)

# plot circles for iss path, size shows magnitude
      for aam in issp.path: # alt, az, mag
        sz = int(1-aam[2] * 2.5 + 0.5) # vmag * 3 (sort of) (round makes a float!)
        if sz<2: sz = 2 # minimum radius
        if aam[2]<99: # visible
          pColor = visColor
        else:
          pColor = (0,127,255)
        pygame.draw.circle(self.BG, pColor, getxy(aam[0],aam[1]), sz, 1)


  def plot(self, issp, utcNow, obs, iss, sun, issmag):

    if (datetime.now() - self.BGupdate).total_seconds() > 60:
      self.drawBG(issp, obs, sun) # update background image once a minute

    self.window.blit(self.BG,(0,0)) # paint background image

    txtColor = Yellow
    txtFont = pygame.font.SysFont("Arial", 20, bold=True)
    issalt = math.degrees(iss.alt)
    issaz = math.degrees(iss.az)

#    t1 = ephem.localtime(obs.date).strftime("%H:%M:%S")
    t1txt = utc_to_local(utcNow).strftime('%H:%M:%S')
    t1 = txtFont.render(t1txt, 1, txtColor)
    self.window.blit(t1, (0, 0))

    if (issalt>0): # if ISS is up, show the time left before it will set
      td = issp.settime - obs.date
      tds = timedelta(td).total_seconds()
      t2txt = "%02d:%02d" % (tds//60, tds%60)
    else: # show how long before it will rise
      td = issp.risetime - obs.date
      tds = timedelta(td).total_seconds()
      t2txt = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)
    t2 = txtFont.render(t2txt, 1, txtColor)
    r2 = t2.get_rect()
    self.window.blit(t2, (320 - r2.width, 0))

    txtFont = pygame.font.SysFont("Arial", 18, bold=True)
    if (issmag<99):
      magtxt = "{:5.1f}".format(issmag)
      issColor = Green
    else:
      magtxt = " - - -"
      issColor = Blue
    tmag = txtFont.render(magtxt, 1, txtColor)
    rmag = tmag.get_rect()
    self.window.blit(tmag, (320 - rmag.width, 160))

    if (issp.maxmag>99):
      maxmagtxt = '---'
    else:
      maxmagtxt = "{:5.1f}".format(issp.maxmag)
    tmaxmag = txtFont.render(maxmagtxt, 1, txtColor)
    rmaxmag = tmaxmag.get_rect()
    self.window.blit(tmaxmag, (320 - rmaxmag.width, 40))

    trng = txtFont.render("{:5.0f} km".format(iss.range/1000) , 1, txtColor)
    rrng = trng.get_rect()
    self.window.blit(trng, (320 - rrng.width, 220))

    tminrng = txtFont.render("{:5.0f} km".format(issp.minrange) , 1, txtColor)
    rminrng = tminrng.get_rect()
    self.window.blit(tminrng, (320 - rminrng.width, 20))

    talt = txtFont.render("{:3.0f}".format(issalt) , 1, txtColor)
    ralt = talt.get_rect()
    self.window.blit(talt, (320 - ralt.width, 180))

    tazi = txtFont.render("{:3.0f}".format(issaz) , 1, txtColor)
    razi = tazi.get_rect()
    self.window.blit(tazi, (320 - razi.width, 200))

    tmaxalt = txtFont.render("{:0.0f}".format(math.degrees(issp.maxalt)) , 1, txtColor)
    rmaxalt = tmaxalt.get_rect()
    self.window.blit(tmaxalt, (320 - rmaxalt.width, 60))

    if (issalt>0):
      (x,y) = getxy(iss.alt,iss.az) # show where ISS is
    else:
      (x,y) = getxy(0, issp.riseazi) # show where ISS will rise
    self.issRect.centerx = x 
    self.issRect.centery = y
    self.window.blit(self.issImg, self.issRect)
    pygame.draw.circle(self.window, issColor, (x,y), self.issRect.width/2, 1)

    self.screen.blit(self.window,self.pos)
    pygame.display.update() # flip()

