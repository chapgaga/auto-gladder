from abstracts import AbstractStack, DataStack
import struct
from threadpool import *
from Queue import Queue, Empty
from asio import ASIO
from proxy import Proxy
from utils import unpack, pack, checksum, inc_with_mod, distance_with_mod
import os
from collections import deque
import time
from environment import Environment


def timestamp():
    "return current time stamp, 32bit, round-trip, ticked by 1ms"
    return int(time.time()*1000) & 0xffffffff

QUEUE_LENGTH = 128
DATA_QUEUE_LENGTH = 1024
class TCPStatus:
    def __init__(self, tcp_stack):
        # stack instance
        self.tcp_stack = tcp_stack

        pair = tcp_stack.get_connection_pair()
        # init destination and source
        self.src_ip , self.src_port = pair[0], pair[1]
        self.dst_ip , self.dst_port = pair[2], pair[3]

        # init proxy socket
        self.sock = Proxy.get_connection(pair[2:])

        # init data IO queue
        self.queue = Queue(DATA_QUEUE_LENGTH)

        # init outcome_seq
        self.acked_outcome_seq = self.outcome_seq = abs(id(self)) & 0xffffffff # generate outcome seq according to id(self)
        self.income_seq  = inc_with_mod(tcp_stack.seq_num, 0xffffffff) # remote sequence, add 1 to indicate we've received
        self.last_ack_send = 0
        self.last_ack_count = 0

        self.running = 1
        self.ahead = -1       # ahead mode disabled
        self.resend_buf = deque()
        self.fin = False

        # debug only
        self.outcome_seq_base = self.outcome_seq
        self.income_seq_base = self.income_seq

    def hand_shake(self):
        tcp_stack = self.tcp_stack
        while self.running:             # send SYN|ACK repeatly until we get the final ACK
            try:
                option_timestamp = (timestamp(), tcp_stack.option_timestamp[0])
            except:
                option_timestamp = None

            tcp_stack.send(
                tcp_stack.parent.fork(src_ip = self.dst_ip, dst_ip = self.src_ip), # IP Layer, reverse src/dst ip pair
                tcp_stack.fork(src_port = self.dst_port, dst_port = self.src_port, # TCP Layer, reverse src/dst port pair
                          flags = SYN | ACK, # handshake, SYN|ACK
                          ack_num = self.income_seq, 
                          seq_num = self.outcome_seq, # synced package, seq 0
                          window = 14480,
                          option_window_scale_factor=None,
                          option_timestamp= option_timestamp,
                      ),
            )
            tag, pkg_fd, pkg = self.queue.get(timeout=0.1)

            if tag == 'from_internal': # we received response
                self.acked_outcome_seq = self.outcome_seq = pkg.ack_num
                try:
                    self.last_timestamp = pkg.option_timestamp[0]
                except:
                    self.last_timestamp = 0
                break

        self.first=True         # special case for first received package
        print "connection established"

    def send(self, data):
        """
        send payload
        if ahead mode is on, check if we need to sendit or wait for ack or resend previous data
        """

        print "send:", len(data), self.ahead

        seq = self.outcome_seq
        self.outcome_seq += len(data)

        self.resend_buf.append((seq, data))
        if self.ahead<0:        # ahead mode disabled
            self.send_response(seq, data)
            self.ahead=3        # enter ahead mode
        elif self.ahead==0:     # reached ahead countdown, wait for ack
            # do nothing, leave the works for the resend routine
            pass
        else:
            self.send_response(seq, data)
            self.ahead-=1

    def receive(self, pkg):
        """
        receive package, update self param
        pkg: tcp_stack
        """
        try:
            self.last_timestamp = pkg.option_timestamp[0]
        except:
            self.last_timestamp = 0

        # check duplicate
        #if pkg.ack_num == self.outcome_seq and self.outcome_seq != self.first_outcome_seq
        diff = distance_with_mod(pkg.ack_num, self.outcome_seq, 0xffffffff)
        print "recv, diff:", diff, repr(pkg.payload[:40])
        if diff >0 or self.first:
            self.first = False
            if pkg.payload: 
                self.sock.send(pkg.payload) # forward to relay node
                self.income_seq = inc_with_mod(self.income_seq, 0xffffffff, len(pkg.payload))

        if pkg.flags & FIN:       # FIN?
