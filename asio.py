
from select import epoll, EPOLLIN
import thread, os

class AsyncIO:
    def __init__(self):
        self.fd_pool={}         # fd -> queue mapping
        self.epoll = epoll()
        thread.start_new_thread(self.loop, ())


    def connect(self, fd, queue):
        self.fd_pool[fd]=queue
        self.epoll.register(fd, EPOLLIN)

    def loop(self):
        while True:
            ret = self.epoll.poll()
            for fd, evt in ret:
                data = os.read(fd, 4096)
                if not data:    # pipe broken! remove it
                    self.disconnect(fd)
                    continue
                self.fd_pool[fd].put(('income', data))

    def disconnect(self, fd):
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
