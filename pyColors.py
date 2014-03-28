class pyColors:

  def __init__(self):
    self.Black = (0,0,0)
    self.setNormal()


  def setNormal(self):
    self.RedOnly = False
    self.Red = (255,0,0)
    self.Orange = (255,127,0)
    self.Green = (0,255,0)
    self.Blue = (0,0,255)
    self.LightBlue = (0,127,255)
    self.Yellow = (255,255,0)
    self.DarkYellow = (225,225,0)
    self.Cyan = (0,255,255)
    self.DarkCyan = (0,225,225)
    self.Magenta = (255,0,255)
    self.White = (255,255,255)

  def setRed(self):
    self.RedOnly = True
    self.Red = (255,0,0)
    self.Orange = (255,64,0)
    self.Green = (225,96,0)
    self.Blue = (192,0,0)
    self.LightBlue = (255,0,64)
    self.Yellow = (255,64,0)
    self.DarkYellow = (225,64,0)
    self.Cyan = (192,0,64)
    self.DarkCyan = (160,0,32)
    self.Magenta = (255,0,32)
    self.White = (255,0,0)

