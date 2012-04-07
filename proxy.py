from socket import *

class ProxyInterface:
    def __init__(self):
        self.connect_fds = {}
        pass

    def get_connection(self, dst_addr):
        s = socket(AF_INET, SOCK_STREAM)
        dst_port = dst_addr[1]
        s.connect(("192.168.1.20", dst_port)) # a fake connection used for testing only
        fd = s.fileno()
        self.connect_fds [fd] = s # cache it to avoid GC
        print "connected:", fd
        return s

    def register_private_proxy(self, addr, port):
        pass

    def register_socks5_proxy(self, addr, port):
        pass

    def register_http_proxy(self, addr, port):
        pass

    def close_connection(self, fd):
        f = self.connect_fds[fd]
        f.close()
        del self.connect_fds[fd]

Proxy = ProxyInterface()