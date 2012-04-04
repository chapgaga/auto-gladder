from abstracts import AbstractStack

class UDPStack(AbstractStack):
    def parse(self, incoming_data):
        self.src_port = struct.unpack("!H", data[:2])
        self.dst_port = struct.unpack("!H", data[2:4])
        self.length = struct.unpack("!H", data[4:6])

        self.data = data[8:8+length]


    def do(self):
        # check if it is a dns query
        if dst_port == 53:      # DNS?
            if self.forward_dns(data): return
        
