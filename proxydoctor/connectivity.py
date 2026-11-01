"""Family-specific bounded DNS/TCP/TLS observations, without HTTP content."""
import errno
import ipaddress
import json
import socket
import ssl
import subprocess
import sys
import time

from .reports import utc_now

TARGETS = (
    ('Cloudflare','one.one.one.one','1.1.1.1'),
    ('Cloudflare','one.one.one.one','2606:4700:4700::1111'),
    ('Google DNS','dns.google','8.8.8.8'),
    ('Google DNS','dns.google','2001:4860:4860::8888'),
)
RESOLVER = '''import json,socket,sys
family=int(sys.argv[1])
try:
    answers=socket.getaddrinfo('example.com',443,family=family,type=socket.SOCK_STREAM)
    print(json.dumps({'addresses':sorted(set(item[4][0] for item in answers))}))
except socket.gaierror as error:
    print(json.dumps({'error':error.errno}))
'''


def dns_probe(version, timeout=2):
    if version not in (4,6) or not 0 < timeout <= 5:
        raise ValueError('Invalid DNS probe limits')
    family = socket.AF_INET if version == 4 else socket.AF_INET6
    row = {'family': version, 'target': 'example.com', 'method': 'system_getaddrinfo',
           'observed_at': utc_now(), 'status': 'unknown', 'error_code': None}
    start = time.monotonic()
    try:
        process = subprocess.run([sys.executable,'-I','-B','-c',RESOLVER,str(int(family))],
                                 capture_output=True, text=True, timeout=timeout, check=False)
        if process.returncode or len(process.stdout) > 16384:
            row['error_code'] = 'RESOLVER_PROCESS_ERROR'
        else:
            payload = json.loads(process.stdout)
            code = payload.get('error')
            if code is not None:
                row['error_code'] = ('DNS_TEMPORARY_ERROR' if code == socket.EAI_AGAIN else
                                     'DNS_NO_ADDRESS' if code == socket.EAI_NONAME else 'DNS_RESOLUTION_ERROR')
            else:
                addresses = payload.get('addresses')
                if not isinstance(addresses,list) or not addresses or any(ipaddress.ip_address(value).version != version for value in addresses):
                    row['error_code'] = 'DNS_INVALID_RESPONSE'
                else:
                    row.update(status='success',addresses=addresses)
    except subprocess.TimeoutExpired:
        row['error_code'] = 'DNS_TIMEOUT'
    except (OSError, ValueError, TypeError, AttributeError):
        row['error_code'] = 'DNS_PROBE_ERROR'
    row['elapsed_ms'] = round((time.monotonic()-start)*1000,3)
    row['timing_scope'] = 'resolver_process_including_startup_and_cache'
    return row


def transport_probe(label, hostname, address, timeout=4):
    ip = ipaddress.ip_address(address)
    if not 0 < timeout <= 10:
        raise ValueError('Invalid transport timeout')
    row = {'target': label, 'hostname': hostname, 'address': address, 'family': ip.version,
           'port': 443, 'observed_at': utc_now(), 'method': 'numeric_tcp_then_verified_tls',
           'tcp': {'status':'unknown'}, 'tls': {'status':'skipped','error_code':'TCP_NOT_CONNECTED'}}
    started = time.monotonic()
    deadline = started + timeout
    stage = 'tcp'
    try:
        # Numeric addresses only: DNS cannot contaminate this TCP observation.
        with socket.create_connection((address,443),timeout=timeout) as raw:
            row['tcp'] = {'status':'success','elapsed_ms':round((time.monotonic()-started)*1000,3)}
            stage = 'tls'
            context = ssl.create_default_context()
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            raw.settimeout(remaining)
            tls_start = time.monotonic()
            with context.wrap_socket(raw,server_hostname=hostname) as secure:
                row['tls'] = {'status':'success','elapsed_ms':round((time.monotonic()-tls_start)*1000,3),
                              'version': secure.version(), 'certificate_verified': True}
    except ssl.SSLCertVerificationError:
        row['tls'] = {'status':'unknown','error_code':'TLS_CERTIFICATE_ERROR'}
    except (TimeoutError, socket.timeout):
        row[stage] = {'status':'unknown','error_code':stage.upper()+'_TIMEOUT'}
    except ssl.SSLError:
        row['tls'] = {'status':'unknown','error_code':'TLS_HANDSHAKE_ERROR'}
    except OSError as error:
        reason = {errno.ENETUNREACH:'NETWORK_UNREACHABLE',errno.EHOSTUNREACH:'HOST_UNREACHABLE',
                  errno.ECONNREFUSED:'CONNECTION_REFUSED',errno.EAFNOSUPPORT:'FAMILY_UNSUPPORTED'}.get(error.errno,'SOCKET_ERROR')
        row[stage] = {'status':'unknown','error_code':reason}
    row['elapsed_ms'] = round((time.monotonic()-started)*1000,3)
    return row


