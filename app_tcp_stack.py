from abstracts import AbstractStack
import struct
from threadpool import *
from Queue import Queue, Empty
from asio import ASIO

QUEUE_LENGTH = 128
DATA_QUEUE_LENGTH = 1024
class TCPStatus:
    def __init__(self, tcp_stack):
        self.tcp_stack = tcp_stack
        self.status='syn'
        self.queue = Queue(QUEUE_LENGTH)
SYN=2
FIN=1
RESET=4
PUSH=8
ACK=16

class TCPStack(AbstractStack):
    ConnectionPair={}

    def __init__(self, *args, **kwargs):
        AbstractStack.__init__(self, *args, **kwargs)

    def parse(self, incoming_data):
        self.src_port = struct.unpack("!H", data[:2])
        self.dst_port = struct.unpack("!H", data[2:4])

        self.seq_num = struct.unpack("!I", data[4:8])
        self.ack_num = struct.unpack("!I", data[8:12])
        self.header_len = (ord(data[12]) >> 4) * 4 # head len is counted as 4 byte words
        self.flags = ((ord(data[12]) & 1) << 8) + (ord(data[13]))
        self.window = struct.unpack("!H", data[14:16])
        
        if self.header_len>20:       # have option
            self.option_max_seg_size=struct.unpack("!I", data[20:24])
        self.data = incoming_data[self.header_len:]

    def do(self):
        # check flags:
        if self.flags & SYN:
            # tcp syn? stage1, init connection and connect to remote
            pair = self.get_connection_pair()
            cp = TCPStack.ConnectionPair
            pool = self.parent.parent.pool
            if pair in cp: # weird!
                print "Warning, duplicated connection on tcp sync stage"
                cp[pair] = TCPStatus(self)
                pool.putRequest(WorkRequest(self.tcp_forward, (cp[pair], )))
        else:
            pair = self.get_connection_pair()
            cp = TCPStatus.ConnectionPair
            cp[pair].queue.put(('outcome', self))


    def get_connection_pair(self):
        pair = (self.parent.src_ip, self.src_port, self.parent.dst_ip, self.dst_port)
        return pair

    def tcp_forward(self, tcp_status):
        pair = self.get_connection_pair()
        dst_addr = pair[2:]
        try:
            fd = Proxy.get_connection(dst_addr)
        except:                 # connection timeout, reset, ... ...
            pass
        # connected, send back syn ack
        tcp_status.fd = fd
        tcp_status.queue = Queue(DATA_QUEUE_LENGTH)

        # send SYN/ACK response pkg
        self.send(self.parent.fork(src_ip = pair[2], dst_ip = pair[0]), # IP Layer
                  self.fork(src_port = pair[3], dst_port = pair[1], # TCP Layer
                            flags = SYN | ACK,
                            windows = 65535
                            )
                  )

        ASIO.connect(fd, tcp_status.queue)
        buf=[]
        while True:
            try:
                tag, pkg = tcp_status.queue.get(timeout=0.05)
            except Empty:
                tag = 'check_buf'
            if tag == 'income': # incoming data, cache first
                buf.append(tag)
                last_pkg = self
            elif tag == 'outcome':
                if pkg.data:
                    os.write(fd, pkg.data)
                    # send ACK
                    self.send(self.parent.fork(src_ip = pair[2], dst_ip = pair[0]), # IP Layer
                              pkg.fork(src_port = pair[3], dst_port = pair[1], # TCP Layer
                                       flags = ACK,
                                       windows = 65535,
                                       ack_num = pkg.seq_num
                                       )
                              )
            elif tag == 'check_buf':
                if buf:         # we have padding data, send it
                    os.write(fd, "".join(buf))
                    buf=[]
                    #  and send ACK
                    self.send(self.parent.fork(src_ip = pair[2], dst_ip = pair[0]), # IP Layer
                              last_pkg.fork(src_port = pair[3], dst_port = pair[1], # TCP Layer
                                            flags = ACK,
                                            windows = 65535,
                                            ack_num = last_pkg.seq_num
                                        )
                              )

            
