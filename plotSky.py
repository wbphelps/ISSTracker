# plot stars on screen
# plot planets on screen - sun, moon, mercury, venus, mars, jupiter, saturn

import pygame
from pygame.locals import *
import math
import ephem #, ephem.stars

R90 = math.radians(90) # 90 degrees in radians

stars = []

#stardata = ephem.stars.db.split("\n")
#for startxt in stardata:
#  name = startxt.split(',')[0]
#  if len(name)>0:
#    stars.append(ephem.star(name))
#del stardata

# there are 94 names in this list and 94 in ephem.stars.db...
starnames = ['Polaris','Sirius','Canopus','Arcturus','Vega','Capella','Rigel','Procyon','Achernar','Betelgeuse','Agena',
  'Altair','Aldebaran','Spica','Antares','Pollux','Fomalhaut','Mimosa','Deneb','Regulus','Adara','Castor','Shaula',
  'Bellatrix','Elnath','Alnilam','Alnair','Alnitak','Alioth','Kaus Australis','Dubhe','Wezen','Alcaid','Menkalinan',
  'Alhena','Peacock','Mirzam','Alphard','Hamal','Algieba','Nunki','Sirrah','Mirach','Saiph','Kochab','Rasalhague',
  'Algol','Almach','Denebola','Naos','Alphecca','Mizar','Sadr','Schedar','Etamin','Mintaka','Caph','Merak','Izar',
  'Enif','Phecda','Scheat','Alderamin','Markab','Menkar','Arneb','Gienah Corvi','Unukalhai','Tarazed','Cebalrai',
  'Rasalgethi','Nihal','Algenib','Alcyone','Vindemiatrix','Sadalmelik','Zaurak','Minkar','Albereo','Alfirk',
  'Sulafat','Megrez','Sheliak','Atlas','Thuban','Alshain','Electra','Maia','Arkab Prior','Rukbat','Alcor',
  'Merope','Arkab Posterior','Taygeta']
for name in starnames:
  stars.append(ephem.star(name))
del starnames

#print 'Stars: {}'.format(len(stars))

class plotSky():

  def getxy(self, alt, azi): # alt, az in radians
# thanks to John at Wobbleworks for the algorithm
    r = (R90 - alt)/R90
    x = r * math.sin(azi)
    y = r * math.cos(azi)
    x = int(self.centerX - x * self.D) # flip E/W, scale to radius, center on plot
    y = int(self.centerY - y * self.D) # scale to radius, center on plot
    return (x,y)

  def getxyD(self, alt, azi): # alt, az in degrees
    return self.getxy(math.radians(alt), math.radians(azi))

  def __init__(self, screen, Colors, obs, centerX=162, centerY=122, D=118, fontSize=15):

    self.screen = screen
    self.Colors = Colors

    self.obs = obs
    self.centerX = centerX
    self.centerY = centerY
    self.D = D

    self.bg = screen.copy() # make a copy of the screen
    self.bgRect = self.bg.get_rect()
    self.bg.fill((0,0,0))
    self.bgColor = (0,0,0)

    self.pLine = self.bgRect.height-2
    self.pFont = fontSize

    sun = ephem.Sun()
    sun.compute(obs)
    sunaltd = math.degrees(sun.alt)
#    print 'showSky: sunalt {}'.format(sunaltd)
    if (sunaltd > 0):
      if self.Colors.RedOnly:
        self.bgColor = (32,0,0) # daytime
      else:
        self.bgColor = (32,32,92) # daytime
    elif (sunaltd > -15): # twilight ???
      if self.Colors.RedOnly:
        self.bgColor = (16,0,0)
      else:
        self.bgColor = (16,16,64)
    else:
        self.bgColor = (0,0,0)

    pygame.draw.circle(self.bg, self.bgColor, (self.centerX,self.centerY), self.D, 0)
    pygame.draw.circle(self.bg, self.Colors.Cyan, (self.centerX,self.centerY), self.D, 1)

    txtColor = self.Colors.Cyan
    txtFont = pygame.font.SysFont("Arial", self.pFont, bold=True)

    txt = txtFont.render("N" , 1, txtColor)
    rect = txt.get_rect()
    rect.centerx, rect.centery = self.getxyD(7,0)
    self.bg.blit(txt, rect)
    txt = txtFont.render("S" , 1, txtColor)
    rect = txt.get_rect()
    rect.centerx, rect.centery = self.getxyD(6,180)
    self.bg.blit(txt, rect)
    txt = txtFont.render("E" , 1, txtColor)
    rect = txt.get_rect()
    rect.centerx, rect.centery = self.getxyD(6,90)
    self.bg.blit(txt, rect)
    txt = txtFont.render("W" , 1, txtColor)
    rect = txt.get_rect()
    rect.centerx, rect.centery = self.getxyD(7,270)
    self.bg.blit(txt, rect)

    self.screen.blit(self.bg, (0,0)) # blit background to screen ???
    pygame.display.update()  # flip?

  def plotStars(self, obs):
    self.obs = obs # update the observer

    for star in stars:
        star.compute(self.obs)
        if star.alt > 0:
          brt = int((7-star.mag)*24+75+0.5)
          if brt>255: brt = 255
          if self.Colors.RedOnly:
            starColor = (brt,0,0)
          else:
            starColor = (brt,brt,brt)
          pygame.draw.circle(self.screen, starColor, self.getxy(star.alt, star.az), 1, 1) # 1 pixel dots