def collect(report=None, on_result=None, *, rounds=2, dns=dns_probe, transport=transport_probe):
    if not 1 <= rounds <= 3:
        raise ValueError('DNS rounds must be 1..3')
    report = {} if report is None else report
    report.update(schema_version=1, observed_at=utc_now(), dns=[], transports=[], dns_summary={},
                  limitations=['Only outbound paths to the named targets were checked.',
                               'DNS timings include process startup and system resolver caching.',
                               'No UDP, PMTU, inbound reachability or media playback was tested.'])
    def completed():
        if on_result is not None:
            on_result()
    for version in (4,6):
        rows = []
        for _ in range(rounds):
            try:
                row = dns(version)
            except Exception:
                row = {'family':version,'status':'unknown','error_code':'DNS_PROBE_ERROR','observed_at':utc_now()}
            rows.append(row)
            report['dns'].append(row)
            completed()
        count = sum(row['status'] == 'success' for row in rows)
        report['dns_summary'][str(version)] = {'attempted':rounds,'succeeded':count,
                                              'success_ratio':count/rounds}
    for label, hostname, address in TARGETS:
        try:
            row = transport(label,hostname,address)
        except Exception:
            row = {'target':label,'family':ipaddress.ip_address(address).version,
                   'tcp':{'status':'unknown','error_code':'PROBE_ERROR'},'tls':{'status':'skipped'}}
        report['transports'].append(row)
        completed()
    report['diagnostics'] = []
    for version in (4,6):
        transports = [row for row in report['transports'] if row['family'] == version]
        tcp_ok = any(row['tcp']['status'] == 'success' for row in transports)
        dns_ok = report['dns_summary'][str(version)]['succeeded'] > 0
        code = ('DNS_FAILED_NUMERIC_TCP_WORKS' if tcp_ok and not dns_ok else
                'DNS_WORKS_TCP_UNCONFIRMED' if dns_ok and not tcp_ok else
                'TARGETS_PARTIALLY_VERIFIED' if tcp_ok else 'CONNECTIVITY_UNCONFIRMED')
        report['diagnostics'].append({'family':version,'code':code})
    report['status'] = 'success' if all(row['status']=='success' for row in report['dns']) and all(
        row['tcp']['status']=='success' and row['tls']['status']=='success' for row in report['transports']) else 'partial'
    completed()
    return report


def render_row(row, out, kind):
    tr = out.text
    labels = {
        'DNS_TIMEOUT': ('DNS 超时','DNS timed out'),
        'DNS_NO_ADDRESS': ('未取得该协议族地址','No address for this family'),
        'DNS_TEMPORARY_ERROR': ('解析器暂时失败','Temporary resolver error'),
        'TLS_CERTIFICATE_ERROR': ('证书验证失败；检查时间及信任链','Certificate rejected; check clock and trust chain'),
        'TLS_HANDSHAKE_ERROR': ('TLS 握手未完成','TLS handshake failed'),
        'TCP_NOT_CONNECTED': ('TCP 未连接，跳过 TLS','TCP unavailable; TLS skipped'),
        'NETWORK_UNREACHABLE': ('系统报告网络不可达','System reports network unreachable'),
        'CONNECTION_REFUSED': ('连接被拒绝','Connection refused'),
        'TCP_TIMEOUT': ('TCP 超时','TCP timed out'),
        'TLS_TIMEOUT': ('TLS 超时','TLS timed out'),
    }
    def error_label(result):
        code = result.get('error_code','UNKNOWN')
        return tr(*labels[code])+f' ({code})' if code in labels else code
    family = 'IPv'+str(row['family'])
    if kind == 'dns':
        out.row(f'{family} DNS',f"{row['elapsed_ms']:g} ms" if row['status']=='success' else error_label(row),
                'ok' if row['status']=='success' else 'unknown')
    else:
        for stage in ('tcp','tls'):
            result = row[stage]
            out.row(f"{family} {row['target']} {stage.upper()}",
                    f"{result['elapsed_ms']:g} ms" if result['status']=='success' else error_label(result),
                    'ok' if result['status']=='success' else 'unknown')


def run_console(lang='zh', color='auto', report=None, on_result=None, *, out=None):
    from .console import Console
    out = out if out is not None else Console(lang,color)
    report = {} if report is None else report
    seen_dns = seen_transport = 0
    def progress():
        nonlocal seen_dns, seen_transport
        for row in report['dns'][seen_dns:]:
            render_row(row,out,'dns')
        for row in report['transports'][seen_transport:]:
            render_row(row,out,'transport')
        seen_dns, seen_transport = len(report['dns']), len(report['transports'])
        if on_result is not None:
            on_result()
    collect(report, progress)
    for version, summary in report['dns_summary'].items():
        out.row(f'IPv{version} DNS',f"{summary['succeeded']}/{summary['attempted']} "+out.text('成功（仅本次样本）','successful (current sample only)'))
    for diagnosis in report['diagnostics']:
        code = diagnosis['code']
        note = {
            'DNS_FAILED_NUMERIC_TCP_WORKS': ('解析未成功但数字 IP 可连接；先排查解析器','DNS failed but numeric TCP worked; inspect resolver'),
            'DNS_WORKS_TCP_UNCONFIRMED': ('解析有结果，目标 TCP 未确认；检查路由及目标','DNS answered but target TCP is unconfirmed; inspect routes and targets'),
            'TARGETS_PARTIALLY_VERIFIED': ('部分目标 TCP 已确认；TLS 结果单独看','Some target TCP paths verified; inspect TLS separately'),
            'CONNECTIVITY_UNCONFIRMED': ('连接尚未确认','Connectivity unconfirmed'),
        }[code]
        out.row(f"IPv{diagnosis['family']} "+out.text('提示','Hint'),out.text(*note),'unknown')
    out.row(out.text('检测范围','Scope'),out.text('出站 DNS/TCP/TLS 检测','Outbound DNS/TCP/TLS checks'),'unknown')
    return 0 if report['status']=='success' else 1
