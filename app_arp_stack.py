from abstracts import AbstractStack, register_stacks
from app_ip_stack import IPStack
import struct
from utils import pack, unpack
from environment import Environment
from exception import ARPLookupException

ETHERTYPE_IP      =      0x0800
ETHERTYPE_ARP     =      0x0806


class _ARPTable:
    table={}
    rtable={}
    padding={}
    def update(self, ip, mac):
        self.table[ip]=mac
        self.rtable[mac]=ip
        if ip in self.padding:
            for op in self.padding[ip]:
                op()
            del self.padding[ip]

    def lookup(self, ip):
        try:
            return self.table[ip]
        except KeyError:
            raise ARPLookupException(ip)

    def padding_operation(self, root, ip, operation):
        if ip in self.padding:
            self.padding.append(operation)
        else:
            self.padding[ip]=[operation]
            arp_query(root, ip)

ARPTable = _ARPTable()

OPCODE_REQUEST    = 1
OPCODE_REPLY      = 2
class ARPStack(AbstractStack):
    """
    Application Arp Stack
    """
    def parse(self, incoming_data):
        self.hardware_type = unpack("!H", incoming_data[:2]) # should be 1
        assert self.hardware_type == 1

        self.protocol = unpack("!H", incoming_data[2:4])     # should be ETHERTYPE_IP
        assert self.protocol == ETHERTYPE_IP

        self.hardware_size = ord(incoming_data[4])           # should be 6
        assert self.hardware_size == 6

        self.protocol_size = ord(incoming_data[5])           # should be 4
        assert self.protocol_size == 4

        self.opcode = unpack("!H", incoming_data[6:8])
        self.sender_mac = incoming_data[8:14]
        self.sender_ip  = tuple([ord(x) for x in incoming_data[14:18]])
        self.target_mac = incoming_data[18:24]
        self.target_ip  = tuple([ord(x) for x in incoming_data[24:28]])
        self.headlen = 28

    def do(self):
        # dispatch to next stack
        if self.opcode == OPCODE_REQUEST:
            # who has `target_ip`, tell `sender_mac/sender_ip`
            if self.target_ip == Environment.virtual_if_ip:
                self.send(self.parent.fork(dst_mac = self.sender_mac, # mac layer
                                           src_mac = Environment.virtual_if_mac),
                          self.fork(opcode = OPCODE_REPLY, # arp reply package
                                    sender_mac = Environment.virtual_if_mac,
                                    sender_ip  = Environment.virtual_if_ip,
                                    target_mac = self.sender_mac,
                                    target_ip  = self.sender_ip),
                      )
        elif self.opcode == OPCODE_REPLY:
            # `sender_ip` is at `sender_mac`
            ARPTable.update(self.sender_ip, self.sender_mac)
            

    def pack(self, payload, peek=None):
        return "\x00\x01\x08\x00\x06\x04"+pack("!H", self.opcode) + self.sender_mac + \
            "".join([chr(x) for x in self.sender_ip]) + self.target_mac + "".join([chr(x) for x in self.target_ip]) + payload


def arp_query(root, ip):
    pkgs = root.construct(AbstractStack._macstack.new(dst_mac = '\xff'*6,
                                                      src_mac = Environment.virtual_if_mac,
                                                      protocol = ETHERTYPE_ARP
                                                  ),
                          ARPStack.new(opcode = OPCODE_REQUEST,
                                       sender_mac = Environment.virtual_if_mac,
                                       sender_ip  = Environment.virtual_if_ip,
                                       target_mac = '\xff'*6,
                                       target_ip  = ip
                                   ))
    pkgs[0].send(*pkgs)

register_stacks('_arptable', ARPTable)