import time

def get_time(): return time.time()

class Event:
    pool={}
    def __init__(self, event_tag, timeout, operation_cb, *operation_args, **operation_kwargs):
        self.tag = event_tag
        self.cb = operation_cb
        self.args = operation_args
        self.kwargs = operation_kwargs
        self.timeout = timeout + get_time()

        pool[self.tag] = self

    @staticmethod
    def find_event(event_tag):
        return Event.pool[event_tag]

    @staticmethod
    def check_timeout():
        now = get_time()
        pool = Event.pool
        timeout_lst = [x for x in pool if pool[x].timedout > now]
        for k in timeout_lst:
            obj = pool[k]
            ret = obj.cb(*obj.args, **obj.kwargs)
            if ret is None:     # remove
                del pool[k]
            else:               # reinit timeout
                obj.timeout = get_time() + ret

    def done(self):
        del Event.pool[self.tag]
