"""Four-part console workflow. Capability and measurement limits are explicit."""
import hashlib
import ipaddress
from pathlib import Path
import shutil
import subprocess
import time

from .checks import inspect
from . import __version__
from .quality import run_quality
from .i18n import translator
from .routes import trace as native_trace
from .media import run_console as run_media
from .bandwidth import run_console as measure_bandwidth, is_complete as bandwidth_complete
from .ipquality import collect as collect_ipquality, render as render_ipquality


def execute_provider(argv, timeout=180):
    """Preserve streaming terminal output; no shell interpolation."""
    try:
        return subprocess.run(argv,check=False,timeout=timeout).returncode
    except (OSError,subprocess.TimeoutExpired):
        return 1


def run_suite(lang='zh',offline=False,sample_mib=4,route_target='1.1.1.1',besttrace=None,
              region_script=None,max_hops=30,geo=True,color='auto',bandwidth_rounds=3,skip_route=False,json_output=None,bandwidth_sources=None,port=8388,show_ip=False,ip_enrichment=True):
    from .cli import redact
    from .console import Console
    import re
    ipaddress.ip_address(route_target)
    if not 1<=sample_mib<=20 or not 1<=max_hops<=64 or not 3<=bandwidth_rounds<=8 or not 1<=port<=65535: raise ValueError('Invalid test limits')
    out=Console(lang,color); tr=out.text
    from datetime import datetime,timezone
    report={'schema_version':2,'mode':'read-only','generated_at':datetime.now(timezone.utc).isoformat(),'target_port':port,'network':None,'route':None,'tool_version':__version__,'offline':offline,'bandwidth':None,'ip_quality':None,'media':{}}
    print(tr(f'ProxyDoctor {__version__} | 原生检测 | 联网模式' if not offline else f'ProxyDoctor {__version__} | 离线模式',
             f'ProxyDoctor {__version__} | Native checks | Online' if not offline else f'ProxyDoctor {__version__} | Offline'),flush=True)
    data=redact(inspect(lang=lang,port=port),lang)
    report['system']=data
    checks={item['id']:item for item in data['checks']}
    unknown=tr('未知','Unknown');incomplete=False
    out.section(1,'VPS 性能与资源','VPS resources and performance')
    system=checks['system']['evidence'].split(';')
    out.row(tr('系统','OS'),system[1].strip() if len(system)>1 else unknown)
    out.row(tr('架构','Architecture'),checks['architecture']['evidence'])
    out.row(tr('内核','Kernel'),checks['kernel']['detail'], 'ok' if checks['kernel']['status']=='pass' else 'unknown')
    cpu=checks['cpu']
    out.row('CPU',re.split('[：:]',cpu['evidence'],maxsplit=1)[-1], 'ok' if cpu['status']=='pass' else 'unknown')
    count=re.search(r'\d+',cpu['detail'])
    out.row(tr('逻辑核心','Logical CPUs'),count.group() if count else unknown,'ok' if count else 'unknown')
    for key,zh,en in [('memory_total','总内存','RAM total'),('memory','可用内存','RAM available'),('disk_capacity','磁盘','Root filesystem')]:
        item=checks.get(key)
        value=re.split(r'[（(]',item['detail'],maxsplit=1)[0] if item else unknown
        out.row(tr(zh,en),value,'ok' if item and item['status']=='pass' else 'unknown')
    statuses={'pass':tr('通过','Pass'),'warn':tr('注意','Warning'),'fail':tr('失败','Failed'),
              'unknown':tr('未知','Unknown'),'skip':tr('跳过','Skipped')}
    for key,zh,en in [('default_route','默认路由','Default route'),('dns_config','DNS 配置','DNS config'),
                      ('ports',f'本机端口 {port}',f'Local port {port}'),('ssh_port_safety','SSH 端口保护','SSH port guard'),
                      ('ssh','SSH 配置','SSH config'),('firewall','本机防火墙','Local firewall'),('cloud_firewall','云防火墙','Cloud firewall')]:
        item=checks[key]
        value=statuses[item['status']]
        if key=='ports' and item['status']=='pass': value=tr('未发现占用（仅本机）','No listener found (local only)')
        if key=='ports' and item['status']=='warn': value=tr('已占用','In use')
        if key=='ssh_port_safety' and item['status']=='warn': value=tr('目标端口与 SSH 冲突','Target conflicts with SSH')
        if key=='ssh' and item['status']=='warn': value=tr('允许 root 或密码认证','Root or password auth allowed')
        out.row(tr(zh,en),value,'bad' if item['status'] in ('warn','fail') else 'ok' if item['status']=='pass' else 'unknown')
    block=b'\x00'*1024**2;start=time.perf_counter()
    for _ in range(32): hashlib.sha256(block).digest()
    out.row('SHA-256',f'{32/max(time.perf_counter()-start,0.000001):.1f} MiB/s')
    if offline: out.row(tr('带宽','Bandwidth'),tr('跳过','Skipped'),'unknown')
    else:
        bandwidth=measure_bandwidth(lang=lang,color=color,rounds=bandwidth_rounds,
                                    sample_mib=sample_mib,sources=bandwidth_sources)
        report['bandwidth']=bandwidth
        incomplete=not bandwidth_complete(bandwidth) or incomplete
    out.section(2,'节点网络质量','Node network quality')
    if offline: out.row(tr('网络','Network'),tr('跳过','Skipped'),'unknown')
    else:
        network={}
        incomplete=bool(run_quality(translator(lang),compact=True,lang=lang,color=color,report=network)) or incomplete
        report['network']=network
        metadata=collect_ipquality(enrich=ip_enrichment)
        report['ip_quality']=metadata
        render_ipquality(metadata,out,show_ip)
        incomplete=not metadata['coverage']['complete'] or incomplete
    out.section(3,'路由追踪','Route trace')
    if offline or skip_route: out.row(tr('路由','Route'),tr('跳过','Skipped'),'unknown')
    else:
        print(tr(f'目标 {route_target} · 最多 {max_hops} 跳 · 位置为数据库估计',
                 f'Target {route_target} · up to {max_hops} hops · estimated IP location'),flush=True)
        print(tr('跳   IP 地址                                    延迟       位置',
                 'Hop  IP address                                  Latency    Location'),flush=True)
        route={'target':route_target,'max_hops':max_hops,'geo_enabled':geo,'hops':[]}
        report['route']=route
        if besttrace and Path(besttrace).is_file():
            route['provider']='external_besttrace'
            route['state']='external_output_only'
            incomplete=bool(execute_provider([str(Path(besttrace).resolve()),route_target],120)) or incomplete
        else:
            def route_output(line,**kwargs):
                print(out.paint(line,'unknown' if any(word in line for word in ('*','unavailable','未知','Unknown')) else 'ok',preserve_space=True),flush=True)
            route['provider']='native_udp'
            route_code=native_trace(route_target,emit=route_output,hops=max_hops,lang=lang,geo=geo,records=route['hops'])
            route['state']='reached' if route_code==0 else 'incomplete'
            incomplete=bool(route_code) or incomplete
    out.section(4,'流媒体区域限制','Streaming region restrictions')
    if offline: out.row(tr('流媒体','Streaming'),tr('跳过','Skipped'),'unknown')
    elif region_script:
        path=Path(region_script).resolve();bash=shutil.which('bash')
        if path.is_file() and bash: incomplete=bool(execute_provider([bash,str(path)],600)) or incomplete
        else: out.row('RegionRestrictionCheck',unknown,'unknown');incomplete=True
    else:
        report['media']=run_media(lang,color)
        incomplete=True  # Account/DRM playback is intentionally not claimed.
    print(tr('\n说明：带宽按来源独立统计 HTTPS 多轮吞吐（含建连）；地区套餐/片库可见不等于账号播放。IP 标记与举报为第三方记录，零举报不保证安全。',
             '\nNotes: per-source repeated HTTPS throughput, including setup. Offers/catalogs do not prove account playback. Provider flags and reports are evidence; zero reports do not guarantee safety.'),flush=True)
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    report['result']='incomplete' if incomplete else 'local_execution_complete'
    counts={state:sum(item.get('state')==state for item in report['media'].values()) for state in ('restricted','offer_available','catalog_visible','metadata_available','unknown')}
    report['summary']={'media':counts,'playback':'not_tested','system_findings':sum(item['status'] in ('warn','fail') for item in data['checks'])}
    print(tr(f"体检结果：{report['summary']['system_findings']} 项本机提示 · 媒体限制 {counts['restricted']} · 媒体未知 {counts['unknown']}",
             f"Results: {report['summary']['system_findings']} local findings · Media restricted {counts['restricted']} · Media unknown {counts['unknown']}"),flush=True)
    if json_output:
        import json
        with Path(json_output).open('x',encoding='utf-8') as stream:
            json.dump(redact(report,lang),stream,ensure_ascii=False,indent=2)
        print(tr('脱敏 JSON 已保存：','Redacted JSON saved: ')+str(json_output),flush=True)
    return 1 if incomplete else 0


