# show Info page

import pygame
from pygame.locals import *
import math
from datetime import datetime, timedelta
import calendar
import ephem
from time import sleep
from pyColors import pyColors

Black = (0,0,0)

col1 = 5
col2 = 110

lsize = 28
line0 = 10
line1 = 16+lsize
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

class showInfo():

  def __init__(self, screen, Colors):
#    self.screen = pygame.Surface((320,240)) # a new screen layer
    self.screen = screen
    self.Colors = Colors
#    self.bgColor = (0,0,0)
    self.bg = screen.copy()
    self.bg.fill((0,0,0))
    self.bgRect = self.bg.get_rect()

    image = pygame.image.load("ISSTracker9cr.png").convert_alpha()

    pixels = pygame.PixelArray(image)
    c = 25
    while c<30: # cut off bottom end
      pixels.replace((c,c,c),(0,0,0),0.1)
      c += 1
    if self.Colors.RedOnly:
      while c<256:
        pixels.replace((c,c,c),(c,0,0),0.1)
        c += 5
    image = pixels.surface
    del pixels

    self.bg.blit(image,(180,80))

    txtColor = self.Colors.Red
    txtFont = pygame.font.SysFont("Arial", 30, bold=True)
    txt = 'Next ISS Pass'
#    if page == pageDemo: txt = txt + ' (Demo)'
    txt = txtFont.render(txt , 1, txtColor)
#    txtr = txt.get_rect()
#    self.bg.blit(txt, ((320-txtr.width)/2, line0)) # center on width
    self.bg.blit(txt, (col1, line0)) # center on width

#    txtColor = self.colors.Red
    txtFont = pygame.font.SysFont("Arial", 24, bold=True)
    txt = txtFont.render("Start:" , 1, txtColor)
    self.bg.blit(txt, (col1, line1))
    txt = txtFont.render("Visible:" , 1, txtColor)
    self.bg.blit(txt, (col1, line2))
    txt = txtFont.render("Magnitude:" , 1, txtColor)
    self.bg.blit(txt, (col1, line3))
    txt = txtFont.render("Altitude:" , 1, txtColor)
    self.bg.blit(txt, (col1, line4))
    txt = txtFont.render("Range:" , 1, txtColor)
    self.bg.blit(txt, (col1, line5))
    txt = txtFont.render("Due in:" , 1, txtColor)
    self.bg.blit(txt, (col1, line6))

    screen.blit(self.bg, self.bgRect)
    pygame.display.update()

  def show(self, utcNow, issp, obs, iss, sun):

    txtColor = self.Colors.Red
    txtFont = pygame.font.SysFont("Arial", 24, bold=True)
    self.screen.blit(self.bg, self.bgRect) # write background image

    t1 = ephem.localtime(issp.risetime).strftime('%b %d %H:%M:%S')
    txt = txtFont.render(t1 , 1, txtColor)
    self.screen.blit(txt, (col2, line1))

    if issp.visible:
      tv = 'Yes'
      tvc = self.Colors.Green
    else:
      tv = 'No'
      tvc = self.Colors.Red

    txt = txtFont.render(tv , 1, tvc)
    self.screen.blit(txt, (col2, line2))

    if (issp.maxmag>99):
      txt = '---'
    else:
      txt = "{:0.1f}".format(issp.maxmag)
    txt = txtFont.render(txt, 1, txtColor)
    self.screen.blit(txt, (col2+30, line3))
    txt = txtFont.render("{:0.0f}".format(math.degrees(issp.maxalt)), 1, txtColor)
    self.screen.blit(txt, (col2, line4))

    txt = txtFont.render("{:0.0f} km".format(issp.minrange) , 1, txtColor)
    self.screen.blit(txt, (col2, line5))

    tds = timedelta(issp.risetime - obs.date).total_seconds() # seconds until ISS rises

    bkg = Black
    if tds > 3600: tnc = self.Colors.Red # more than an hour
    elif tds > 600: tnc = self.Colors.Yellow # more than 10 minutes
    elif tds > 180: tnc = self.Colors.Green  # more than 3 minutes
    else:
#      if int(tds)%2:
      if datetime.now().second%2: # blink the time
        tnc = self.Colors.Green # odd seconds
        bkg = self.Colors.Black
      else:
        tnc = self.Colors.Black # alternate colors
        bkg = self.Colors.Green

    t2 = "%02d:%02d:%02d" % (tds//3600, tds//60%60, tds%60)
    txt = txtFont.render(t2 , 1, tnc, bkg)
    self.screen.blit(txt, (col2, line6))

    tn = utc_to_local(utcNow).strftime('%m/%d/%y %H:%M:%S')
    tn = txtFont.render(tn, 1, self.Colors.Orange) # show current time
    rect = tn.get_rect()
    self.screen.blit(tn, (320 - rect.width - 2, 240 - rect.height - 2))

    pygame.display.flip()
#    pygame.display.update()

