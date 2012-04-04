from phy_interface import VirtualInterface
from threadpool import *               # we'll need thread pool, please easy_install threadpool it.

def bring_up_script(vif_name):
    script=['ifconfig %s 192.168.0.40',
            'route add -net 192.168.0.0/24 %s']

    for cmd in script:
        os.system(cmd % vif_name)

POOL_SIZE = 50

class Router:
    def __init__(self):
        self.vif = VirtualInterface()
        bring_up_script(self.vif.ifname)
        self.pool = ThreadPool(POOL_SIZE)

    def loop(self):
        while True:
            data = self.vif.read(1600) # controlled by MTU
            ip=IPStack(self, data)

