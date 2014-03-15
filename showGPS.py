# show GPS page

from datetime import datetime, timedelta
import pygame
from pygame.locals import *
import math
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

def getxy(alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r = (R90 - alt)/R90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    x = int(160 - x * 120) # flip E/W, scale to radius, center on plot
    y = int(120 - y * 120) # scale to radius, center on plot
    return (x,y)

class showGPS():

  def __init__(self, screen, gps, obs, sun, x=0, y=0):

    self.screen = screen
    self.pos = (x,y)

    self.window = screen.copy()
    rect = self.window.get_rect()
    self.height = rect.height
    self.width = rect.width

    self.BG = screen.copy() # make another copy for the background
    self.BGupdate = datetime.now() - timedelta(seconds=61) # force BG update

    self.drawBG(obs, sun) # fill in the background & draw it

  def drawBG(self, obs, sun):

    self.BGupdate = datetime.now()

    self.Sky = plotSky(self.BG, obs, 40, 0, 120) # draw the sky background & compass points
    self.Sky.plotStars(obs) # add stars
    self.Sky.plotPlanets(obs) # add planets


  def plot(self, gps, obs, sun):

    if (datetime.now() - self.BGupdate).total_seconds() > 60:
      self.drawBG(obs, sun) # update background image once a minute

    self.window.blit(self.BG,(0,0)) # paint background image
    line = 0

    txtColor = Yellow
    txtFont = pygame.font.SysFont("Arial", 18, bold=True)

    t1 = txtFont.render(gps.datetime.strftime('%H:%M:%S'), 1, txtColor) # time
    t1r = t1.get_rect()
    self.window.blit(t1, (0,0)) # time
    line += t1r.height

    t2 = txtFont.render(gps.datetime.strftime('%Y/%m/%d'), 1, txtColor) # date
    t2r = t2.get_rect()
    self.window.blit(t2, (self.width - t2r.width, 0))

    e1 = txtFont.render('({})'.format(gps.error_count), 1, Red)
    e1r = e1.get_rect()
    self.window.blit(e1, (self.width - e1r.width, t2r.height))

    # draw a circle for each satellite
    satFont = pygame.font.SysFont("Arial", 10, bold=True)
# TODO: detect collision and move label ?
    ns = 0
    nsa = 0
    for sat in gps.satellites: # plot all GPS satellites on sky chart
        if (sat.alt,sat.azi) == (0,0): pass
        xy = getxy(sat.alt,sat.azi)
        ns += 1
        sz = sat.snr
        if sz>0: nsa += 1
        if sz<5:    color = Red # no signal
        elif sz<20: color = Yellow
        else:       color = Green
        if sz<9: sz = 9 # minimum circle size
        pygame.draw.circle(self.window, color, xy, sz, 1)
#        tsat = satFont.render(format(sat.svn), 1, White)
        tsat = satFont.render(format(sat.svn), 1, White, self.Sky.bgColor)
        tpos = tsat.get_rect()
        tpos.centerx = xy[0]
        tpos.centery = xy[1]
        self.window.blit(tsat,tpos)

    txtFont = pygame.font.SysFont("Arial", 17, bold=True)

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

    self.screen.blit(self.window,self.pos)
    pygame.display.flip() #flip()

