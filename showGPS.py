# show GPS page

from datetime import datetime, timedelta
import pygame
from pygame.locals import *
import math
from plotSky import plotStars, plotPlanets

#import os
# Init framebuffer/touchscreen environment variables
#os.putenv('SDL_VIDEODRIVER', 'fbcon')
#os.putenv('SDL_FBDEV'      , '/dev/fb1')
#os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
#os.putenv('SDL_MOUSEDEV'   , '/dev/input/touchscreen')

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

    self.BG = screen.copy() # make another copy for the background
    self.BGupdate = datetime.now() - timedelta(seconds=61) # force BG update

    self.drawBG(obs, sun) # fill in the background & draw it

  def drawBG(self, obs, sun):

    self.BGupdate = datetime.now()

    self.BG.fill((0,0,0)) # clear window
    image = pygame.Surface.convert(pygame.image.load("ISSTracker7Dim.png"))
#    image  = pygame.transform.scale(image, (320,240))
    self.BG.blit(image, (0,0))

    self.bgColor = (0,0,0)

    sunaltd = math.degrees(sun.alt)
#    print "sun alt {}".format(sunaltd)
    if (sunaltd > 0):
        self.bgColor = (32,32,92) # daytime
    elif (sunaltd > -15): # twilight ???
        self.bgColor = (16,16,64)
    else:
        self.bgColor = (0,0,0)

    pygame.draw.circle(self.BG, self.bgColor, (160,120), 120, 0)
    pygame.draw.circle(self.BG, (0,255,255), (160,120), 120, 1)

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


  def plot(self, gps, obs, sun):

    if (datetime.now() - self.BGupdate).total_seconds() > 60:
      self.drawBG(obs, sun) # update background image once a minute

    self.window.blit(self.BG,(0,0)) # paint background image

    txtColor = Yellow
    txtFont = pygame.font.SysFont("Arial", 20, bold=True)

    t1 = txtFont.render(gps.datetime.strftime('%H:%M:%S'), 1, txtColor) # time
    self.window.blit(t1, (0,0)) # time

    t2 = txtFont.render(gps.datetime.strftime('%Y'), 1, txtColor) # date
    rect = t2.get_rect()
    self.window.blit(t2, (320 - rect.width, 0))
    t3 = txtFont.render(gps.datetime.strftime('%m/%d'), 1, txtColor) # date
    rect = t3.get_rect()
    self.window.blit(t3, (320 - rect.width, 24))

    txtFont = pygame.font.SysFont("Arial", 18, bold=True)

#    tgeod = txtFont.render('{:5.1f}'.format(gps.geodiff), 1, txtColor)
#    rect = tgeod.get_rect()
#    self.window.blit(tgeod, (320 - rect.width, 140))

#    tdil = txtFont.render('{:5.1f}m'.format(gps.hDilution), 1, txtColor)
#    rect = tdil.get_rect()
#    self.window.blit(tdil, (320 - rect.width, 160))

    alt = gps.altitude #+ gps.geodiff
    if alt<100:
      talt = '{:6.1f}m'.format(alt)
    else:
      talt = '{:6.0f}m'.format(alt)
    talt = txtFont.render(talt, 1, txtColor)
    rect = talt.get_rect()
    self.window.blit(talt, (320 - rect.width, 180))

    if gps.quality == 2:
      fmt = '{:7.5f}' # differential GPS - 1 meter accuracy!!!
    else:
      fmt = '{:7.5f}' # normal signal

    tlat = txtFont.render(fmt.format(math.degrees(gps.avg_latitude)), 1, txtColor)
    rect = tlat.get_rect()
    self.window.blit(tlat, (320 - rect.width, 200))

    tlon = txtFont.render(fmt.format(math.degrees(gps.avg_longitude)), 1, txtColor)
    rect = tlon.get_rect()
    self.window.blit(tlon, (320 - rect.width, 220))

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
        t1 = satFont.render(format(sat.svn), 1, White, self.bgColor)
        t1pos = t1.get_rect()
        t1pos.centerx = xy[0]
        t1pos.centery = xy[1]
        self.window.blit(t1,t1pos)

    s1 = txtFont.render('{}/{}'.format(gps.status,gps.quality), 1, txtColor)
    self.window.blit(s1,(1,24))
    s2 = txtFont.render('{:0>2}/{:0>2}'.format(nsa, ns), 1, txtColor)
    self.window.blit(s2,(1,44))

    tdil = txtFont.render('{:0.1f}m'.format(gps.hDilution), 1, txtColor)
    self.window.blit(tdil, (1, 64))

    self.screen.blit(self.window,self.pos)
    pygame.display.update() #flip()
