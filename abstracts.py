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
        self.parent = None
        if data: self.parse(data)

    def do(self):
        "protocol actions"
        pass

    def fork(self, **kwargs):
        stack = copy(self)
        for k, v in kwargs.items():
            if not v in stack: print "Warning, unknown property:", k
            if v: setattr(stack, k, v)
            
        return stack        

def test():
    pkg = NetworkPkgData("abcdef")
    print pkg[1:5].as_str()     # bcdef
    print pkg.as_str()          # abcdef
    


if __name__ == "__main__":
    test()
