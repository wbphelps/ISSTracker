# show Sky page

import pygame
from pygame.locals import *
import math
from datetime import datetime, timedelta
import calendar
from plotSky import plotSky
import ephem

R90 = math.radians(90) # 90 degrees in radians

def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

class showSky():


  def getxy(self, alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r = (R90 - alt)/R90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    if self.flip:
      x = int(self.centerX - x * self.D) # flip E/W, scale to radius, center on plot
      y = int(self.centerY - y * self.D) # scale to radius, center on plot
    else:
      x = int(self.centerX + x * self.D) # flip E/W, scale to radius, center on plot
      y = int(self.centerY + y * self.D) # scale to radius, center on plot
    return (x,y)



  def __init__(self, screen, Colors, issp, obs, iss, sun, x=0, y=0, flip=False):

    self.screen = screen
    self.Colors = Colors
    self.pos = (x,y)

    self.window = screen.copy() # make a copy of the screen
    rect = self.window.get_rect()
    self.height = rect.height
    self.width = rect.width
    self.D = self.height/2 - 2 # plot diameter
    self.centerX = self.width/2 + 2
    self.centerY = self.height/2 + 2
    self.flip = flip

    self.BG = screen.copy() # make another copy for the background
#    self.BGupdate = datetime.now() - timedelta(seconds=61) # force BG update

#    issImg = pygame.image.load("ISSWm52x52.png")
#    issImg = pygame.Surface.convert_alpha(pygame.image.load("ISSWm52x52.png"))
    if self.Colors.RedOnly:
      issImg = pygame.image.load("ISSWm52x52-red.png").convert_alpha()
    else:
      issImg = pygame.image.load("ISSWm52x52.png").convert_alpha()
    self.issImg = pygame.transform.scale(issImg, (30,30))
    self.issRect = self.issImg.get_rect()

    self.drawBG(issp, obs, sun) # fill in the background & draw it

# this draws the entire background & sky plot each time
# it doesn't need to be run so often - once a minute is plenty...

  def drawBG(self, issp, obs, sun):

#    self.BGupdate = datetime.now()

    Sky = plotSky(self.BG, self.Colors, obs, self.centerX, self.centerY, self.D) # draw the sky background & compass points
    Sky.plotStars(obs) # add stars
    Sky.plotPlanets(obs) # add planets

    if issp.daytimepass:
      visColor = self.Colors.Yellow # yellow
    else:
      visColor = self.Colors.White # white

# plot circles for iss path, size shows magnitude
    for aam in issp.path: # alt, az, mag
      sz = int(1-aam[2] * 2.5 + 0.5) # vmag * 3 (sort of) (round makes a float!)
      if sz<2: sz = 2 # minimum radius
      if aam[2]<99: # visible
        pColor = visColor
      else:
        pColor = self.Colors.LightBlue
      pygame.draw.circle(self.BG, pColor, self.getxy(aam[0],aam[1]), sz, 1)


  def plot(self, issp, utcNow, obs, iss, sun, issmag):

    fName = 'Monospac821 BT'
    test = pygame.font.match_font(fName, bold=True) # check to see if it's installed
    if test == None:
      fName = 'DejaVuSansMono' # use this one instead

#    if (datetime.now() - self.BGupdate).total_seconds() > 60:
    second = int(obs.date.tuple()[5])
    if second%60 == 0: # update screen every 60 seconds
      self.drawBG(issp, obs, sun) # update background image once a minute

    self.window.blit(self.BG,(0,0)) # paint background image

    txtColor = self.Colors.Yellow
    txtFont = pygame.font.SysFont(fName, 15, bold=True)
    issalt = math.degrees(iss.alt)
    issaz = math.degrees(iss.az)

    d1txt = utc_to_local(utcNow).strftime('%m/%d/%y')
    d1 = txtFont.render(d1txt, 1, txtColor)
    d1r = d1.get_rect()
    self.window.blit(d1, (0, 0))

#    t1 = ephem.localtime(obs.date).strftime("%H:%M:%S")
    t1txt = utc_to_local(utcNow).strftime('%H:%M:%S')
    t1 = txtFont.render(t1txt, 1, txtColor)
    self.window.blit(t1, (0, d1r.height))

    if (issalt>0): # if ISS is up, show the time left before it will set
      t2 = issp.settime
      t3 = t2 - obs.date
      tds = timedelta(t3).total_seconds()
      t3txt = "%02d:%02d" % (tds//60, tds%60)
    else: # show how long before it will rise
      t2 = issp.risetime
      t3 = t2 - obs.date
      tds = timedelta(t3).total_seconds()
      t3txt = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)

    line = 0

    d2txt = ephem.localtime(t2).strftime('%m/%d/%y') # date when ISS is due to rise (or set)
    d2r = txtFont.render(d2txt, 1, txtColor)
    d2rect = d2r.get_rect()
    self.window.blit(d2r, (self.width - d2rect.width, line))
    line += d2rect.height

    t2txt = ephem.localtime(t2).strftime('%H:%M:%S') # time when ISS is due to rise (or set)
    t2r = txtFont.render(t2txt, 1, txtColor)
    t2rect = t2r.get_rect()
    self.window.blit(t2r, (self.width - t2rect.width, line))
    line += t2rect.height

    txtFont = pygame.font.SysFont(fName, 15, bold=True)

    tminrng = txtFont.render("{:5.0f}km".format(issp.minrange) , 1, txtColor)
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

    t3r = txtFont.render(t3txt, 1, txtColor) # time before ISS rises (or sets)
    t3rect = t3r.get_rect()
    line -= t3rect.height
    self.window.blit(t3r, (self.width - t3rect.width, line))
#    line += t3rect.height

    trng = txtFont.render("{:5.0f}km".format(iss.range/1000) , 1, txtColor) # distance to ISS now
    rrng = trng.get_rect()
    line -= rrng.height
    self.window.blit(trng, (self.width - rrng.width, line))

    tazi = txtFont.render("{:3.0f}".format(issaz) , 1, txtColor) # current azimuth
    razi = tazi.get_rect()
    line -= razi.height
    self.window.blit(tazi, (self.width - razi.width, line))

    talt = txtFont.render("{:3.0f}".format(issalt) , 1, txtColor) # current altitude
    ralt = talt.get_rect()
    line -= ralt.height
    self.window.blit(talt, (self.width - ralt.width, line))

#    txtFont = pygame.font.SysFont(fName, 18, bold=True) # ???
    if (issmag<99):
      magtxt = "{:5.1f}".format(issmag)
      issColor = self.Colors.Green
    else:
      magtxt = "---"
      issColor = self.Colors.Blue
    tmag = txtFont.render(magtxt, 1, txtColor)
    rmag = tmag.get_rect()
    line -= rmag.height
    self.window.blit(tmag, (self.width - rmag.width, line))

    if (issalt>0):
      (x,y) = self.getxy(iss.alt,iss.az) # show where ISS is
    else:
      (x,y) = self.getxy(0, issp.riseazi) # show where ISS will rise
    self.issRect.centerx = x 
    self.issRect.centery = y
    self.window.blit(self.issImg, self.issRect)
    pygame.draw.circle(self.window, issColor, (x,y), self.issRect.width/2, 1)

    self.screen.blit(self.window,self.pos)
    pygame.display.update() # flip()

