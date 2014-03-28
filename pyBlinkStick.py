from blinkstick import blinkstick
import threading
from time import sleep

# from Arduino
def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;

class BlinkStick():

  def __init__(self, mag=0, alt=0, count=1):
    self.mag = mag
    self.alt = alt
    self.bstick = blinkstick.find_first()
    self.running = False
    self.thread = 0
    self.count = count
    self._run = False
    self.lock = threading.Lock()
    self.Red = True
    self.Green = True
    self.Blue = True

  def blink(self, count=-1):
    with self.lock:
      if self.running:
        print "bl: error already running"
        return
      self.running = True
      if count>0:
        self.count = count
    repeat=1
    steps = 10
    count = self.count # + 0 # make a copy
#    print "blink {}".format(count)
    while self._run and count>0:
      dm = map(self.mag, 0, -6, 4, 255)
      if (dm>255): dm = 255
      if (dm<0): dm = 4
      da = map(self.alt, 0, 90, 500, 33)
#      print "bl mag: {:3.1f} alt: {:3.1f} dm:{:3.0f} da:{:3.0f}".format(self.mag,self.alt,dm,da)
      if self.Red:   self.bstick.pulse(dm,0,0,None,None,repeat,da,steps) # red
      if self.Green: self.bstick.pulse(0,dm,0,None,None,repeat,da,steps) # green
      if self.Blue:  self.bstick.pulse(0,0,dm,None,None,repeat,da,steps) # blue
      count -= 1
    self.bstick.turn_off()
    with self.lock:
      self.running = False
#    print "bl: stop {}".format(self.count)

  def set(self, mag, alt, count=1):
    with self.lock:
      self.alt = alt
      self.mag = mag
      self.count = count

  def start(self, mag, alt, count=1):
    with self.lock:
      self.alt = alt
      self.mag = mag
      self.count = count
      if self.running == False:
#        print "bl: start thread"
        self._run = True
        self.thread = threading.Thread(target = self.blink)
        self.thread.start()

  def stop(self):
    with self.lock:
      self._run = False # stop loop
#    while self.running :
#      sleep(0.1)