#          sz = int(brt/87 + 0.5) # size proportional to brightness
#          if star.mag<0:    sz = 2
#          elif star.mag < 2: sz = 2
#          else:              sz = 1
#          if sz<=1: # minimum radius - pygame draws small circles as funny squares
#            pygame.draw.circle(self.screen, (brt,brt,brt), self.getxy(star.alt, star.az), 1, 1)
#          else:
#            pygame.draw.circle(self.screen, (brt,brt,brt), self.getxy(star.alt, star.az), sz, 0)
#            print 'star {} mag {} sz {}'.format(star.name, star.mag, sz)
        del star

# plot 5 circles to test plot
#    pygame.draw.circle(screen, (0,255,0), self.getxy(math.radians(90), math.radians(0)), 5, 1) # center
#    pygame.draw.circle(screen, (255,0,0), self.getxy(math.radians(45), math.radians(0)), 5, 1) # red N
#    pygame.draw.circle(screen, (0,255,0), self.getxy(math.radians(45), math.radians(90)), 5, 1) # green E
#    pygame.draw.circle(screen, (0,0,255), self.getxy(math.radians(45), math.radians(180)), 5, 1) # blue S
#    pygame.draw.circle(screen, (255,255,0), self.getxy(math.radians(45), math.radians(270)), 5, 1) # yellow W


#  def plotStar(self, name):
#    star = ephem.star(name)
#    star.compute(self.obs)
#    if star.alt > 0:
#      pygame.draw.circle(self.screen, (255,255,255), self.getxy(star.alt, star.az), 1, 1)


  def plotPlanets(self, obs):

    self.obs = obs # update the observer

    moon = ephem.Moon()
    sun = ephem.Sun()

    if self.Colors.RedOnly:
      self.plotPlanet('6', ephem.Saturn(), (225,32,64), 7, self.pFont)
      self.plotPlanet('5', ephem.Jupiter(),(225,64,32), 7, self.pFont)
      self.plotPlanet('4', ephem.Mars(),  (225,0,0), 7, self.pFont)
      self.plotPlanet('2', ephem.Venus(), (225,64,64), 7, self.pFont)
      self.plotPlanet('1', ephem.Mercury(), (225,32,32), 7, self.pFont)
      self.plotPlanet('M', ephem.Moon(), self.Colors.White, 9, self.pFont)
      self.plotPlanet('S', ephem.Sun(), self.Colors.Yellow, 9, self.pFont)
    else:
      self.plotPlanet('6', ephem.Saturn(), (225,120,225), 7, self.pFont)
      self.plotPlanet('5', ephem.Jupiter(),(225,225,120), 7, self.pFont)
      self.plotPlanet('4', ephem.Mars(),  (225,0,0), 7, self.pFont)
      self.plotPlanet('2', ephem.Venus(), (225,225,225), 7, self.pFont)
      self.plotPlanet('1', ephem.Mercury(), (120,225,225), 7, self.pFont)
      self.plotPlanet('M', ephem.Moon(), self.Colors.White, 9, self.pFont)
      self.plotPlanet('S', ephem.Sun(), self.Colors.Yellow, 9, self.pFont)

  def plotPlanet(self, pnum, planet, color, size, font):
    txtFont = pygame.font.SysFont('Arial',font, bold=True)
    pFont = pygame.font.SysFont('Arial', font-3, bold=True)
    planet.compute(self.obs)
#    print "{} alt: {} az:{}".format(planet.name, math.degrees(planet.alt), math.degrees(planet.az))
    if (planet.alt>0):
#      pygame.draw.circle(self.screen, color, self.getxy(planet.alt, planet.az), size, 0)
      pos = self.getxy(planet.alt, planet.az)
      pygame.draw.circle(self.screen, color, pos, size, 0)
      txt = pFont.render(pnum, 1, self.Colors.Black)
      txtr = txt.get_rect()
      txtr.centerx,txtr.centery = pos[0], pos[1]+1
      self.screen.blit(txt,txtr)
      txt = txtFont.render(pnum + ' ' + planet.name, 1, color, (0,0,0))
      txtr = txt.get_rect()
      self.pLine -= txtr.height
      self.screen.blit(txt, (0, self.pLine))

