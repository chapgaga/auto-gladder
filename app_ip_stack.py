from abstracts import AbstractStack

from app_tcp_stack import TCPStack
from app_udp_stack import UDPStack
from app_icmp_stack import ICMPStack
IPPROTO_TCP = 6
IPPROTO_ICMP = 1
IPPROTO_UDP = 17

class IPStack(AbstractStack):
    def parse(self, incoming_data):
        data = [ord(x) for x in incoming_data[:20]]
        self.version = data[0] >> 4
        self.headlen = data[0] & 0xf
        self.issegment = (data[6]>>5) & 0x3
        self.segment_id = ((data[6] & 0x1f) << 8) + data[7]
        self.TTL = data[8]
        self.protocol = data[9]
        self.src_ip = data[12:16]
        self.dst_ip = data[16:20]


    def do(self):
        if self.protocol == IPPROTO_UDP:
            self.next = UDPStack(self, data[headlen:])
        elif self.protocol == IPPROTO_TCP:
            self.next = TCPStack(self, data[headlen:])
        elif self.protocol == IPPROTO_ICMP:
            self.next = ICMPStack(self, data[headlen:])


