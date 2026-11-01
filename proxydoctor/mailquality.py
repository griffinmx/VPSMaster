"""Opt-in bounded PTR/forward consistency and outbound SMTP TCP probes.

No email, SMTP command or authentication is sent. DNSBL remains unqueried until
each provider's terms, error codes and resolver requirements are configured.
"""
import ipaddress
import json
import subprocess
import sys
from .reports import utc_now

PROGRAM = '''import ipaddress,json,socket,sys,time
options=json.loads(sys.stdin.readline())
if options['mode']=='ptr':
 try:
  host,aliases,addresses=socket.gethostbyaddr(options['ip'])
  forward=socket.getaddrinfo(host,None,type=socket.SOCK_STREAM)
  matches=any(ipaddress.ip_address(row[4][0])==ipaddress.ip_address(options['ip']) for row in forward)
  print(json.dumps({'status':'observed','hostname':host[:253],'forward_matches':matches}))
 except socket.herror:
  print(json.dumps({'status':'unknown','error_code':'PTR_NO_RECORD_OR_RESOLVER_ERROR'}))
 except OSError:
  print(json.dumps({'status':'unknown','error_code':'DNS_ERROR'}))
else:
 try:
  addresses=socket.getaddrinfo('gmail-smtp-in.l.google.com',25,type=socket.SOCK_STREAM)
  target=next(row for row in addresses if ipaddress.ip_address(row[4][0]).version==options['family'] and ipaddress.ip_address(row[4][0]).is_global)
  start=time.monotonic()
  with socket.create_connection((target[4][0],25),timeout=2):pass
  print(json.dumps({'status':'reachable','elapsed_ms':round((time.monotonic()-start)*1000,3),'address':target[4][0]}))
 except (OSError,StopIteration):
  print(json.dumps({'status':'unknown','error_code':'SMTP_TCP_UNCONFIRMED'}))
'''


def probe(mode,address):
    ip=ipaddress.ip_address(address)
    if not ip.is_global or mode not in ('ptr','smtp'):
        raise ValueError('Expected global IP and supported probe')
    try:
        process=subprocess.run([sys.executable,'-I','-B','-c',PROGRAM],
                               input=json.dumps({'mode':mode,'ip':str(ip),'family':ip.version}),
                               capture_output=True,text=True,encoding='utf-8',timeout=5,check=False)
        if process.returncode or len(process.stdout)>8192:
            return {'status':'unknown','error_code':'PROBE_ERROR'}
        result=json.loads(process.stdout)
        return result if isinstance(result,dict) else {'status':'unknown','error_code':'INVALID_RESPONSE'}
    except subprocess.TimeoutExpired:
        return {'status':'unknown','error_code':'PROBE_TIMEOUT'}
    except (OSError,ValueError):
        return {'status':'unknown','error_code':'PROBE_ERROR'}


def collect(address, query=probe):
    report={'checked_at':utc_now(),'scope':'selected_family_outbound_only','ptr':None,'smtp_tcp':None,
            'dnsbl':{'status':'skipped','reason':'provider_terms_and_resolver_configuration_required'},
            'limitations':['PTR consistency does not establish email deliverability or IP reputation.',
                           'SMTP TCP uses the default route; it does not bind the queried IP as source.',
                           'One outbound target cannot prove all port-25 paths or inbound mail availability.',
                           'No DNSBL result or clean-IP score is inferred from missing data.']}
    if not address:
        report.update(ptr={'status':'skipped','error_code':'IP_UNAVAILABLE'},smtp_tcp={'status':'skipped','error_code':'IP_UNAVAILABLE'})
        return report
    for mode,key in (('ptr','ptr'),('smtp','smtp_tcp')):
        try:report[key]=query(mode,address)
        except Exception:report[key]={'status':'unknown','error_code':'PROBE_ERROR'}
    return report


def render(report,out):
    tr=out.text
    ptr=report['ptr'];smtp=report['smtp_tcp']
    out.row('PTR',ptr.get('hostname') or ptr.get('error_code','Unknown'),'ok' if ptr['status']=='observed' else 'unknown')
    matches=ptr.get('forward_matches')
    out.row(tr('PTR 正向一致','PTR forward match'),tr('是','Yes') if matches is True else tr('否','No') if matches is False else tr('未知','Unknown'),
            'ok' if matches is True else 'unknown')
    out.row(tr('出站 TCP/25','Outbound TCP/25'),tr('单目标可连接','One target reachable') if smtp['status']=='reachable' else tr('未确认；不能认定全部被封','Unconfirmed; does not prove universal blocking'),
            'ok' if smtp['status']=='reachable' else 'unknown')
    out.row('DNSBL',tr('未查询：需核实来源条款及解析器条件','Not queried: provider terms/resolver setup required'),'unknown')
