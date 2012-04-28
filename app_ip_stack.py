from abstracts import AbstractStack, register_stacks

from app_tcp_stack import TCPStack
from app_udp_stack import UDPStack
from app_icmp_stack import ICMPStack
IPPROTO_TCP = 6
IPPROTO_ICMP = 1
IPPROTO_UDP = 17

import struct
from utils import pack, unpack, checksum

class IPStack(AbstractStack):
    """
    Application IP Stack
      - IP package encoding and decoding
      - need to support IP fragment
    """
    def parse(self, incoming_data):
        data = [ord(x) for x in incoming_data[:20]]
        self.version = data[0] >> 4
        self.headlen = (data[0] & 0xf) * 4
        self.identification = unpack("!H", incoming_data[4:6])
        self.flags = (data[6]>>5)
        self.segment_id = ((data[6] & 0x1f) << 8) + data[7]
        self.TTL = data[8]
        self.protocol = data[9]
        self.src_ip = tuple(data[12:16])
        self.dst_ip = tuple(data[16:20])

    def do(self):
        # dispatch to next stack
        if self.protocol == IPPROTO_UDP:
            self.next = UDPStack(self, self.payload)
        elif self.protocol == IPPROTO_TCP:
            self.next = TCPStack(self, self.payload)
        elif self.protocol == IPPROTO_ICMP:
            self.next = ICMPStack(self, self.payload)


    def pack(self, payload, peek=None):
        s1 = chr((self.version << 4) + (self.headlen / 4))
        s2 = chr(0)             # different service field
        s3 = pack("!H", 20+len(payload))            
        s4 = pack("!H", self.identification)
        s5 = chr((self.flags <<5)+ (self.segment_id >> 8))
        s6 = chr(self.segment_id & 0xff)
        s7 = chr(self.TTL)
        s8 = chr(self.protocol)
        s10 = "".join([chr(x) for x in self.src_ip])
        s11 = "".join([chr(x) for x in self.dst_ip])
        s9 = pack("!H", checksum(s1+s2+s3+s4+s5+s6+s7+s8+s10+s11))

        return s1+s2+s3+s4+s5+s6+s7+s8+s9+s10+s11+payload


register_stacks('_ipstack', IPStack)