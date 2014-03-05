# show GPS page

import pygame
from pygame.locals import *
import math
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
r90 = math.radians(90) # 90 degrees in radians

def getxy(alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r = (r90 - alt)/r90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    x = int(160 - x * 120) # flip E/W, scale to radius, center on plot
    y = int(120 - y * 120) # scale to radius, center on plot
    return (x,y)

class showGPS():

  def __init__(self, screen, gps, obs, sun):
#    self.screen = pygame.Surface((320,240)) # a new screen layer
    self.screen = screen
    self.bg = pygame.image.load("ISSTracker7Dim.png") # the non-changing background
    self.bgColor = (0,0,0)
    self.bgRect = self.bg.get_rect()

    sunaltd = math.degrees(sun.alt)
#    print "sun alt {}".format(sunaltd)
    if (sunaltd > 0):
        self.bgColor = (32,32,92) # daytime
    elif (sunaltd > -15): # twilight ???
        self.bgColor = (16,16,64)
    else:
        self.bgColor = (0,0,0)

    pygame.draw.circle(self.bg, self.bgColor, (160,120), 120, 0)
    pygame.draw.circle(self.bg, (0,255,255), (160,120), 120, 1)

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

    pygame.display.update()


  def plot(self, gps, obs, sun):

    txtColor = Yellow
    txtFont = pygame.font.SysFont("Arial", 20, bold=True)

    self.screen.blit(self.bg, self.bgRect)

    t1 = txtFont.render(gps.datetime.strftime('%H:%M:%S'), 1, txtColor) # time
    self.screen.blit(t1, (0,0)) # time
    t2 = txtFont.render(gps.datetime.strftime('%y-%m-%d'), 1, txtColor) # date
    rect = t2.get_rect()
    self.screen.blit(t2, (320 - rect.width, 0))

    txtFont = pygame.font.SysFont("Arial", 18, bold=True)

    alt = gps.altitude + gps.geodiff
    if alt<100:
      talt = '{:6.1f}m'.format(alt)
    else:
      talt = '{:6.0f}m'.format(alt)
    talt = txtFont.render(talt, 1, txtColor)
    rect = talt.get_rect()
    self.screen.blit(talt, (320 - rect.width, 180))

    tlat = txtFont.render('{:6.4f}'.format(math.degrees(gps.lat)), 1, txtColor)
    rect = tlat.get_rect()
    self.screen.blit(tlat, (320 - rect.width, 200))

    tlon = txtFont.render('{:6.4f}'.format(math.degrees(gps.lon)), 1, txtColor)
    rect = tlon.get_rect()
    self.screen.blit(tlon, (320 - rect.width, 220))

    plotStars(self.screen, obs, sun)
    plotPlanets(self.screen, obs, sun)

    satFont = pygame.font.SysFont("Arial", 10, bold=True)

# TODO: detect collision and move label
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
        pygame.draw.circle(self.screen, color, xy, sz, 1)
        t1 = satFont.render(format(sat.svn), 1, White, self.bgColor)
        t1pos = t1.get_rect()
        t1pos.centerx = xy[0]
        t1pos.centery = xy[1]
        self.screen.blit(t1,t1pos)
    s1 = txtFont.render('{:0>2}/{:0>2}'.format(nsa, ns), 1, txtColor)
    self.screen.blit(s1,(1,44))
    s2 = txtFont.render('{}/{}'.format(gps.status,gps.quality), 1, txtColor)
    self.screen.blit(s2,(1,24))

    pygame.display.update() #flip()

