from phy_interface import PhyInterface
from threadpool import *               # we'll need thread pool, please easy_install threadpool it.
import os

from app_ip_stack import IPStack
from app_mac_stack import MACStack
from abstracts import AbstractStack
from environment import Environment


POOL_SIZE = 50

class Router(AbstractStack):
    """
    Application Router
     - Receive packages from tun device
     - Substract layer 4 information and forward through TCP connection to relay node
    """
    def __init__(self):
        AbstractStack.__init__(self)
        self.pif = PhyInterface(Environment.default_if) # open main physical interface for injection
#        bring_if_up(self.pif.ifname)
        self.pool = ThreadPool(POOL_SIZE)

    def loop(self):
        while True:
            data = self.pif.read(1600) # controlled by MTU
#            print "data recv from vif:", repr(data)
            MACStack(self, data)
#            IPStack(self, data) # just create object, it'll do the rest automatically


if __name__=="__main__":
    import thread, time
    from event import Event
    def timeout_loop():
        time.sleep(1)
        Event.check_timeout()

    thread.start_new(timeout_loop, ())

    Router().loop()



