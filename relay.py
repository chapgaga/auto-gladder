from socket import *
import select

import thread

class Relay:
    def __init__(self, port):
        self.s = socket(AF_INET, SOCK_STREAM)
        self.s.bind(("0.0.0.0", port))
        self.s.listen(5)
        

    def loop(self):
        while True:
            sock, peer = self.s.accept()
            thread.start_new(self.proxy, (sock, ))

    def proxy(self, sock):
        cmd_line = sock.recv(128)

        host, port = cmd_line.split(":")[:2]
        print "connect to:", host, port

        sock2 = socket(AF_INET, SOCK_STREAM)
        sock2.connect((host, int(port)))

        p = select.poll()
        p.register(sock2, select.POLLIN)
        p.register(sock, select.POLLIN)

        while True:
            ret = p.poll()
            for fd, evt in ret:
                if fd == sock.fileno():
                    data = sock.recv(4096)
                    sock2.send(data)
                else:
                    data = sock2.recv(4096)
                    sock.send(data)

def main():
    r=Relay(7777)
    r.loop()

main()
        