#            print "pkg flag:", pkg.flags, pkg.flags & FIN
            if not self.fin:        # already in fin
                self.close()
            else:
                self.send_response(self.outcome_seq, "")
                print "put done"
                self.queue.put(('done', 0, ''))
        self.acked_outcome_seq = pkg.ack_num
        if self.ahead>=0: self.ahead=3
        self.clean_resend_buf()

    def clean_resend_buf(self):
        while self.resend_buf:
            peek=self.resend_buf[0]
            d = distance_with_mod(peek[0], self.acked_outcome_seq, 0xffffffff)
#            print "clean, d:", d
            if d<0:
                self.resend_buf.popleft()
            else: break
    

    def send_response(self, seq, payload='', fin=0):
        """
        send tcp response(with ack)
        """
        if self.last_timestamp: option_timestamp = (timestamp(), self.last_timestamp)
        else: option_timestamp = None

        print 'FIN:',self.fin, "SEQ:", distance_with_mod(seq, self.outcome_seq_base, 0xffffffff), \
            "ACK:", distance_with_mod(self.income_seq, self.income_seq_base, 0xffffffff), \
            "payload:", len(payload), repr(payload[:40])

        ts = self.tcp_stack
        ts.send(ts.parent.fork(src_ip = self.dst_ip, dst_ip = self.src_ip), # IP Layer, reverse src and dst, because this is a ACK routine
                ts.fork(src_port = self.dst_port, dst_port = self.src_port, # TCP Layer
                        flags = ACK | PUSH | fin,
                        window = 14480,
                        ack_num = self.income_seq,
                        seq_num = seq,
                        option_timestamp = option_timestamp,
                        option_SACK_Permit = None,
                        option_max_segment_size = None,
                        option_window_scale_factor=None,
                        
                    ),
                DataStack(payload),
            )
        self.last_ack_send = time.time()
        self.last_ack_count = 0

    def resend_routine(self):
        """
        resend previous package
        """
        for seq, data in self.resend_buf:
            if seq == -1:       # we reached end
                self.fin = True
                self.send_response(self.outcome_seq, "", fin=FIN)
                self.queue.put(('check_buf', 0, 0))
                return
            print "check seq", distance_with_mod(seq, self.outcome_seq_base, 0xffffffff), \
                distance_with_mod(self.acked_outcome_seq, self.outcome_seq_base, 0xffffffff), \
                distance_with_mod(self.outcome_seq, self.outcome_seq_base, 0xffffffff), repr(data[:40])

            d = distance_with_mod(seq, self.acked_outcome_seq, 0xffffffff)
            print "d:", d
            if d>=0:
                self.send_response(seq, data)
                break
        else:                   # send ack?
            if self.ahead<=0:
                self.send_response(self.outcome_seq,"")
                self.ahead=3

        if self.resend_buf:
            self.queue.put(('check_buf', 0, 0))
        
    def close(self):
        self.resend_buf.append((-1, '')) 


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
                cp[pair].queue.put(('from_internal', None, self))
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
        ts.hand_shake()

        # Connection established

        ASIO.connect(ts.sock.fileno(), ts.queue, mtu=Environment.MTU_TCP, tag='from_external')
        
        # handshake done

        while True:
            try:
                tag, pkg_fd, pkg = ts.queue.get(timeout=0.1)
            except Empty:   # IO queue empty
                ts.resend_routine()
                continue

            print "   ###### tag:", tag
            if tag == 'from_external': # download data from relay node, forward to internal net
                ts.send(pkg)
            elif tag == 'from_internal': # outcoming data to relay node
                ts.receive(pkg)
            elif tag == 'check_buf':
                ts.resend_routine()
            elif tag == 'close':
                ts.close()
            elif tag == 'done':
                break

        print "tcp closed"

