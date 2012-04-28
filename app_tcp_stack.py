from abstracts import AbstractStack, DataStack
import struct
from threadpool import *
from Queue import Queue, Empty
from asio import ASIO
from proxy import Proxy
from utils import unpack, pack, checksum, inc_with_mod
import os
from collections import deque
import time


def timestamp():
    "return current time stamp, 32bit, round-trip, ticked by 1ms"
    return int(time.time()*1000) & 0xffffffff

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

    def parse(self, data):
        self.src_port = unpack("!H", data[:2])
        self.dst_port = unpack("!H", data[2:4])

        self.seq_num = unpack("!I", data[4:8])
        self.ack_num = unpack("!I", data[8:12])
        self.headlen = (ord(data[12]) >> 4) * 4 # head len is counted as 4 byte words
        self.flags = ((ord(data[12]) & 1) << 8) + (ord(data[13]))
        self.window = unpack("!H", data[14:16])
        self.urgent = unpack("!H", data[18:20])
        
        if self.headlen>20:       # have option
            self.parse_option(data[20:self.headlen])

    def parse_option(self, option_data):
        p = 0
        while p<len(option_data):
            kind = ord(option_data[p])
            if kind == 0: # end
                break
            elif kind == 1:     # NOP
                p+=1
                continue

            p+=1
            length = ord(option_data[p])

            p+=1
            if kind == 2:       # MAX segment_size
                self.option_max_segment_size = unpack('!H', option_data[p:p+2])
            elif kind == 3:     # Window scale factor
                self.option_window_scale_factor = ord(option_data[p])
            elif kind == 4:     # TCP SACK Permitted Option
                self.option_SACK_Permit = True
            elif kind == 5:     # SACK
                pass
            elif kind == 8:     # time stamp
                self.option_timestamp = struct.unpack("!II", option_data[p:p+8]) # timestamp value / timestamp echo reply
            else:
                print "Warning, unknown TCP options:", kind
            p+=length-2

    def do(self):
        # check flags:
#        self.dump()
        if self.flags & SYN:
            # tcp syn? stage1, init connection and connect to remote

            pair = self.get_connection_pair()
            print "TCP SYNC:", pair

            cp = TCPStack.ConnectionPair
            pool = self.root.pool
            if pair in cp: # weird!
                print "Warning, duplicated connection on tcp sync stage"
            cp[pair] = TCPStatus(self)
            pool.putRequest(WorkRequest(self.tcp_forward, (cp[pair], )))
        else:
            pair = self.get_connection_pair()
            cp = TCPStack.ConnectionPair
            try:
                cp[pair].queue.put(('outcome', None, self))
            except KeyError:    # a connection without SYN, drop
                pass
                

    def pack(self, payload, peek=None):
        s1 = pack("!H", self.src_port)
        s2 = pack("!H", self.dst_port)
        s3 = pack("!I", self.seq_num)
        s4 = pack("!I", self.ack_num)
        s6 = chr(self.flags & 0xff)
        s7 = pack("!H", self.window)
        s9 = pack("!H", self.urgent)
        s10 = self.pack_options()

        self.headlen = len(s1+s2+s3+s4+' '+s6+s7+s9+s10+'  ')
        s5 = chr(((self.headlen /4) <<4) + (self.flags >> 8))

        # construct fake IP header: src_ip, dst_ip, reserved(0x00), protocol(tcp is 0x06), length(header+payload)
        fake_header = "".join([chr(x) for x in peek.src_ip]) + "".join([chr(x) for x in peek.dst_ip]) + "\x00\x06"+pack("!H", self.headlen+len(payload))
        csum = checksum(fake_header + s1+s2+s3+s4+s5+s6+s7+s9+s10+payload)
        s8 = pack("!H", csum)

        return s1+s2+s3+s4+s5+s6+s7+s8+s9+s10+payload

    def pack_options(self):
        opt_str = []
        for option in [x for x in dir(self) if x.startswith("option_")]:
            option_value = getattr(self, option)
            if option == 'option_max_segment_size':
                opt_str.append("\x02\x04"+pack("!H", option_value))
            elif option == 'option_window_scale_factor':
                opt_str.append("\x03\x03"+chr(option_value))
            elif option == 'option_SACK_Permit':
                opt_str.append("\x04\02")
            elif option == 'option_timestamp':
                opt_str.append("\x08\x0a"+struct.pack("!II", *self.option_timestamp))
            else:
                print "Warning, unsupported tcp option:", option
        opt = "".join(opt_str)

