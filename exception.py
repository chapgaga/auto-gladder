
class ARPLookupException(Exception): 
    def __init__(self, ip):
        self.ip = ip