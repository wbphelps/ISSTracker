# show Sky page

import pygame
from pygame.locals import *
import math
from datetime import datetime, timedelta
import calendar
from plotSky import plotSky

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
    rect = self.window.get_rect()
    self.height = rect.height
    self.width = rect.width

    self.BG = screen.copy() # make another copy for the background
    self.BGupdate = datetime.now() - timedelta(seconds=61) # force BG update

#    issImg = pygame.image.load("ISSWm52x52.png")
    issImg = pygame.Surface.convert_alpha(pygame.image.load("ISSWm52x52.png"))
    self.issImg  = pygame.transform.scale(issImg, (30,30))
    self.issRect = self.issImg.get_rect()

    self.drawBG(issp, obs, sun) # fill in the background & draw it

# this draws the entire background & sky plot each time
# it doesn't need to be run so often - once a minute is plenty...

  def drawBG(self, issp, obs, sun):

    self.BGupdate = datetime.now()

    Sky = plotSky(self.BG, obs, 40, 0, 120) # draw the sky background & compass points
    Sky.plotStars(obs) # add stars
    Sky.plotPlanets(obs) # add planets

    if issp.daytimepass:
      visColor = Yellow # yellow
    else:
      visColor = White # white

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
    t2r = t2.get_rect()
    self.window.blit(t2, (self.width - t2r.width, 0))
    line = t2r.height

    tminrng = txtFont.render("{:5.0f} km".format(issp.minrange) , 1, txtColor)
    rminrng = tminrng.get_rect()
    self.window.blit(tminrng, (self.width - rminrng.width, line))
    line += rminrng.height

    if (issp.maxmag>99):
      maxmagtxt = '---'
    else:
      maxmagtxt = "{:5.1f}".format(issp.maxmag)
    tmaxmag = txtFont.render(maxmagtxt, 1, txtColor)
    rmaxmag = tmaxmag.get_rect()
    self.window.blit(tmaxmag, (self.width - rmaxmag.width, line))
    line += rmaxmag.height

    tmaxalt = txtFont.render("{:0.0f}".format(math.degrees(issp.maxalt)) , 1, txtColor)
    rmaxalt = tmaxalt.get_rect()
    self.window.blit(tmaxalt, (self.width - rmaxalt.width, line))
#    line += rmaxalt.height

    line = self.height

    trng = txtFont.render("{:5.0f} km".format(iss.range/1000) , 1, txtColor)
    rrng = trng.get_rect()
    line -= rrng.height
    self.window.blit(trng, (self.width - rrng.width, line))

    tazi = txtFont.render("{:3.0f}".format(issaz) , 1, txtColor)
    razi = tazi.get_rect()
    line -= razi.height
    self.window.blit(tazi, (self.width - razi.width, line))

    talt = txtFont.render("{:3.0f}".format(issalt) , 1, txtColor)
    ralt = talt.get_rect()
    line -= ralt.height
    self.window.blit(talt, (self.width - ralt.width, line))

#    txtFont = pygame.font.SysFont("Arial", 18, bold=True) # ???
    if (issmag<99):
      magtxt = "{:5.1f}".format(issmag)
      issColor = Green
    else:
      magtxt = " - - -"
      issColor = Blue
    tmag = txtFont.render(magtxt, 1, txtColor)
    rmag = tmag.get_rect()
    line -= rmag.height
    self.window.blit(tmag, (self.width - rmag.width, line))

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

