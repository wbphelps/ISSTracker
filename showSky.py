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

def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def getxy(alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r90 = math.radians(90) # 90 degrees in radians
    r = (r90 - alt)/r90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    x = int(160 - x * 120) # flip E/W, scale to radius, center on plot
    y = int(120 - y * 120) # scale to radius, center on plot
    return (x,y)

class showSky():

  def __init__(self, screen, issp, obs, iss, sun):

    self.screen = screen
    self.bg = pygame.image.load("ISSTracker7Dim.png") # the non-changing background
    self.bgColor = (0,0,0)
    self.bgRect = self.bg.get_rect()

    sunaltd = math.degrees(sun.alt)
    if (sunaltd > 0):
        self.bgColor = (32,32,92) # daytime
    elif (sunaltd > -15): # twilight ???
        self.bgColor = (16,16,64)
    else:
        self.bgColor = (0,0,0)

    pygame.draw.circle(self.bg, self.bgColor, (160,120), 120, 0)
    pygame.draw.circle(self.bg, (0,255,255), (160,120), 120, 1)

    vispath = []
    nvispath = []
    firstvis = True
    firstnvis = True

#    for aam in issp.path: # alt, az, mag
#      if aam[2]<99: # visible?
#        if firstvis and not firstnvis: # if path started with non-visible portion
#          print 'linking nvis to vis'
#          vispath.append(nvispath[-1]) # connect with last point of non-visible path
#        firstvis = False
#        vispath.append(getxy(aam[0],aam[1]))
#      else:
#        if firstnvis and not firstvis: # if path started with visible portion
#          print 'linking vis to nvis'
#          nvispath.append(vispath[-1]) # connect with last point of visible path
#        firstnvis = False
#        nvispath.append(getxy(aam[0],aam[1]))

    if issp.daytimepass:
        visColor = Yellow # yellow
    else:
        visColor = White # white

#    if (len(vispath)>1):  pygame.draw.lines(self.bg, viscolor, False, vispath, 1)
#    if (len(nvispath)>1):  pygame.draw.lines(self.bg, (0,127,255), False, nvispath, 1)
    for aam in issp.path: # alt, az, mag
      sz = int(1-aam[2] * 3 + 0.5) # vmag * 3 (sort of) (round makes a float!)
      if sz<2: sz = 2
      if aam[2]<99: # visible
        pColor = visColor
      else:
        pColor = (0,127,255)
      pygame.draw.circle(self.bg, pColor, getxy(aam[0],aam[1]), sz, 1)

    txtColor = Cyan
    txtFont = pygame.font.SysFont("Arial", 14, bold=True)
    txt = txtFont.render("N" , 1, txtColor)
    self.bg.blit(txt, (155, 0))
    txt = txtFont.render("S" , 1, txtColor)
    self.bg.blit(txt, (155, 222))
    txt = txtFont.render("E" , 1, txtColor)
    self.bg.blit(txt, (43, 112))
    txt = txtFont.render("W" , 1, txtColor)
    self.bg.blit(txt, (263, 112))

    self.issImg = pygame.image.load("ISSWm.png")
    self.issRect = self.issImg.get_rect()

    pygame.display.update()

  def plot(self, issp, utcNow, obs, iss, sun, issmag):

    txtColor = Yellow
    txtFont = pygame.font.SysFont("Arial", 20, bold=True)
    issalt = math.degrees(iss.alt)
    issaz = math.degrees(iss.az)

#    t1 = ephem.localtime(obs.date).strftime("%H:%M:%S")
    t1 = utc_to_local(utcNow).strftime('%H:%M:%S')
    t1 = txtFont.render(t1, 1, txtColor)

    if (issalt>0): # if ISS is up, show the time left before it will set
      td = issp.settime - obs.date
      tds = timedelta(td).total_seconds()
      t2 = "%02d:%02d" % (tds//60, tds%60)
    else: # show how long before it will rise
      td = issp.risetime - obs.date
      tds = timedelta(td).total_seconds()
      t2 = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)
    t2 = txtFont.render(t2, 1, txtColor)

    txtFont = pygame.font.SysFont("Arial", 18, bold=True)
    if (issmag<99):
      tmag = "{:5.1f}".format(issmag)
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

    talt = txtFont.render("{:3.0f}".format(issalt) , 1, txtColor)
    tazi = txtFont.render("{:3.0f}".format(issaz) , 1, txtColor)
    tmaxalt = txtFont.render("{:0.0f}".format(math.degrees(issp.maxalt)) , 1, txtColor)
    self.screen.blit(self.bg, self.bgRect)

    plotStars(self.screen, obs, sun)
    plotPlanets(self.screen, obs, sun)

#    self.screen.blit(tmag, (0,24))
#    self.screen.blit(talt, (6,44))
#    self.screen.blit(tazi, (6,64))
    rect = tmag.get_rect()
    self.screen.blit(tmag, (320 - rect.width, 160))
    rect = talt.get_rect()
    self.screen.blit(talt, (320 - rect.width, 180))
    rect = tazi.get_rect()
    self.screen.blit(tazi, (320 - rect.width, 200))

    self.screen.blit(t1, (0, 0))
    rect = t2.get_rect()
    self.screen.blit(t2, (320 - rect.width, 0))
    rect = tminrng.get_rect()
    self.screen.blit(tminrng, (320 - rect.width, 20))
    rect = tmaxmag.get_rect()
    self.screen.blit(tmaxmag, (320 - rect.width, 40))
    rect = tmaxalt.get_rect()
    self.screen.blit(tmaxalt, (320 - rect.width, 60))

    rect = trng.get_rect()
    self.screen.blit(trng, (320 - rect.width, 220))

    if (issalt>0):
      (x,y) = getxy(iss.alt,iss.az)
      self.issRect.centerx = x 
      self.issRect.centery = y
      self.screen.blit(self.issImg, self.issRect)

    pygame.display.update() # flip()