#        import ipdb; ipdb.set_trace()

        if len(opt) % 4 >0:     # we have remaining
            opt+="\x01" * (4-(len(opt) % 4)) # use NOP to fill, make it 4 bytes aligned
        return opt

    def get_connection_pair(self):
        pair = (self.parent.src_ip, self.src_port, self.parent.dst_ip, self.dst_port)
        return pair

    def tcp_forward(self, tcp_status):
        try:
            return self._tcp_forward(tcp_status)
        except:
            import traceback; traceback.print_exc()

    def _tcp_forward(self, tcp_status):
        ts = tcp_status
        pair = self.get_connection_pair()
        ts.src_ip , ts.src_port = pair[0], pair[1]
        ts.dst_ip , ts.dst_port = pair[2], pair[3]

        dst_addr = pair[2:]
        try:
            sock = Proxy.get_connection(dst_addr)
        except Exception,e:                 # connection timeout, reset, ... ...
            import traceback
            traceback.print_exc()
            pass
        # connected, send back syn ack
        ts.sock = sock
        ts.queue = Queue(DATA_QUEUE_LENGTH)

        # send SYN/ACK response pkg
        seq_num = id(ts)
        if seq_num<0: seq_num = -seq_num
        ts.seq_num = seq_num & 0xffffffff #  init self seq, which is seq 0

        ts.remote_seq_num = inc_with_mod(self.seq_num, 0xffffffff) # receive remote seq, which is remote seq 0
        ts.last_ack_send = time.time()


        buf = deque()
        resend_buf = deque()

        while True:             # send SYN|ACK repeatly until we get the final ACK
            print "send syn/ack"
            try:
                option_timestamp = (timestamp(),self.option_timestamp[0])
            except:
                option_timestamp = None

            self.send(
                self.parent.fork(src_ip = pair[2], dst_ip = pair[0]), # IP Layer
                self.fork(src_port = pair[3], dst_port = pair[1], # TCP Layer
                          flags = SYN | ACK,
                          ack_num = ts.remote_seq_num, 
                          seq_num = ts.seq_num, # synced package, seq 1
                          window = 14480,
                          option_window_scale_factor=None,
                          option_timestamp= option_timestamp,
                      )
            )
            tag, pkg_fd, pkg = ts.queue.get(timeout=0.1)

            if tag == 'outcome': # we received response
                ts.seq_num = pkg.ack_num
                try:
                    ts.last_timestamp = pkg.option_timestamp[0]
                except:
                    ts.last_timestamp = 0
                break
        print "connection established"

        # Connection established

        ASIO.connect(ts.sock.fileno(), ts.queue)
        
        seq_num = ts.seq_num    # remember base
        remote_seq_num = ts.remote_seq_num # remember base
        while True:
            try:
                tag, pkg = ts.queue.get(timeout=0.1)
                print tag, repr(pkg)
            except Empty:
                tag = 'check_buf'
                if buf: print tag, buf

            if tag == 'income': # incoming data from relay node, cache first
                buf.append(pkg)
            elif tag == 'outcome': # outcoming data from internal net, send to relay node, and send ack to vif, carry incoming data if we have

                try:
                    ts.last_timestamp = pkg.option_timestamp[0]
                except:
                    ts.last_timestamp = 0

                print "outcome seq:", ts.remote_seq_num, ts.seq_num, pkg.seq_num, pkg.ack_num, repr(pkg.payload)

                # first, check this is a valid package
                if pkg.ack_num == ts.seq_num and ts.seq_num!=seq_num: # is it a retransmited package? (make a exception for first package)
                    seq_num=-1
                    payload = ""
                    ts.last_ack_send = 0 # we must force to sent ACK
                elif pkg.payload:  # assume it is a normal package, check payload
                    # we have payload, forward to relay node
                    print "outcome, send payload:", repr(pkg.payload)
                    ts.sock.send(pkg.payload)
#                    ts.sock.flush()

                    # increase remote_seq_num counter, send ACK latter.
                    ts.remote_seq_num = inc_with_mod(ts.remote_seq_num, 0xffffffff, len(pkg.payload))

                    # update my ACK
                    ts.seq_num = pkg.ack_num
                    
                # send ACK
                if buf:         # we have cached incoming data, send it with ACK carried
                    payload = buf.popleft()                    
                else:           # we don't have cached data, send a bare ACK
                    payload = ''

                if payload or time.time()-ts.last_ack_send > 0.2: # we must send it now, no more delay 
                    print "outcome, send ack"
                    self.send_response(ts, payload)
        
            elif tag == 'check_buf': # we don't have outcoming data, 
                if buf:         # however, we do have cached incoming data, send to vif
                    payload = "".join(buf)
                    print "check buf, send payload:", repr(payload)
                    buf.clear()

                    #  and send ACK
                    self.send_response(ts, payload)

    def send_response(self, tcp_status, payload=''):
        ts = tcp_status

        if ts.last_timestamp: option_timestamp = (timestamp(),ts.last_timestamp)
        else: option_timestamp = None

        print "SEQ:", ts.seq_num, "ACK:", ts.remote_seq_num, "payload:", repr(payload)
        self.send(self.parent.fork(src_ip = ts.dst_ip, dst_ip = ts.src_ip), # IP Layer, reverse src and dst, because this is a ACK routine
                  self.fork(src_port = ts.dst_port, dst_port = ts.src_port, # TCP Layer
                            flags = ACK | PUSH,
                            window = 14480,
                            ack_num = ts.remote_seq_num,
                            seq_num = ts.seq_num,
                            option_timestamp = option_timestamp,
                            option_SACK_Permit = None,
                            option_max_segment_size = None,
                            option_window_scale_factor=None,
                            
                        ),
                  DataStack(payload),
        )
        ts.last_ack_send = time.time()
