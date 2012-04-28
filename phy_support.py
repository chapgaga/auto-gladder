
from socket import AF_PACKET, SOCK_RAW, socket, htons
import fcntl, os, struct


ETH_P_ALL       = 0x0003
PACKET_OUTGOING = 4

SIOCGIFFLAGS    = 0x8913
SIOCSIFFLAGS    = 0x8914
SIOCGIFINDEX	= 0x8933
IFF_PROMISC	= 0x100

IF_NAMESIZE     = 16

def promisc_open(ifname):
    """
    Open a promisc socket on `ifname`.
    return: socket object
    """
    s = socket(AF_PACKET, SOCK_RAW, ETH_P_ALL) # proto need htons?

    ifr_struct = '%dsh' % IF_NAMESIZE
    ifr = struct.pack(ifr_struct, ifname, 0)
    ret = fcntl.ioctl(s.fileno(), SIOCGIFFLAGS, ifr)

#    print repr(ret)
    flags = struct.unpack(ifr_struct, ret)[1]
    ifr = struct.pack(ifr_struct, ifname, flags | IFF_PROMISC)

    fcntl.ioctl(s.fileno(), SIOCSIFFLAGS, ifr)

#    idx = fcntl.ioctl(s.fileno(), SIOCGIFINDEX, ifr)
#    ifr_ifindex = #FIXME
#    iface_bind(s.fileno(), ifr_ifindex)

    s.bind((ifname, ETH_P_ALL))

    return s #, ifr_ifindex


def raw_sendto(ifname, s, data):
    return s.sendto(data, 0, (ifname, ETH_P_ALL, PACKET_OUTGOING, 0, data[:6]))

def test():
    s = promisc_open("eth0")
    fd = s.fileno()
    while True:
        print "read:", repr(os.read(fd, 4096))

if __name__=="__main__":
    test()
