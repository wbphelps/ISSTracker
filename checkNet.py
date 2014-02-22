# check for working network
# uses "netifaces" from https://github.com/raphdg/netifaces
import netifaces

class checkNet:

    def __init__(self):
        self.interface = None
        self.address = None
        self.broadcast = None
        self.netmask = None
        self.up = False

        ifaces = netifaces.interfaces()
        for iface in ifaces:
#            print 'iface {}'.format(iface)
            if iface == 'lo': continue
            addr = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addr:
                ifdata = addr[netifaces.AF_INET][0] # yes there could be more than one, but hopefully not...
                self.interface = iface
                self.address = ifdata['addr']
                self.broadcast = ifdata['broadcast']
                self.netmask = ifdata['netmask']
 #               print 'iface {} up'.format(iface)
                self.up = True
                break
