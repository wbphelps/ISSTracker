# show ISS Crew page

import pygame
from pygame.locals import *
import math
from datetime import datetime, timedelta
import urllib
import urllib2
from checkNet import checkNet

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

col1 = 0
col2 = 180

lsize = 56
line0 = 30
line1 = 40+lsize
line2 = line1+lsize
line3 = line2+lsize
line4 = line3+lsize
line5 = line4+lsize
line6 = line5+lsize

def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

class showCrew():

  def __init__(self, screen, x=0, y=0):
#    self.screen = pygame.Surface((320,240)) # a new screen layer
    self.screen = screen

    self.x = x
    self.y = y

#    pygame.draw.rect(self.screen, (255,255,255), (x,y,680,520), 1) # window outline

    self.window = pygame.Surface((320,240))
    self.window.fill((0,0,0))
    self.windowRect = self.window.get_rect()
    self.windowRect.x = self.x
    self.windowRect.y = self.y

    txtColor = Yellow
    txtFont = pygame.font.SysFont("Arial", 18, bold=True)
#    self.window.blit(self.bg, self.bgRect) # write background image

    self.imgname = 'isscrew.jpg' # use fixed name so we can find it if no network

    if checkNet().up:
      uhead = "http://www.nasa.gov"
      url1 = uhead + "/mission_pages/station/main"
      data = urllib2.urlopen(url1).read()

      i1 = data.find("Read about the current crew")
      d1 = data[i1-100:i1+100]
#      print 'd1: {}'.format(d1)

      i2 = d1.find('href="')
      d2 = d1[i2:i2+100]
#      print 'd2: {}'.format(d2)

      url2 = d2.split('"')[1]
#      print 'url2: {}'.format(d2)

      data = urllib2.urlopen(url2).read()

      i1 = data.find('content="Expedition ')
      d1 = data[i1:i1+100]
#     print 'd1: {}'.format(d1)

      expname = d1.split('"')[1] # expedition name
#      print 'expname {}'.format(expname)

      i2 = data.find(expname + ' crew portrait')
      d2 = data[i2:i2+200]

      i3 = d2.find('src="')
      d3 = d2[i3:i3+100]
      imgurl = d3.split('"')[1]
#      print 'imgurl: {}'.format(imgurl)
      d4 = imgurl.split('/')
#      imgname = d4[-1]
#      print imgname

      urllib.urlretrieve(uhead + imgurl, self.imgname)

    self.imagename = "isscrew.annotated.png" # use an annotated image instead
    image = pygame.Surface.convert(pygame.image.load(self.imagename))
    image  = pygame.transform.scale(image, (320,240))
 
    self.window.blit(image, (0,0,320,240))

    txt = txtFont.render(expname + ' Crew' , 1, txtColor)
    self.window.blit(txt, (0, 0))

    self.screen.blit(self.window, self.windowRect)
#    pygame.display.flip()
    pygame.display.update()

  def show(self):

    return

