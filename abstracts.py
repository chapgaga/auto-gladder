import types
from copy import copy

class SlicedString:
    def __init__(self, parent, slice):
        self.slice = slice
        self.parent = parent

    def as_str(self):
        return self.parent.data[self.slice]

    def __repr__(self): return repr(self.as_str())
    def __str__(self): return self.as_str()

class NetworkPkgData:
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

class AbstractStack:
    def __init__(self, parent=None, data=None):
        self.parent = parent
        if parent is None:      # this is the root
            self.root = self
        else:
            self.root = self.parent.root

        if data: 
            self.parse(data)
            self.payload = data[self.headlen:]

        self.do()

    def do(self):
        "protocol actions"
        pass

    def fork(self, **kwargs):
        stack = copy(self)
        for k, v in kwargs.items():
            if not hasattr(stack, k): print "Warning, unknown property:", k
            if v: setattr(stack, k, v)
            if v is None: delattr(stack, k)
            
        return stack        

    def pack(self, payload, peek=None): raise NotImplemented
    def parse(self): raise NotImplemented

    def dump(self):
        print "====== DUMP:%s =======" % repr(self.__class__)
        for k in dir(self):
            if hasattr(self.__class__, k): continue
            print k,':', repr(getattr(self, k))
              
        print '--------------'

    def send(self, *stacks):
        vif = self.root.vif     # get tun interface from root
        
        payload=""
        stacks = stacks[::-1]
        for peek_stack, stack in zip(stacks[1:]+(None,), stacks): # pack stack from top to bottom
            payload = stack.pack(payload, peek_stack)
#            stack.dump()

        vif.write(payload)

class DataStack(AbstractStack):
    def __init__(self, payload): self.payload = payload
    def pack(self, payload, peek=None): return self.payload
        
def test():
    pkg = NetworkPkgData("abcdef")
    print pkg[1:5].as_str()     # bcdef
    print pkg.as_str()          # abcdef
    


if __name__ == "__main__":
    test()
