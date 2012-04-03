from phy_interface import VirtualInterface


def bring_up_script(vif_name):
    script=['ifconfig %s 192.168.0.40',
            'route add -net 192.168.0.0/24 %s']

    for cmd in script:
        os.system(cmd % vif_name)

IPPROTO_TCP = 6
IPPROTO_ICMP = 1
IPPROTO_UDP = 17
class Router:
    def __init__(self):
        self.vif = VirtualInterface()
        bring_up_script(self.vif.ifname)

    def loop(self):
        while True:
            data = self.vif.read(1600) # controlled by MTU
            self.parse_ip(data)

    def parse_ip(self, incoming_data):
        # parse IP header
        data = [ord(x) for x in incoming_data[:20]]
        version = data[0] >> 4
        headlen = data[0] & 0xf
        issegment = (data[6]>>5) & 0x3
        segment_id = ((data[6] & 0x1f) << 8) + data[7]
        TTL = data[8]
        protocol = data[9]
        src_ip = data[12:16]
        dst_ip = data[16:20]

        if protocol == IPPROTO_UDP:
            self.do_udp_forward(data[headlen:])
        elif protocol == IPPROTO_TCP:
            self.do_tcp_forward(data[headlen:])
        elif protocol == IPPROTO_ICMP:
            self.do_icmp_forward(data[headlen:])
    
    def do_udp_forward(self, data):
        # parse udp
        src_port = struct.unpack("!H", data[:2])
        dst_port = struct.unpack("!H", data[2:4])
        length = struct.unpack("!H", data[4:6])

        data = data[8:8+length]

        # check if it is a dns query
        if dst_port == 53:      # DNS?
            if self.forward_dns(data): return

    
    def do_icmp_forward(self, data):
        pass

    def do_tcp_forward(self, data):
        src_port = struct.unpack("!H", data[:2])
        dst_port = struct.unpack("!H", data[2:4])

    def forward_dns(self, data):
        pass
        return False



        
