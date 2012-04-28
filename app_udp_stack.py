from abstracts import AbstractStack

from utils import unpack, pack

class UDPStack(AbstractStack):
    def parse(self, incoming_data):
        self.src_port = unpack("!H", incoming_data[:2])
        self.dst_port = unpack("!H", incoming_data[2:4])
        self.headlen = unpack("!H", incoming_data[4:6])

    def do(self):
        # check if it is a dns query
        if self.dst_port == 53:      # DNS?
            if self.forward_dns(): return
        
    def forward_dns(self):
        if self.payload:        # FIXME, this is a dns description
            pass