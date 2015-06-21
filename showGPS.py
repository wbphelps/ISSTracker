# show GPS page

from datetime import datetime, timedelta
import pygame
from pygame.locals import *
import math
from plotSky import plotSky

R90 = math.radians(90) # 90 degrees in radians

class showGPS():

  def getxy(self, alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r = (R90 - alt)/R90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    if self.flip:
      x = int(self.centerX - x * self.D) # flip E/W, scale to radius, center on plot
    else:
      x = int(self.centerX + x * self.D) # flip E/W, scale to radius, center on plot
    y = int(self.centerY - y * self.D) # scale to radius, center on plot
    return (x,y)

  def __init__(self, Screen, Colors, gps, obs, sun, x=0, y=0, flip=False):

    self.Screen = Screen
    self.Colors = Colors
    self.pos = (x,y)
    self.flip = flip

    self.window = Screen.copy()
    rect = self.window.get_rect()
    self.height = rect.height
    self.width = rect.width
    self.D = self.height/2 - 2
    self.centerX = self.width/2 + 2
    self.centerY = self.height/2 + 2

    self.BG = Screen.copy() # make another copy for the background
    self.BGupdate = datetime.now() - timedelta(seconds=61) # force BG update

    self.drawBG(obs, sun) # fill in the background & draw it

  def drawBG(self, obs, sun):

    self.BGupdate = datetime.now()

    self.Sky = plotSky(self.BG, self.Colors, obs, self.centerX, self.centerY, self.D, flip=False) # draw the sky background & compass points
    self.Sky.plotStars(obs) # add stars
    self.Sky.plotPlanets(obs) # add planets


  def plot(self, gps, obs, sun):

#    fName = 'Monospac821 BT'
#    test = pygame.font.match_font(fName, bold=True) # check to see if it's installed
#    if test == None:
    fName = 'DejaVuSansMono' # use this one instead

    if (datetime.now() - self.BGupdate).total_seconds() > 60:
      self.drawBG(obs, sun) # update background image once a minute

    self.window.blit(self.BG,(0,0)) # paint background image
    line = 0

    txtColor = self.Colors.Yellow
    txtFont = pygame.font.SysFont(fName, 15, bold=True)

    t1 = txtFont.render(gps.datetime.strftime('%H:%M:%S'), 1, txtColor) # time
    t1r = t1.get_rect()
    self.window.blit(t1, (0,0)) # time
    line += t1r.height

    t2 = txtFont.render(gps.datetime.strftime('%Y/%m/%d'), 1, txtColor) # date
    t2r = t2.get_rect()
    self.window.blit(t2, (self.width - t2r.width, 0))

    e1 = txtFont.render('({})'.format(gps.error_count), 1, self.Colors.Red)
    e1r = e1.get_rect()
    self.window.blit(e1, (self.width - e1r.width, t2r.height))

    # draw a circle for each satellite
    satFont = pygame.font.SysFont(fName, 9, bold=True)
# TODO: detect collision and move label ?
    ns = 0
    nsa = 0
    for sat in gps.satellites: # plot all GPS satellites on sky chart
        if (sat.alt,sat.azi) == (0,0): pass
        xy = self.getxy(sat.alt,sat.azi)
        ns += 1
        sz = sat.snr
        if sz>0: nsa += 1
        if sz<5:    color = self.Colors.Red # no signal
        elif sz<20: color = self.Colors.Yellow
        else:       color = self.Colors.Green
        if sz<9: sz = 9 # minimum circle size
        pygame.draw.circle(self.window, color, xy, sz, 1)
#        tsat = satFont.render(format(sat.svn), 1, self.Colors.White)
        tsat = satFont.render(format(sat.svn), 1, self.Colors.White, self.Sky.bgColor)
        tpos = tsat.get_rect()
        tpos.centerx = xy[0]
        tpos.centery = xy[1]
        self.window.blit(tsat,tpos)

#    txtFont = pygame.font.SysFont(fName, 15, bold=True)

    s1 = txtFont.render('{}/{}'.format(gps.status,gps.quality), 1, txtColor)
    s1r = s1.get_rect()
    self.window.blit(s1,(1,line))
    line += s1r.height

    s2 = txtFont.render('{:0>2}/{:0>2}'.format(nsa, ns), 1, txtColor)
    s2r = s2.get_rect()
    self.window.blit(s2,(1,line))
    line += s2r.height

    tdil = txtFont.render('{:0.1f}m'.format(gps.hDilution), 1, txtColor)
    tdilr = tdil.get_rect()
    self.window.blit(tdil, (1, line))
#    line += tdilr.height

    line = self.height

    if gps.quality == 2 or gps.hDilution < 2:
      fmt = '{:7.5f}' # differential GPS - 1 meter accuracy!!!
    else:
      fmt = '{:6.4f}' # normal signal

    tlon = txtFont.render(fmt.format(math.degrees(gps.avg_longitude)), 1, txtColor)
    tlonr = tlon.get_rect()
    line -= tlonr.height
    self.window.blit(tlon, (self.width - tlonr.width, line))

    tlat = txtFont.render(fmt.format(math.degrees(gps.avg_latitude)), 1, txtColor)
    tlatr = tlat.get_rect()
    line -= tlatr.height
    self.window.blit(tlat, (self.width - tlatr.width, line))

    alt = gps.altitude #+ gps.geodiff
    if alt<100:
      talt = '{:6.1f}m'.format(alt)
    else:
      talt = '{:6.0f}m'.format(alt)
    talt = txtFont.render(talt, 1, txtColor)
    taltr = talt.get_rect()
    line -= taltr.height
    self.window.blit(talt, (self.width - taltr.width, line))

    self.Screen.blit(self.window,self.pos)
    pygame.display.update() #flip()

