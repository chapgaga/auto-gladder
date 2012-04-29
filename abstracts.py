"""
Some abstract classes
"""

import types
from copy import copy

from exception import ARPLookupException

class SlicedString:
    """
    A very simple version of shared slice string.
    """
    def __init__(self, parent, slice):
        self.slice = slice
        self.parent = parent

    def as_str(self):
        return self.parent.data[self.slice]

    def __repr__(self): return repr(self.as_str())
    def __str__(self): return self.as_str()

class NetworkPkgData:
    """
    Network package data impl with SlicedString to reduce memory usage
    """
    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        if isinstance(key, types.IntType):
            return self.data[key]
        elif isinstance(key, types.SliceType):
            return SlicedString(self, key)

    def as_str(self): return self.data

    def __repr__(self): return repr(self.as_str())
    def __str__(self): return self.as_str()

def register_stacks(identify, stack):
    setattr(AbstractStack, identify, stack)

class AbstractStack:
    """
    Abstract class for IPStack/TCPStack/UDPStack/ ...
    provide:
      - hierarchical stack layer
      - parse/action/fork/dump/send support
    """
    def __init__(self, parent=None, data=None):
        self.parent = parent
        if parent is None:      # this is the root
            self.root = self
        else:
            self.root = self.parent.root

        if data:                # parse the data automatically
            self.parse(data)
            self.payload = data[self.headlen:]
            self.do()

    def construct(self, *stacks):
        "construct stacks from this level"
        stacks[0].root = self
        for a,b in zip(stacks[:-1], stacks[1:]):
            b.parent = a
            b.root = self
        return stacks

    @classmethod
    def new(cls, **kwargs):
        ins = cls()
        ins._set_attribute(False, **kwargs)
        return ins


    def do(self):              
        """
        protocol actions
         - some post actions after parsed
        """
        pass

    def fork(self, **kwargs):
        """
        duplicate current stack
          - override properties by **kwargs
          - A kwargs like {key:None} will remove the property
        """
        stack = copy(self)
        stack._set_attribute(True, **kwargs)
        return stack

    def _set_attribute(self, verbose, **kwargs):
        for k, v in kwargs.items():
            if verbose and not hasattr(self, k): print "Warning, unknown property:", k
            if v: setattr(self, k, v)
            if v is None: delattr(self, k)
            
    def pack(self, payload, peek=None):
        """
        Pack the Stack into bytestream.
         - payload: previous stack bytestream
         - peek: refer to next stack structure for the purpose of cross layer protocols
        """
        raise NotImplemented
    def parse(self): raise NotImplemented

    def dump(self):
        """
        Dump the stack properties
        """
        print "====== DUMP:%s =======" % repr(self.__class__)
        for k in dir(self):
            if hasattr(self.__class__, k): continue
            print k,':', repr(getattr(self, k))
              
        print '--------------'

    def send(self, *stacks, **kwargs):
        pif = self.root.pif     # get tun interface from root
        
        payload=""
        stacks = stacks[::-1]

        if 'debug' in kwargs:
            debug = kwargs['debug']
        else:
            debug = None

        if debug: print "[Send Debug]"

        for peek_stack, stack in zip(stacks[1:]+(None,), stacks): # pack stack from top to bottom
            if debug: stack.dump()
#            print "previous payload:", repr(payload)
            payload = stack.pack(payload, peek_stack)
#            print "new payload:", repr(payload)

        if debug: print "[Send Debug] PAYLOAD:", repr(payload)

        if isinstance(stacks[-1], AbstractStack._macstack): # The last stack is mac stack, we can send it now
            pif.write(payload)
        else:                   # the last stack isn't mac, we need to create one
            assert isinstance(stacks[-1], AbstractStack._ipstack)
            def operate():
                ipstack = stacks[-1]
                payload2 = self._macstack.new_from_ip(ipstack).pack(payload, None)
                pif.write(payload2)
            try:
                operate()
            except ARPLookupException, e:
                AbstractStack._arptable.padding_operation(self.root, e.ip, operate)
                

class DataStack(AbstractStack):
    """
    An internal Stack class for raw bytestream.
    """
    def __init__(self, payload):
        AbstractStack.__init__(self)
        self.payload = payload

    def pack(self, payload, peek=None):
        return self.payload
        
def test():
    pkg = NetworkPkgData("abcdef")
    print pkg[1:5].as_str()     # bcdef
    print pkg.as_str()          # abcdef
    


if __name__ == "__main__":
    test()
