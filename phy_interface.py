import os, fcntl

from tap_support import tun_open, get_mac
from phy_support import promisc_open, raw_sendto

from environment import get_mac_by_if

class VirtualInterface(object):
    count=0
    def __init__(self, ifname='vif', mac=None):
        self.mac = None
        self.ifname = ifname+str(VirtualInterface.count)
        self.ifd = tun_open(self.ifname, istap=1, mac=mac)
        self.mac = get_mac(self.ifd, self.ifname)

    def read(self, size=4096):
        return os.read(self.ifd, size)

    def write(self, buf):
        return os.write(self.ifd, buf)

    def close(self):
        os.close(self.ifd)

    def __repr__(self):
        return "<%s:%s, fd:%d>" % (self.__class__.__name__, self.if_name, self.ifd)

    __str__=__repr__

    def get_mac(self):
        if not self.mac:
            self.mac = get_mac_by_if(self.ifname)
        return self.mac


class PhyInterface(VirtualInterface):
    def __init__(self, ifname='eth1'):
        self.mac = get_mac_by_if(ifname)
        self.ifname = ifname
        self.s = promisc_open(ifname)
        self.ifd = self.s.fileno()

    def write(self, buf):
        return raw_sendto(self.ifname, self.s, buf)


def test():
    pf = PhyInterface()
    print "mac:", repr(pf.mac)
    while True:
        print "read:", repr(pf.read(1024))
        

if __name__=="__main__":
    test()

