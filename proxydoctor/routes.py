"""Small Linux UDP trace using the socket error queue; no raw socket/root needed."""
import ipaddress
import socket
import struct
import sys
import time
import select
import re
import shutil
from .geo import GeoLocator
from .console import clean


def parse_traceroute_hop(text, ttl, target):
    """Parse numeric Linux traceroute -n -q 1 output; retain explicit errors."""
    for line in text.splitlines():
        match = re.match(r'^\s*(\d+)\s+(.*)', line)
        if not match or int(match[1]) != ttl:
            continue
        rest=match[2]
        if rest.strip()=='*':
            return {'hop':ttl,'ip':None,'latency_ms':None,'state':'timeout','probes_sent':1,'responses':0}
        fields=rest.split()
        try:
            address=str(ipaddress.ip_address(fields[0]))
            rtt=float(fields[1])
            if not 0<=rtt<=60000 or fields[2]!='ms':continue
        except (ValueError,IndexError):continue
        unreachable=any(token.startswith('!') for token in fields[3:])
        return {'hop':ttl,'ip':address,'latency_ms':rtt,'probes_sent':1,'responses':1,
                'state':'unreachable' if unreachable else 'reached' if address==str(target) else 'reply'}
    return None


def trace_method(target, emit=print, *, method='udp', tcp_port=443, hops=30, wait=1.0,
                 lang='zh', geo=True, records=None, on_result=None, deadline=None):
    """Native UDP or fixed-system Linux traceroute ICMP/TCP, without elevation."""
    if method=='udp':
        return trace(target,emit,hops,wait,lang,geo,records,on_result,deadline)
    if method not in ('icmp','tcp') or not 1<=hops<=64 or not 1<=tcp_port<=65535 or not 0<wait<=10:
        raise ValueError('Invalid trace method or limits')
    address=ipaddress.ip_address(target)
    executable=shutil.which('traceroute',path='/usr/sbin:/usr/bin:/sbin:/bin') if sys.platform=='linux' else None
    if not executable:
        emit('TRACEROUTE_DEPENDENCY_MISSING · ICMP/TCP 需要系统 traceroute' if lang=='zh' else
             'TRACEROUTE_DEPENDENCY_MISSING · ICMP/TCP require system traceroute',flush=True)
        return 1
    from .worker import local_command
    deadline=deadline if deadline is not None else time.monotonic()+90
    locator=GeoLocator(lang,enabled=geo)
    for ttl in range(1,hops+1):
        remaining=deadline-time.monotonic()
        if remaining<=0:return 1
        argv=[executable,'-6' if address.version==6 else '-4','-n','-N','1','-q','1',
              '-f',str(ttl),'-m',str(ttl),'-w',str(wait),'-I' if method=='icmp' else '-T']
        if method=='tcp':argv+=['-p',str(tcp_port)]
        argv.append(str(address))
        try:code,text,error=local_command(argv,timeout=min(wait+2,remaining))
        except OSError:
            code,text,error=None,'','COMMAND_UNAVAILABLE'
        row=parse_traceroute_hop(text,ttl,address)
        if row is None:
            emit(error or 'TRACEROUTE_FAILED_OR_PERMISSION_DENIED',flush=True)
            return 1
        row.update(method=method,statistics_scope='one_probe_this_ttl_not_forwarding_loss')
        row['location']=clean(locator.lookup(row['ip'])) if row['ip'] else None
        row['response_loss_percent']=0.0 if row['responses'] else 100.0
        if records is not None:records.append(row)
        emit(f"{ttl:2d}  {row['ip'] or '*':<39} {str(row['latency_ms']) if row['latency_ms'] is not None else '---':>8} ms  {row['location'] or '---'}",flush=True)
        if on_result:on_result()
        if row['state']=='reached':return 0
        if code or row['state']=='unreachable':return 1
    return 1


def trace(target, emit=print, hops=30, wait=1.0, lang='zh', geo=True, records=None, on_result=None, deadline=None):
    if not 1<=hops<=64 or not 0<wait<=10: raise ValueError('Invalid trace limits')
    address=ipaddress.ip_address(target)
    deadline=deadline if deadline is not None else time.monotonic()+90
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
                if time.monotonic()>=deadline:
                    emit('Route observation time budget exhausted (90s)',flush=True)
                    return 1
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
                        emit(f'{ttl:2d}  {hop:<39} {elapsed:8.1f} ms  {location}  [reply 1/1; timeout 0/1]',flush=True)
                        reached=(icmp_type==1 and icmp_code==4 if v6 else icmp_type==3 and icmp_code==3) and ipaddress.ip_address(hop)==address
                        if records is not None: records.append({'hop':ttl,'ip':hop,'latency_ms':round(elapsed,3),'location':location,
                                                                'probes_sent':1,'responses':1,'response_loss_percent':0.0,'statistics_scope':'one_probe_this_ttl_not_forwarding_loss',
                                                                'icmp_type':icmp_type,'icmp_code':icmp_code,'state':'reached' if reached else 'reply'})
                        found=True
                        if on_result is not None: on_result()
                        if reached: return 0
                        if icmp_type==(1 if v6 else 3):
                            emit(f'  ICMP 不可达（代码 {icmp_code}）' if zh else f'  ICMP unreachable (code {icmp_code})',flush=True)
                            return 1
                    if found: break
                if not found:
                    emit(f'{ttl:2d}  {"*":<39} {"---":>8}     ---  [reply 0/1; timeout 1/1]',flush=True)
                    if records is not None: records.append({'hop':ttl,'ip':None,'latency_ms':None,'location':None,'state':'timeout',
                                                           'probes_sent':1,'responses':0,'response_loss_percent':100.0,'statistics_scope':'one_probe_this_ttl_not_forwarding_loss'})
                    if on_result is not None: on_result()
    except (OSError,AttributeError):
        emit('原生 UDP 追踪不可用或未收到允许的响应' if zh else 'Native UDP trace unavailable or blocked',flush=True)
    return 1


def summarize_hops(records):
    """Statistics over actually sent TTL probes, never forwarding-loss claims."""
    import statistics
    grouped={}
    for row in records:
        ttl=row['hop']
        item=grouped.setdefault(ttl,{'hop':ttl,'probes_sent':0,'responses':0,'ips':set(),'rtts':[]})
        item['probes_sent']+=row.get('probes_sent',1)
        item['responses']+=row.get('responses',1 if row.get('ip') else 0)
        if row.get('ip'):item['ips'].add(row['ip'])
        if row.get('latency_ms') is not None:item['rtts'].append(row['latency_ms'])
    result=[]
    for ttl,item in sorted(grouped.items()):
        sent=item['probes_sent'];received=item['responses']
        result.append({'hop':ttl,'probes_sent':sent,'responses':received,'timeouts':sent-received,
                       'response_loss_percent':round(100*(sent-received)/sent,2) if sent else None,
                       'median_rtt_ms':statistics.median(item['rtts']) if item['rtts'] else None,
                       'ips':sorted(item['ips']),
                       'scope':'router_response_loss_only_not_end_to_end_forwarding_loss'})
    return result
