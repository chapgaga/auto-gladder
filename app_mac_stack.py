from abstracts import AbstractStack, register_stacks

from app_ip_stack import IPStack
from app_arp_stack import ARPStack

import struct
from utils import pack, unpack

ETHERTYPE_IP      =      0x0800
ETHERTYPE_ARP     =      0x0806

from environment import Environment

from app_arp_stack import ARPTable

BROADCAST_MAC  = '\xff'*6

class MACStack(AbstractStack):
    """
    Application Mac Stack
    """
    def parse(self, incoming_data):
        self.dst_mac = incoming_data[:6]
        self.src_mac = incoming_data[6:12]
        self.protocol = unpack("!H", incoming_data[12:14])
        self.headlen = 14

    def do(self):
        # dispatch to next stack
        if not (self.dst_mac == Environment.virtual_if_mac or self.dst_mac == BROADCAST_MAC): # drop package
            return

        if self.protocol == ETHERTYPE_IP:
            self.next = IPStack(self, self.payload)
        elif self.protocol == ETHERTYPE_ARP:
            self.next = ARPStack(self, self.payload)

    def pack(self, payload, peek=None):
        return self.dst_mac + self.src_mac + pack("!H", self.protocol) + payload

    @classmethod
    def new_from_ip(cls, ip_stack):
        stack = cls()
        stack.src_mac = Environment.virtual_if_mac
        stack.protocol = ETHERTYPE_IP
        stack.dst_mac = ARPTable.lookup(ip_stack.dst_ip)

        return stack

register_stacks('_macstack', MACStack)