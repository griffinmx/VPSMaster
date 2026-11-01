"""Opt-in, bounded outbound checks; do not infer reputation or universal reachability."""
import ipaddress
import json
import socket
import subprocess
import sys
import time

TARGETS = (("Cloudflare", "1.1.1.1", 443), ("Google", "8.8.8.8", 443))
DNS_NAME = "example.com"
TIMEOUT = 5


def dns_check():
    # A subprocess permits a hard timeout even if the system resolver blocks.
    program = ("import json,socket; "
               "a=socket.getaddrinfo('example.com',443,type=socket.SOCK_STREAM); "
               "print(json.dumps(sorted(set(x[0] for x in a))))")
    start = time.monotonic()
    try:
        proc = subprocess.run([sys.executable, '-I', '-B', '-c', program], capture_output=True,
                              text=True, timeout=TIMEOUT, check=False)
        if proc.returncode != 0:
            return {'status':'unknown', 'reason':'lookup_failed'}
        families = json.loads(proc.stdout)
        if not isinstance(families, list) or not families:
            return {'status':'unknown', 'reason':'no_answers'}
        return {'status':'pass', 'elapsed_ms':round((time.monotonic()-start)*1000),
                'ipv4':socket.AF_INET in families, 'ipv6':socket.AF_INET6 in families}
    except subprocess.TimeoutExpired:
        return {'status':'unknown', 'reason':'timeout'}
    except (OSError, ValueError, TypeError):
        return {'status':'unknown', 'reason':'lookup_failed'}


def tcp_check(label, address, port):
    # Validate a numeric address so this check never triggers DNS.
    ipaddress.ip_address(address)
    start = time.monotonic()
    try:
        with socket.create_connection((address, port), timeout=TIMEOUT):
            elapsed = round((time.monotonic()-start)*1000)
        return {'target':label, 'port':port, 'status':'pass', 'elapsed_ms':elapsed}
    except (OSError, TimeoutError):
        return {'target':label, 'port':port, 'status':'unknown'}


def run_quality(t, emit=print, compact=False, lang='zh', color='auto', report=None, on_result=None):
    """Run explicit checks, flushing each result as soon as it is available."""
    if compact:
        from .console import Console
        console=Console(lang,color)
        dns=dns_check()
        if report is not None: report.update(dns=dns,tcp=[])
        if on_result is not None: on_result()
        if dns['status']=='pass':
            versions='/'.join(v for v,ok in [('IPv4',dns['ipv4']),('IPv6',dns['ipv6'])] if ok)
            console.row('DNS',f"{versions} / {dns['elapsed_ms']} ms")
        else: console.row('DNS',console.text('未成功','Unsuccessful'),'bad')
        complete=dns['status']=='pass'
        for label,address,port in TARGETS:
            result=tcp_check(label,address,port)
            if report is not None: report['tcp'].append(result)
            if on_result is not None: on_result()
            ok=result['status']=='pass'
            console.row(f'{label} TCP/{port}',f"{result['elapsed_ms']} ms" if ok else console.text('未连通','Unreachable'),'ok' if ok else 'bad')
            complete=complete and ok
        return 0 if complete else 1
    def show(message):
        emit(message, flush=True)
    show(t('网络质量检测：会向系统 DNS、Cloudflare 和 Google 发起请求。'))
    show(t('正在查询 DNS：example.com ...'))
    dns = dns_check()
    if report is not None: report.update(dns=dns,tcp=[])
    if on_result is not None: on_result()
    complete = dns['status'] == 'pass'
    if dns['status'] == 'pass':
        versions = '/'.join(v for v, ok in [('IPv4', dns['ipv4']), ('IPv6', dns['ipv6'])] if ok) or t('其他')
        show(t('DNS 查询成功：{versions}，耗时 {ms} ms', versions=versions, ms=dns['elapsed_ms']))
    else:
        show(t('DNS 查询未成功；原因可能是超时、网络或解析器配置，不能确定唯一原因。'))
    for label, address, port in TARGETS:
        show(t('正在测试 {target} TCP {port} ...', target=label, port=port))
        result = tcp_check(label, address, port)
        if report is not None: report['tcp'].append(result)
        if on_result is not None: on_result()
        complete = complete and result['status'] == 'pass'
        if result['status'] == 'pass':
            show(t('{target} TCP 连接成功：{ms} ms', target=label, ms=result['elapsed_ms']))
        else:
            show(t('{target} TCP 连接未成功；原因尚未确定。', target=label))
    show(t('以上结果为本次从此服务器到这些测试目标的连接情况。'))
    return 0 if complete else 1
