import os, fcntl

from tap_support import tun_open

class VirtualInterface:
    count=0
    def __init__(self, ifname='vif'):
        self.ifname = ifname+str(VirtualInterface.count)
        self.ifd = tun_open(self.ifname, istap=0)

    def read(self, size=4096):
        return os.read(self.ifd, size)

    def write(self, buf):
        return os.write(self.ifd, buf)

    def close(self):
        os.close(self.ifd)

    def __repr__(self):
        return "<VInterface:%s, fd:%d>" % (self.if_name, self.ifd)

    __str__=__repr__


def test():
    vf = VirtualInterface()
    while True:
        print "read:", repr(vf.read(1024))
        

if __name__=="__main__":
    test()
