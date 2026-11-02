"""Four-part console workflow. Capability and measurement limits are explicit."""
import ipaddress
from pathlib import Path
import shutil
import subprocess
import time

from .checks import inspect
from . import __version__, release_label
from .quality import run_quality
from .i18n import translator
from .routes import trace as native_trace, trace_method as protocol_trace
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
              region_script=None,max_hops=30,geo=True,color='auto',bandwidth_rounds=3,skip_route=False,json_output=None,bandwidth_sources=None,port=8388,show_ip=False,ip_enrichment=True,allow_bandwidth=False,mail_probes=False,route_probes=3,theme='default',
              route_method='udp',tcp_port=443,include_return_routes=False,include_bgp=False,show_unavailable=False):
    from .cli import redact
    from .console import Console
    import re
    ipaddress.ip_address(route_target)
    if not 1<=sample_mib<=20 or not 1<=max_hops<=64 or not 3<=bandwidth_rounds<=8 or not 1<=port<=65535: raise ValueError('Invalid test limits')
    if besttrace or region_script:
        raise ValueError('External executables are disabled in the safe workflow; use native checks')
    if not 1<=route_probes<=3:raise ValueError('Route probe rounds must be 1..3')
    if route_method not in ('udp','icmp','tcp') or not 1<=tcp_port<=65535 or theme not in ('default','iprisk','framed'):
        raise ValueError('Invalid route or theme options')
    out=Console(lang,color,hide_unavailable=not show_unavailable); tr=out.text
    iprisk = theme == 'iprisk'
    framed = theme == 'framed'
    from datetime import datetime,timezone
    report={'schema_version':3,'mode':'read-only','generated_at':datetime.now(timezone.utc).isoformat(),'target_port':port,'network':None,'route':None,'tool_version':__version__,'offline':offline,'bandwidth':None,'bandwidth_consent':allow_bandwidth,'cpu_benchmark':'not_run','ip_quality':None,'media':{}}
    if framed:
        out.frame_open(tr('VPSMaster 检测报告','VPSMaster diagnostic report'), box_w=78, subtitle=release_label(lang) + ' · ' + __version__)
        out.frame_keyvalue(tr('模式','Mode'), tr('离线模式' if offline else '联网模式','Offline' if offline else 'Online'))
        out.frame_keyvalue(tr('目标端口','Target port'), str(port))
    elif iprisk:
        out.banner('  VPSMaster  ' + ('v' + __version__))
        out.line(release_label(lang), 'unknown')
        out.keyvalue(tr('只读体检报告 · 原生检测','Read-only diagnostic report · native checks'),
                     tr('离线模式' if offline else '联网模式','Offline' if offline else 'Online'),'title')
        out.hrule()
        print(flush=True)
    else:
        out.line(release_label(lang), 'unknown')
        print(tr(f'VPSMaster {__version__} | 原生检测 | 联网模式' if not offline else f'VPSMaster {__version__} | 离线模式',
                 f'VPSMaster {__version__} | Native checks | Online' if not offline else f'VPSMaster {__version__} | Offline'),flush=True)
    from .reports import ReportStore, UnavailableStore, utc_now
    from .runner import ModuleRunner
    data = {'checks': []}
    unknown = tr('未知','Unknown')
    incomplete = False
    report['result'] = 'running'
    # Open an exclusive recovery journal before starting any checks.
    try:
        store = ReportStore(json_output, lambda value: redact(value, lang))
    except FileExistsError:
        raise  # A collision must be resolved before running any checks.
    except OSError:
        store = UnavailableStore(json_output)
    persistence_warning = False

    def checkpoint():
        nonlocal persistence_warning
        from .schema import normalize_report
        normalize_report(report)
        if not store.checkpoint(report) and not persistence_warning:
            persistence_warning = True
            out.row(tr('报告保存','Report storage'),tr('写入失败；保留已有日志并继续终端检测','Write failed; retaining prior journal and continuing terminal checks'),'bad')

    def module_error(name):
        out.row(name, tr('本模块异常，继续其他检测（MODULE_ERROR）','Module failed; continuing other checks (MODULE_ERROR)'),'bad')

    runner = ModuleRunner(report, checkpoint, module_error)

    def heading(number, zh, en, kind='b_cyan'):
        if iprisk:
            out.theme_section(number, zh, en, kind)
        else:
            out.section(number, zh, en)

    def collect_system():
        nonlocal data, incomplete
        data=redact(inspect(lang=lang,port=port),lang)
        report['system']=data
        checks={item['id']:item for item in data['checks']}
        unknown=tr('未知','Unknown')
        heading(1,'基础信息','Basic information')
        system=checks['system']['evidence'].split(';')
        out.row(tr('系统','OS'),system[1].strip() if len(system)>1 else unknown)
        out.row(tr('架构','Architecture'),checks['architecture']['evidence'])
        out.row(tr('内核','Kernel'),checks['kernel']['detail'], 'ok' if checks['kernel']['status']=='pass' else 'unknown')
        cpu=checks['cpu']
        out.row('CPU',re.split('[：:]',cpu['evidence'],maxsplit=1)[-1], 'ok' if cpu['status']=='pass' else 'unknown')
        # Allocation-focused numbers are rendered by the resources module.
        # Keep raw OS-visible values in structured evidence, not as VPS limits.
        for key,zh,en in [('disk_capacity','磁盘','Root filesystem')]:
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
        out.row('CPU benchmark',tr('未运行：常规检测不执行性能基准','Not run: routine checks do not benchmark CPU'),'unknown')

    def collect_bandwidth():
        nonlocal data, incomplete
        if offline or not allow_bandwidth:
            out.row(tr('带宽','Bandwidth'),tr('跳过；使用 --allow-bandwidth 明确允许测速','Skipped; use --allow-bandwidth to consent to traffic tests'),'unknown')
        else:
            report['bandwidth']={}
            bandwidth=measure_bandwidth(lang=lang,color=color,rounds=bandwidth_rounds,
                                        sample_mib=sample_mib,sources=bandwidth_sources,destination=report['bandwidth'],on_result=checkpoint,out=out)
            report['bandwidth']=bandwidth
            incomplete=not bandwidth_complete(bandwidth) or incomplete

    def collect_resources():
        from .resources import collect, render
        resource_data = collect()
        report['resources'] = resource_data
        render(resource_data, out)

    def collect_security():
        nonlocal incomplete
        from .security import collect as collect_security_data, render as render_security
        security_data = {}
        report['security'] = security_data
        if framed:
            out.frame_line(tr('基础安全（只读）','Basic security (read-only)'), 'title')
        else:
            print(out.paint(tr('--- 基础安全（只读） ---','--- Basic security (read-only) ---'),'title'),flush=True)
        collect_security_data(security_data, on_result=checkpoint)
        render_security(security_data, out)
        incomplete = bool(security_data.get('review_count') or security_data['status'] == 'unsupported') or incomplete

    def collect_network():
        nonlocal data, incomplete
        heading(2,'节点网络质量','Node network quality')
        if offline: out.row(tr('网络','Network'),tr('跳过','Skipped'),'unknown')
        else:
            from .connectivity import run_console as run_connectivity
            network={}
            report['network']=network
            incomplete=bool(run_connectivity(lang=lang,color=color,report=network,on_result=checkpoint,out=out)) or incomplete

    def collect_ip_quality():
        nonlocal data, incomplete
        report['ip_quality']={}
        metadata=collect_ipquality(enrich=ip_enrichment,mail=mail_probes,destination=report['ip_quality'],on_result=checkpoint)
        report['ip_quality']=metadata
        render_ipquality(metadata,out,show_ip)
        incomplete=not metadata['coverage']['complete'] or incomplete

    def collect_route():
        nonlocal data, incomplete
        heading(3,'路由追踪','Route trace')
        if offline or skip_route: out.row(tr('路由','Route'),tr('跳过','Skipped'),'unknown')
        else:
            out.line(tr(f'目标 {route_target} · 最多 {max_hops} 跳 · 位置为数据库估计',
                        f'Target {route_target} · up to {max_hops} hops · estimated IP location'))
            out.line(tr('跳   IP 地址                                    延迟       位置',
                        'Hop  IP address                                  Latency    Location'))
            out.line(tr('每跳仅1次探测；响应/超时计数不等于转发丢包率。','One probe per hop; response/timeout counts are not forwarding-loss estimates.'))
            route={'target':route_target,'max_hops':max_hops,'geo_enabled':geo,'method':route_method,'hops':[]}
            report['route']=route
            if besttrace and Path(besttrace).is_file():
                route['provider']='external_besttrace'
                route['state']='external_output_only'
                incomplete=bool(execute_provider([str(Path(besttrace).resolve()),route_target],120)) or incomplete
            else:
                def route_output(line,**kwargs):
                    out.line(line,'unknown' if any(word in line for word in ('*','unavailable','未知','Unknown')) else 'ok')
                route['provider']='native_udp' if route_method=='udp' else 'system_traceroute_'+route_method
                from .routes import summarize_hops
                deadline=time.monotonic()+90
                replies=0;attempts=0
                route['probe_rounds_requested']=route_probes
                route['probe_outcomes']=[]
                for number in range(route_probes):
                    if time.monotonic()>=deadline:break
                    out.line(tr(f'路由探测 {number+1}/{route_probes}',f'Route probe {number+1}/{route_probes}'))
                    outcome={}
                    options=dict(emit=route_output,hops=max_hops,lang=lang,geo=geo and number==0,summary=outcome,
                                 records=route['hops'],on_result=checkpoint,deadline=deadline)
                    route_code=(native_trace(route_target,**options) if route_method=='udp' else
                                protocol_trace(route_target,method=route_method,tcp_port=tcp_port,**options))
                    attempts+=1;replies+=route_code==0
                    route['probe_outcomes'].append(outcome)
                    route['statistics']=summarize_hops(route['hops'])
                    checkpoint()
                route.update(state='reached' if replies else 'incomplete',probe_rounds_run=attempts,destination_responses=replies)
                for row in route.get('statistics',[]):
                    out.row(tr('跳','Hop')+' '+str(row['hop']),
                            f"reply {row['responses']}/{row['probes_sent']} · timeout {row['timeouts']} · response-loss {row['response_loss_percent']}%",'unknown')
                out.line(tr('以上是路由器响应缺失统计，不是线路转发丢包率。','These are router-response statistics, not forwarding packet-loss estimates.'))
                incomplete=replies<route_probes or incomplete

    def collect_media():
        nonlocal data, incomplete
        heading(4,'流媒体可达性','Media reachability')
        if offline: out.row(tr('流媒体','Streaming'),tr('跳过','Skipped'),'unknown')
        elif region_script:
            path=Path(region_script).resolve();bash=shutil.which('bash')
            if path.is_file() and bash: incomplete=bool(execute_provider([bash,str(path)],600)) or incomplete
            else: out.row('RegionRestrictionCheck',unknown,'unknown');incomplete=True
        else:
            run_media(lang,color,results=report['media'],on_result=checkpoint,out=out)
            incomplete=any(item.get('state')!='reachable' for item in report['media'].values()) or incomplete

    def collect_return_routes():
        nonlocal incomplete
        from .carriers import return_routes
        out.line(tr('三城三运营商 · 方向：本机 → 中国目标','Three cities × three carriers · this host → China targets'),'title')
        report['return_routes']={}
        return_routes(method=route_method,hops=max_hops,geo=False,tcp_port=tcp_port,
                      destination=report['return_routes'],on_result=checkpoint,out=out)
        incomplete=report['return_routes']['status']!='success' or incomplete

    def collect_bgp():
        nonlocal incomplete
        from .bgp import collect,render
        address=(report.get('ip_quality') or {}).get('ip')
        if not address:
            report['bgp']={'status':'unknown','error_code':'EGRESS_IP_UNAVAILABLE'}
            out.row('BGP','EGRESS_IP_UNAVAILABLE','unknown');incomplete=True
            return
        report['bgp']={}
        collect(address,report['bgp'],checkpoint);render(report['bgp'],out)
        incomplete=report['bgp']['status']!='success' or incomplete

    cancelled = False
    try:
        runner.run('system', collect_system)
        runner.run('resources', collect_resources)
        runner.run('security', collect_security)
        runner.run('bandwidth', collect_bandwidth,
                   'offline' if offline else 'consent_required' if not allow_bandwidth else None)
        if offline and show_unavailable:
            heading(2,'节点网络质量','Node network quality')
            out.row('DNS / TCP / TLS',tr('离线跳过','Skipped offline'),'unknown')
        runner.run('network', collect_network, 'offline' if offline else None)
        runner.run('ip_quality', collect_ip_quality, 'offline' if offline else None)
        if (offline or skip_route) and show_unavailable:
            heading(3,'路由追踪','Route trace')
            out.row(tr('路由','Route'),tr('已跳过','Skipped'),'unknown')
        runner.run('route', collect_route, 'offline' if offline else 'user_skipped' if skip_route else None)
        if offline and show_unavailable:
            heading(4,'流媒体可达性','Media reachability')
            out.row(tr('流媒体','Media'),tr('离线跳过','Skipped offline'),'unknown')
        runner.run('media', collect_media, 'offline' if offline else None)
        if include_return_routes:runner.run('return_routes',collect_return_routes,'offline' if offline else None)
        if include_bgp:runner.run('bgp',collect_bgp,'offline' if offline else None)
    except KeyboardInterrupt:
        from .worker import cancel_all
        cancel_all()
        cancelled = True
    finally:
        report['finished_at'] = utc_now()
        failed = any(item['status'] == 'failure' for item in report['modules'].values())
        report['result'] = 'cancelled' if cancelled else 'incomplete' if incomplete or failed else 'local_execution_complete'
        report['summary'] = {
            'playback': 'not_tested',
            'system_findings': sum(item['status'] in ('warn','fail') for item in data['checks']),
            'failed_modules': sum(item['status'] == 'failure' for item in report['modules'].values()),
            'permission_reviews': report.get('security',{}).get('review_count',0),
            'media': {state: sum(isinstance(item, dict) and item.get('state') == state
                                 for item in report['media'].values())
                      for state in ('reachable','access_denied','rate_limited','http_error','unknown')},
        }
        from .schema import normalize_report
        normalize_report(report)
        saved = store.finish(report)
        store.close()
    out.row(tr('体检结果','Results'), report['result'], 'unknown' if cancelled or incomplete or failed else 'ok')
    if saved and not store.failed:
        out.row(tr('脱敏报告','Redacted report'), str(store.path))
    else:
        out.row(tr('报告保存','Report storage'), tr('保存未完成，请保留已有恢复日志','Save incomplete; retain the existing recovery journal'),'bad')
    if store.journal_path is not None:
        out.row(tr('恢复日志','Recovery journal'), str(store.journal_path))
    if framed:
        out.frame_close()
    return 130 if cancelled else 1 if incomplete or failed or store.failed else 0
