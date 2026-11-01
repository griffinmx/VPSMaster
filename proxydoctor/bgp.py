"""Bounded RIPE RIS observations, not the VPS's selected routing table."""
import ipaddress
from urllib.parse import urlencode
from .net import request_json
from .reports import utc_now

SOURCE='https://stat.ripe.net'
ASN_HINTS={4134:'China Telecom 163',4809:'China Telecom CN2',4837:'China Unicom',
           9929:'China Unicom 9929',9808:'China Mobile',58453:'CMI',58807:'CMIN2'}


def as_number(value):
    if isinstance(value,bool):return None
    try:
        number=int(value)
        return number if str(number)==str(value) and 1<=number<=4294967295 else None
    except (TypeError,ValueError):return None


def query(endpoint,resource,**params):
    url=SOURCE+'/data/'+endpoint+'/data.json?'+urlencode({'resource':resource,**params})
    payload,state=request_json(url,max_bytes=524288)
    if state!='ok':return None,state
    if payload.get('status')!='ok' or not isinstance(payload.get('data'),dict):
        return None,'invalid_response'
    return payload['data'],'ok'


def collect(address, destination=None, on_result=None):
    ip=ipaddress.ip_address(address)
    if not ip.is_global:raise ValueError('BGP lookup requires a public IP')
    report=destination if destination is not None else {}
    report.update(target=str(ip),checked_at=utc_now(),source=SOURCE,status='unknown',
                  prefix=None,origin_asns=[],neighbours=[],paths=[],sources={},
                  limitations=['RIS collector observations are not the local selected route.',
                               'ASN adjacency does not prove a commercial upstream relationship.',
                               'Sampled AS paths do not prove packet paths or CN2 GIA service.'])
    def save():
        if on_result:on_result()
    data,state=query('network-info',str(ip))
    report['sources']['network-info']=state
    if state!='ok':save();return report
    try:
        prefix=ipaddress.ip_network(data['prefix'])
        origins=data['asns']
        if ip not in prefix or not isinstance(origins,list) or not origins or any(as_number(n) is None for n in origins):
            raise ValueError()
        report.update(prefix=str(prefix),origin_asns=[int(n) for n in origins],status='partial')
    except (ValueError,TypeError,KeyError):
        report['sources']['network-info']='invalid_response';save();return report
    save()
    neighbours,state=query('asn-neighbours','AS'+str(report['origin_asns'][0]))
    report['sources']['asn-neighbours']=state
    if state=='ok':
        rows=neighbours.get('neighbours',[])
        if isinstance(rows,list):
            report['neighbours']=[{'asn':as_number(row.get('asn')),'type':row.get('type'),
                                    'power':row.get('power')} for row in rows[:256]
                                   if isinstance(row,dict) and as_number(row.get('asn'))]
        report['neighbours_query_time']=neighbours.get('query_starttime')
    save()
    state_data,state=query('bgp-state',report['prefix'],rrcs='0')
    report['sources']['bgp-state']=state
    if state=='ok':
        rows=state_data.get('bgp_state',[])
        seen=set()
        if isinstance(rows,list):
            for row in rows[:512]:
                if not isinstance(row,dict) or not isinstance(row.get('path'),list):continue
                path=row['path']
                try:prefix=ipaddress.ip_network(row.get('target_prefix'))
                except (ValueError,TypeError):continue
                if ip not in prefix or not path or len(path)>128 or any(as_number(n) is None for n in path):continue
                path=tuple(map(int,path))
                if path in seen:continue
                seen.add(path)
                report['paths'].append({'as_path':list(path),'collector_peer':row.get('source_id'),
                                        'prefix':str(prefix),'network_hints':[ASN_HINTS[n] for n in dict.fromkeys(path) if n in ASN_HINTS]})
                if len(report['paths'])>=20:break
        report['data_time']=state_data.get('timestamp',state_data.get('query_time'))
    report['status']='success' if report['paths'] and all(v=='ok' for v in report['sources'].values()) else 'partial'
    save()
    return report


def render(report,out):
    tr=out.text
    out.row('BGP',report.get('status','unknown'),'ok' if report.get('status')=='success' else 'unknown')
    out.row(tr('公告前缀','Announced prefix'),report.get('prefix') or tr('未知','Unknown'),'unknown')
    out.row(tr('起源 ASN','Origin ASNs'),', '.join('AS'+str(n) for n in report.get('origin_asns',[])) or '---')
    out.row(tr('观测邻居','Observed neighbours'),len(report.get('neighbours',[])),'unknown')
    for row in report.get('paths',[]):
        out.row('RIS AS_PATH',' → '.join(map(str,row['as_path'])),'unknown')
        if row['network_hints']:out.row(tr('ASN 标签','ASN hints'),' / '.join(row['network_hints']),'unknown')
    for name,state in report.get('sources',{}).items():out.row(name,state,'ok' if state=='ok' else 'unknown')
    out.row(tr('范围','Scope'),tr('RIS 采集器视角；不等于本机实际选路或商业上游','RIS collector view; local path and commercial upstream unconfirmed'),'unknown')
