#!/usr/bin/python
import array, fcntl
from time import sleep
# test program to read state of buttons on HwLevel LCD display for Raspberry Pi
# 12 March 2014 - William B Phelps - wm@usa.net
# no warranty of any kind, use at your own risk

#SSD1289_GET_KEYS = -2147202303

_IOC_NRBITS   =  8
_IOC_TYPEBITS =  8
_IOC_SIZEBITS = 14
_IOC_DIRBITS  =  2

_IOC_DIRMASK    = (1 << _IOC_DIRBITS) - 1
_IOC_NRMASK     = (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK   = (1 << _IOC_TYPEBITS ) - 1

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT+_IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT+_IOC_TYPEBITS
_IOC_DIRSHIFT  = _IOC_SIZESHIFT+_IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2

def _IOC(dir, type, nr, size):
#  print 'dirshift {}, typeshift {}, nrshift {}, sizeshift {}'.format(_IOC_DIRSHIFT, _IOC_TYPESHIFT, _IOC_NRSHIFT, _IOC_SIZESHIFT)
  ioc = (dir << _IOC_DIRSHIFT ) | (type << _IOC_TYPESHIFT ) | (nr << _IOC_NRSHIFT ) | (size << _IOC_SIZESHIFT)
  if ioc > 2147483647: ioc -= 4294967296
  return ioc
#def _IO(type, nr):
#  return _IOC(_IOC_NONE,  type, nr, 0)

def _IOR(type,nr,size):
  return _IOC(_IOC_READ,  type, nr, size)
#def _IOW(type,nr,size):
#  return _IOC(_IOC_WRITE, type, nr, sizeof(size))

class lcdButtons():

  def __init__(self):

    self.SSD1289_GET_KEYS = _IOR(ord('K'), 1, 4)
    #print 'ssd {} {:12} {:0>8x} {:0>32b}'.format(ssd1289, hex(ssd1289), ssd1289, ssd1289)
    self.buf = array.array('h',[0])

  def get(self):

    with open('/dev/fb1', 'rw') as fd:

      fcntl.ioctl(fd, self.SSD1289_GET_KEYS, self.buf, 1) # read the key register
      keybits = 0b11111-self.buf[0] # invert so bits show key pressed
  
      self.buttons = (keybits & 0b10000 > 0, keybits & 0b01000 > 0, keybits & 0b00100 > 0, keybits & 0b00010 > 0, keybits & 0b00001 > 0)
      self.keybits = keybits
      return self.buttons

