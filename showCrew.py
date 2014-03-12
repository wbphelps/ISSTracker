# show ISS Crew page

import pygame
from pygame.locals import *
import math
from datetime import datetime, timedelta
import urllib
import urllib2
from checkNet import checkNet

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

    self.imagename = 'isscrew.jpg' # use fixed name so we can find it if no network

    if checkNet().up:
#      image_url = 'http://www.meier-phelps.com/ISS/isscrew.annotated.png'
      image_url = 'http://www.meier-phelps.com/ISS/isscrew.annotated.largefont.png'

      urllib.urlretrieve(image_url, self.imagename)

#    self.imagename = "isscrew.annotated.png" # use an annotated image instead
    image = pygame.Surface.convert(pygame.image.load(self.imagename))
    image  = pygame.transform.scale(image, (320,240))

    self.window.blit(image, (0,0,320,240))

#    txt = txtFont.render(expname + ' Crew' , 1, txtColor)
#    self.window.blit(txt, (0, 0))

    self.screen.blit(self.window, self.windowRect)
#    pygame.display.flip()
    pygame.display.update()

  def show(self):

    return

