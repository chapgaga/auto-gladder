import struct
import array

def unpack(fstr, data_str):
    return struct.unpack(fstr, data_str)[0]

def pack(fstr, data):
    return struct.pack(fstr, data)

def inc_with_mod(data, mod, v=1):
    return (data+v) & mod

if struct.pack("H",1) == "\x00\x01": # big endian
    def checksum(pkt):
        if len(pkt) % 2 == 1:
            pkt += "\0"
        s = sum(array.array("H", pkt))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        s = ~s
        return s & 0xffff
else:
    def checksum(pkt):
        if len(pkt) % 2 == 1:
            pkt += "\0"
        s = sum(array.array("H", pkt))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        s = ~s
        return (((s>>8)&0xff)|s<<8) & 0xffff

def test():
    s="45 00 00 b0 f5 df 40 00 40 06 c0 fa c0 a8 01 14 c0 a8 01 09" # IP
    s = "".join([chr(int(x,16)) for x in s.split()])
    assert checksum(s) == 0

    ss="ec f9 00 15 a9 67 f2 81 34 5c 94 4f 80 18 39 08 66 e4 00 00 01 01 08 0a 01 04 9e 78 94 f3 92 fd 69 6e 63 6f 6d 65" #  TCP
    s_fake = "c0 a8 01 09 c0 a8 01 14 00 06 00 26"                  # TCP fake header

#    ss="00 15 82 c3 63 b0 42 00 fb 15 5e e4 50 12 ff ff 00 00 02 04 08 0a 01"
    ss='00 15 83 65 5e 71 42 d8 5d 22 bb aa 50 12 ff ff 00 00 02 04 08 0a 01'
    s_fake = "c0 a8 00 14 c0 a8 00 28 00 06 00 17"
    s = s_fake + ' ' + ss
    s = "".join([chr(int(x,16)) for x in s.split()])
    assert checksum(s) == 0

if __name__ == "__main__":
    test()
    