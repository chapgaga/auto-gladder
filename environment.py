import os

class _env: pass

Environment = _env()
Environment.default_if = 'eth0' # note: will be overrided by auto detection
Environment.virtual_if_mac = "\x74\x34\x76\x0a\x01\x01"
Environment.virtual_if_ip  = (192,168,1,200)

def bring_if_up(vif_name):
    script=['ifconfig %(vif_name)s %(vif_ip)s',
#            'route add -net %(vif_network)s netmask %(vif_netmask)s %(vif_name)s'
    ]

    ip, mask = get_local_ip_and_mask()
    vip = '.'.join(ip.split('.')[:-1]+['200']) # assign a new ip of x.x.x.200
    
    vif_network = '.'.join([str(int(iter_ip) & int(iter_mask)) for iter_ip, iter_mask in zip(vip.split('.'),
                                                                                             mask.split('.'))
                        ])      # get the local network

    values={'vif_name':vif_name,
            'vif_ip': vip,      
            'vif_network': vif_network, 
            'vif_netmask':mask,
    }

    for cmd in script:
        os.system(cmd % values)

def get_local_ip_and_mask():
    if hasattr(Environment, "local_ip"):
        return (Environment.local_ip, Environment.local_mask)

    with open("/proc/net/route") as f:
        interfaces = [x for x in f.readlines()[1:] if x]

    if interfaces:
        for i in interfaces:
            val=[x for x in i.split("\t") if x]

            if not val:
                raise Exception("Error, no network configuration!!!")

            if val[7]== "00000000": # has default gw
                interface=val[0]
                break
        else:
            interface=interfaces[-1].split("\t")[0] # don't have default gw, choose the last interface in route table
    else:                                       # not route table configuration!!!
        print "Warning, not route configuration!!!, broken network!!"
        return ("127.0.0.1", "255.255.255.0")

    with os.popen("/sbin/ifconfig %s" % interface) as f:
        data = f.read()

    Environment.local_ip=data.split("\n")[1].split(":")[1].split(" ")[0]
    Environment.local_mask=data.split("\n")[1].split(":")[-1]
    Environment.local_interface=interface

    return (Environment.local_ip, Environment.local_mask)

def get_mac_by_if(interface):
    with os.popen("/sbin/ifconfig %s" % interface) as f:
        data = f.read()

    mac = data.split('\n')[0].split()[-1] 
    return mac

def init():
    get_local_ip_and_mask()
    Environment.default_if = Environment.local_interface


init()