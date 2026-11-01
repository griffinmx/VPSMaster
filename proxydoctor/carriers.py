"""Fixed public test endpoints; provider labels are claims until corroborated.

Endpoint references: NextTrace and CleanIP sh.cd (see THIRD_PARTY_NOTICES.md).
No remote scripts or automatic registry downloads are executed.
"""
from dataclasses import dataclass,asdict
import ipaddress
import socket
import time
from .reports import utc_now


@dataclass(frozen=True)
class CarrierNode:
    identifier:str
    carrier:str
    city:str
    host:str
    port:int=8080
    mainland:bool=True


NODES=(CarrierNode('ct-sh','telecom','Shanghai','speedtest1.online.sh.cn'),
       CarrierNode('ct-nj','telecom','Nanjing','5gnanjing.speedtest.jsinfo.net'),
       CarrierNode('ct-cd','telecom','Chengdu','speedtest1.sc.189.cn'),
       CarrierNode('cu-sh','unicom','Shanghai','mobile.shunicomtest.com'),
       CarrierNode('cu-bj','unicom','Beijing','beijing.unicomtest.com'),
       CarrierNode('cu-tj','unicom','Tianjin','speedtest3.online.tj.cn'),
       CarrierNode('cm-fz','mobile','Fuzhou','csfw.fj.chinamobile.com'),
       CarrierNode('cm-hz','mobile','Hangzhou','speedtest.139play.com'),
       CarrierNode('cm-bj','mobile','Beijing','speedtest.bmcc.com.cn'),
       CarrierNode('cm-hk','mobile','Hong Kong','speedtestbb.hk.chinamobile.com',mainland=False))


def resolve_public(host,family=4):
    """Only called inside a bounded network worker."""
    af=socket.AF_INET6 if family==6 else socket.AF_INET
    values={row[4][0] for row in socket.getaddrinfo(host,None,af,type=socket.SOCK_STREAM)}
    if not values or any(not ipaddress.ip_address(value).is_global for value in values):
        raise ValueError('Non-public or missing endpoint')
    return sorted(values)


def probe_node(identifier):
    from .worker import enabled,invoke
    if identifier not in {row.identifier for row in NODES}:raise ValueError('Unknown node')
    if enabled():
        result=invoke('carrier_probe',{'identifier':identifier},timeout=9)
        return result if isinstance(result,dict) else {'identifier':identifier,'status':'unknown','error_code':'NODE_TIMEOUT_OR_ERROR','checked_at':utc_now()}
    node=next(row for row in NODES if row.identifier==identifier)
    row={**asdict(node),'checked_at':utc_now(),'status':'unknown','scope':'small_protocol_probe_not_bandwidth',
         'provider_identity':'catalogue_claim','transport':'plaintext_tcp_no_credentials'}
    try:
        addresses=resolve_public(node.host)
        row['addresses']=addresses
        started=time.monotonic()
        with socket.create_connection((addresses[0],node.port),timeout=2) as sock:
            row['tcp_ms']=round((time.monotonic()-started)*1000,3)
            sock.settimeout(2);sock.sendall(b'HI\n')
            body=bytearray()
            while b'\n' not in body and len(body)<256:
                part=sock.recv(1)
                if not part:break
                body.extend(part)
            if not body.startswith(b'HELLO '):
                row['error_code']='UNRECOGNIZED_TEST_PROTOCOL';return row
            sock.sendall(b'DOWNLOAD 16384\n')
            total=0
            deadline=time.monotonic()+3
            while total<16384:
                if time.monotonic()>=deadline:raise TimeoutError()
                block=sock.recv(min(4096,16384-total))
                if not block:break
                total+=len(block)
            row['sample_bytes']=total
            row['status']='sample_available' if total==16384 else 'unknown'
            if total!=16384:row['error_code']='SHORT_TEST_SAMPLE'
    except socket.gaierror:row['error_code']='DNS_ERROR'
    except (OSError,ValueError):row['error_code']='CONNECTION_OR_PROTOCOL_ERROR'
    return row


def collect_nodes(destination=None,on_result=None,out=None):
    from concurrent.futures import ThreadPoolExecutor,as_completed
    report=destination if destination is not None else {}
    report.update(checked_at=utc_now(),nodes={},coverage={},status='unknown',
                  scope='current_vantage_to_fixed_public_test_nodes_not_all_china',
                  bandwidth_measured=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(probe_node,node.identifier):node for node in NODES}
        for future in as_completed(futures):
            node=futures[future]
            try:row=future.result()
            except Exception:row={'identifier':node.identifier,'status':'unknown','error_code':'NODE_PROBE_ERROR'}
            report['nodes'][node.identifier]={**asdict(node),**row}
            if on_result:on_result()
            if out:
                label=f'{node.carrier} / {node.city}' + (' [HK]' if not node.mainland else '')
                out.row(label,row['status']+' · '+str(row.get('error_code',str(row.get('sample_bytes',0))+' bytes')),
                        'ok' if row['status']=='sample_available' else 'unknown')
    for carrier in ('telecom','unicom','mobile'):
        report['coverage'][carrier]=any(row['carrier']==carrier and row['mainland'] and row['status']=='sample_available'
                                       for row in report['nodes'].values())
    report['status']='success' if all(report['coverage'].values()) else 'partial'
    if on_result:on_result()
    return report


def return_routes(*,method='udp',family=4,hops=30,geo=False,tcp_port=443,destination=None,on_result=None,out=None):
    """Beijing/Shanghai/Guangzhou × three carriers, from this host only."""
    from .worker import invoke
    from .routes import trace_method,summarize_hops
    if method not in ('udp','icmp','tcp') or family not in (4,6) or not 1<=hops<=64:
        raise ValueError('Invalid return-route options')
    report=destination if destination is not None else {}
    report.update(direction='this_host_to_china_targets',checked_at=utc_now(),status='partial',routes={},
                  scope='three_cities_three_carriers_not_all_provinces_or_reverse_direction',
                  target_reference='https://github.com/nxtrace/NTrace-core/blob/main/fast_trace/basic.go')
    for city in ('pek','sha','can'):
        for carrier,asn in (('telecom',4134),('unicom',4837),('mobile',9808)):
            key=f'{city}-{carrier}'
            host=f'ipv{family}.{city}-{asn}.endpoint.nxtrace.org'
            row={'host':host,'carrier_claim':carrier,'expected_asn':asn,'method':method,'hops':[],'state':'unknown'}
            report['routes'][key]=row
            if out:out.line(f'{city} / {carrier} / {method.upper()}','title')
            addresses=invoke('resolve_public',{'host':host,'family':family},timeout=5)
            if not isinstance(addresses,list) or not addresses:
                row['error_code']='TARGET_DNS_UNCONFIRMED'
            else:
                row['target']=addresses[0]
                def progress():
                    if on_result:on_result()
                def emit(line,**kwargs):
                    if out:out.line(line,'unknown')
                code=trace_method(row['target'],emit,method=method,tcp_port=tcp_port,hops=hops,lang=out.lang if out else 'en',
                                  geo=geo,records=row['hops'],on_result=progress,deadline=time.monotonic()+30)
                row['state']='reached' if code==0 else 'incomplete'
                row['statistics']=summarize_hops(row['hops'])
            if on_result:on_result()
    report['status']='success' if all(row['state']=='reached' for row in report['routes'].values()) else 'partial'
    return report
