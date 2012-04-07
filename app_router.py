from phy_interface import VirtualInterface
from threadpool import *               # we'll need thread pool, please easy_install threadpool it.
import os

from app_ip_stack import IPStack
from abstracts import AbstractStack

def bring_up_script(vif_name):
    script=['ifconfig %s 192.168.0.40',
            'route add -net 192.168.0.0/24 %s']

    for cmd in script:
        os.system(cmd % vif_name)

POOL_SIZE = 50

class Router(AbstractStack):
    def __init__(self):
        AbstractStack.__init__(self)
        self.vif = VirtualInterface()
        bring_up_script(self.vif.ifname)
        self.pool = ThreadPool(POOL_SIZE)

    def loop(self):
        while True:
            data = self.vif.read(1600) # controlled by MTU
#            print "data recv from vif:", repr(data)
            IPStack(self, data) # just create object, the rest will be automatically

if __name__=="__main__":
    Router().loop()