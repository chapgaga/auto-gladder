import os, struct, fcntl
import array
from socket import AF_UNIX

# ported from ioctl
_IOC_READ=2
_IOC_WRITE=1
_IOC_NONE=0

_IOC_NRBITS   =  8
_IOC_TYPEBITS =  8

_IOC_SIZEBITS=14
_IOC_DIRBITS=2
_IOC_NRMASK  = ((1 << _IOC_NRBITS)-1)
_IOC_TYPEMASK= ((1 << _IOC_TYPEBITS)-1)
_IOC_SIZEMASK= ((1 << _IOC_SIZEBITS)-1)
_IOC_DIRMASK = ((1 << _IOC_DIRBITS)-1)

_IOC_NRSHIFT=0
_IOC_TYPESHIFT=_IOC_NRSHIFT+_IOC_NRBITS
_IOC_SIZESHIFT=_IOC_TYPESHIFT+_IOC_TYPEBITS
_IOC_DIRSHIFT=_IOC_SIZESHIFT+_IOC_SIZEBITS


def _IOC(dir, type, nr, size):  return  (((dir)  << _IOC_DIRSHIFT) | ((type) << _IOC_TYPESHIFT) |  ((nr)   << _IOC_NRSHIFT) | ((size) << _IOC_SIZESHIFT))
def _IOW(type,nr,size): return  _IOC(_IOC_WRITE,ord(type),nr,size)

TUNSETIFF=_IOW('T', 202, 4)

IF_NAMESIZE =16

IFF_TUN=0x0001
IFF_TAP=0x0002
IFF_NO_PI=0x1000

SIOCGIFHWADDR = 0x8927
SIOCSIFHWADDR = 0x8924

def tun_open(ifname, istap=1, mac=None):
    fd = os.open("/dev/net/tun", os.O_RDWR)
    
    ifr_struct = '%dsh' % IF_NAMESIZE

    if istap: mode = IFF_TAP
    else:     mode = IFF_TUN

    ifr = struct.pack(ifr_struct, ifname, mode | IFF_NO_PI)
    fcntl.ioctl(fd, TUNSETIFF, ifr)

    if istap and mac:                     # set mac
        ifr = struct.pack(ifr_struct, ifname, AF_UNIX) + mac
        fcntl.ioctl(fd, SIOCSIFHWADDR, ifr)

    return fd

def get_mac(fd, ifname):
    buf = array.array('c', ifname+'\0'*32)
    fcntl.ioctl(fd, SIOCGIFHWADDR, buf, 1)
    mac= buf[IF_NAMESIZE+2:IF_NAMESIZE+2+6] # struct: ifname(16 bytes), AF_UNIX(short), MAC(6 bytes)
    return mac.tostring()

