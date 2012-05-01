
from select import epoll, EPOLLIN
import thread, os
import time
#from threading import Condition

class AsyncIO:
    "connect network socket with Queue"
    def __init__(self):
        self.fd_pool={}         # fd -> queue mapping
        self.epoll = epoll()
#        self.cond = Condition()
        thread.start_new_thread(self.loop, ())

    def connect(self, fd, queue, mtu=0, tag='income'):
        print "### register:", fd
        self.fd_pool[fd] = queue
        queue.mtu = mtu
        queue.tag = tag
        self.epoll.register(fd, EPOLLIN)

    def loop(self):
        try:
            self._loop()
        except:
            import traceback
            traceback.print_exc()

    def _loop(self):
        while True:
            if not self.fd_pool: 
                time.sleep(0.1)
                continue

            ret = self.epoll.poll()
            for fd, evt in ret:
                data = os.read(fd, 4096)
                if not data:    # pipe broken! remove it
                    self.disconnect(fd)
                    continue
                queue = self.fd_pool[fd]

                if queue.mtu:                    # frag needed!
                    while len(data) > queue.mtu: # frag
                        queue.put((queue.tag, fd, data[:queue.mtu]))
                        data = data[queue.mtu:]
                queue.put((queue.tag, fd, data))

    def disconnect(self, fd):
        print "### disconnect:", fd
        self.epoll.unregister(fd)
        del self.fd_pool[fd]

ASIO=AsyncIO()


def test():
    import os, Queue, time
    p=os.pipe()

    q=Queue.Queue()
    
    ASIO.connect(p[0],q)
    os.write(p[1],'hello')
    print q.get()

if __name__=="__main__":
    test()
