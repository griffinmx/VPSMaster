"""Small Linux UDP trace using the socket error queue; no raw socket/root needed."""
import ipaddress
import socket
import struct
import sys
import time
import select
from .geo import GeoLocator
from .console import clean


def trace(target, emit=print, hops=30, wait=1.0, lang='zh', geo=True, records=None):
    if not 1<=hops<=64 or not 0<wait<=10: raise ValueError('Invalid trace limits')
    address=ipaddress.ip_address(target)
    locator=GeoLocator(lang,enabled=geo)
    zh=lang=='zh';v6=address.version==6
    if sys.platform != 'linux':
        emit('当前平台无法进行原生追踪' if zh else 'Native trace unavailable on this platform',flush=True)
        return 1
    family=socket.AF_INET6 if v6 else socket.AF_INET
    protocol=socket.IPPROTO_IPV6 if v6 else socket.IPPROTO_IP
    recverr=25 if v6 else 11
    try:
        with socket.socket(family,socket.SOCK_DGRAM) as sock:
            sock.setsockopt(protocol,recverr,1)  # Linux IPV6_RECVERR/IP_RECVERR
            sock.setblocking(False)
            for ttl in range(1,hops+1):
                sock.setsockopt(protocol,socket.IPV6_UNICAST_HOPS if v6 else socket.IP_TTL,ttl)
                start=time.monotonic()
                endpoint=(str(address),33434+ttl,0,0) if v6 else (str(address),33434+ttl)
                sock.sendto(b'ProxyDoctor',endpoint)
                found=False
                while time.monotonic()-start < wait:
                    try:
                        _, controls, _, destination=sock.recvmsg(512,512,socket.MSG_ERRQUEUE)
                    except BlockingIOError:
                        remaining=wait-(time.monotonic()-start)
                        if remaining>0: select.select([sock],[],[sock],remaining)
                        continue
                    if not destination or ipaddress.ip_address(destination[0]) != address or destination[1] != 33434+ttl:
                        continue  # Ignore late errors from previous TTL probes.
                    for level,kind,data in controls:
                        if level != protocol or kind != recverr or len(data)<(44 if v6 else 24):
                            continue
                        _,origin,icmp_type,icmp_code,_,_,_=struct.unpack('=IBBBBII',data[:16])
                        if origin != (3 if v6 else 2): continue
                        if icmp_type not in ((1,3) if v6 else (3,11)): continue
                        hop=socket.inet_ntop(family,data[24:40] if v6 else data[20:24])
                        elapsed=(time.monotonic()-start)*1000
                        location=clean(locator.lookup(hop))
                        emit(f'{ttl:2d}  {hop:<39} {elapsed:8.1f} ms  {location}',flush=True)
                        reached=(icmp_type==1 and icmp_code==4 if v6 else icmp_type==3 and icmp_code==3) and ipaddress.ip_address(hop)==address
                        if records is not None: records.append({'hop':ttl,'ip':hop,'latency_ms':round(elapsed,3),'location':location,
                                                                'icmp_type':icmp_type,'icmp_code':icmp_code,'state':'reached' if reached else 'reply'})
                        found=True
                        if reached: return 0
                        if icmp_type==(1 if v6 else 3):
                            emit(f'  ICMP 不可达（代码 {icmp_code}）' if zh else f'  ICMP unreachable (code {icmp_code})',flush=True)
                            return 1
                    if found: break
                if not found:
                    emit(f'{ttl:2d}  {"*":<39} {"---":>8}     ---',flush=True)
                    if records is not None: records.append({'hop':ttl,'ip':None,'latency_ms':None,'location':None,'state':'timeout'})
    except (OSError,AttributeError):
        emit('原生 UDP 追踪不可用或未收到允许的响应' if zh else 'Native UDP trace unavailable or blocked',flush=True)
    return 1
