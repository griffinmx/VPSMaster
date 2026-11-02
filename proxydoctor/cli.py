import argparse
import ipaddress
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from . import __version__, release_label
from .checks import inspect
from .i18n import translator
from .quality import run_quality
from .suite import run_suite
from .bandwidth import SOURCES, CHINA_SOURCES


LABELS = {"pass": "通过", "warn": "注意", "unknown": "未知", "skip": "跳过", "fail": "失败"}


def redact(value, lang="zh"):
    """Mask IP addresses in exports; never claim arbitrary text is secret-free."""
    if isinstance(value, dict):
        return {key: redact(item, lang) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, lang) for item in value]
    if not isinstance(value, str):
        return value
    hidden = translator(lang)("[IP已隐藏]")
    def mask_v6(match):
        token = match.group(0)
        address = token.rstrip(".")
        try:
            ipaddress.IPv6Address(address.split("%", 1)[0])
            return hidden + token[len(address):]
        except ValueError:
            return token
    # IPv6 first: replacing embedded IPv4 first would break mapped IPv6 parsing.
    value = re.sub(r"[0-9a-fA-F:.]+(?:%[a-zA-Z0-9_.-]+)?", mask_v6, value)
    return re.sub(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?!\w|\.\d)", hidden, value)


class LocalizedParser(argparse.ArgumentParser):
    def __init__(self, *args, lang="zh", **kwargs):
        self.lang = lang
        super().__init__(*args, add_help=False, **kwargs)
        t = translator(lang)
        self._positionals.title = t("命令")
        self._optionals.title = t("选项")
        self.add_argument("-h", "--help", action="help", help=t("显示帮助并退出"))

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, translator(self.lang)("参数错误：{message}", message=message) + "\n")


def _main():
    # Support Windows consoles that cannot encode Chinese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    # Discover language before building help/errors. --lang works on either side of check.
    language_parser = argparse.ArgumentParser(add_help=False)
    language_parser.add_argument("--lang", choices=("zh", "en"), default="zh")
    language_args, remaining = language_parser.parse_known_args()
    lang = language_args.lang
    # Auto-degrade to English when the console cannot render CJK glyphs
    # (e.g. Linux framebuffer tty1) unless the user explicitly requested zh.
    if lang == 'zh':
        from .console import can_render_cjk
        explicit_language = any(arg == '--lang' or arg.startswith('--lang=') for arg in sys.argv[1:])
        if not can_render_cjk() and not explicit_language:
            lang = 'en'
    t = translator(lang)
    st = lambda zh, en: zh if lang == 'zh' else en
    parser = LocalizedParser(prog="vpsmaster", lang=lang, description=("VPSMaster（只读体检）：check 默认离线；suite 会联网" if lang=='zh' else 'VPSMaster (read-only diagnostics): check defaults offline; suite contacts external services'))
    parser.add_argument("--version", action="version", version=__version__ + ' · ' + release_label(lang), help=t("显示版本并退出"))
    parser.add_argument("--lang", choices=("zh", "en"), default=lang, help=t("界面和报告语言：zh 中文，en 英文（默认 zh）"))
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", lang=lang, help=t("读取系统信息并生成体检报告"))
    check.add_argument("--lang", choices=("zh", "en"), default=lang, help=t("界面和报告语言：zh 中文，en 英文（默认 zh）"))
    check.add_argument("--port", type=int, default=8388, help=t("拟使用的代理端口，默认 8388"))
    ips = check.add_mutually_exclusive_group()
    ips.add_argument("--public-ip", help=t("云控制台提供的 IP；本工具不验证归属"))
    ips.add_argument("--detect-public-ip", action="store_true", help=t("向 ipify 发送 HTTPS 请求查询出口 IP（第三方会看到该地址）"))
    check.add_argument("--json", action="store_true", dest="as_json", help=t("输出 JSON（默认隐藏 IP）"))
    check.add_argument("--show-ip", action="store_true", help=t("仅在终端显示完整 IP；保存的报告仍脱敏"))
    check.add_argument("--output", type=Path, help=t("另存为脱敏 JSON；已存在的文件不会覆盖"))
    check.add_argument("--color", choices=("auto", "always", "never"), default="auto", help=st("彩色输出：auto/always/never", "Colour output: auto/always/never"))
    check.add_argument("--theme", choices=("default", "iprisk", "framed"), default="default", help=st("终端版式：default/iprisk/framed", "Terminal theme: default/iprisk/framed"))
    node = sub.add_parser("nodequality", lang=lang, help=t("运行本地 NodeQuality 脚本并实时显示输出"))
    node.add_argument("--lang", choices=("zh", "en"), default=lang, help=t("界面和报告语言：zh 中文，en 英文（默认 zh）"))
    node.add_argument("--script", type=Path, required=True, help=t("已下载并检查的 NodeQuality 脚本路径"))
    quality = sub.add_parser('quality', lang=lang, help=t('联网检测 DNS 和 TCP 连接并实时显示结果'))
    quality.add_argument('--lang', choices=('zh','en'), default=lang, help=t('界面和报告语言：zh 中文，en 英文（默认 zh）'))
    quality.add_argument('--color', choices=('auto','always','never'), default='auto', help=st('彩色输出：auto/always/never','Colour output: auto/always/never'))
    export = sub.add_parser('report',lang=lang,help=st('将本地 JSON 导出为脱敏 Markdown','Export local JSON as redacted Markdown'))
    export.add_argument('--input',type=Path,required=True)
    export.add_argument('--output',type=Path,required=True)
    recover = sub.add_parser('recover',lang=lang,help=st('从恢复日志导出最后完整结果','Export the last complete recovery snapshot'))
    recover.add_argument('--journal',type=Path,required=True)
    recover.add_argument('--output',type=Path,required=True)
    recover.add_argument('--format',choices=('json','markdown'),default='json')
    ipq = sub.add_parser('ipquality',lang=lang,help=st('只查询 IP 归属与风险，按来源保留证据','Query IP ownership and provider-specific risk evidence'))
    ipq.add_argument('--lang',choices=('zh','en'),default=lang)
    ipq.add_argument('--color',choices=('auto','always','never'),default='auto')
    ipq.add_argument('--show-ip',action='store_true',help=st('终端显示出口 IP；文件仍脱敏','Show egress IP in terminal; exports stay redacted'))
    ipq.add_argument('--no-enrichment',action='store_true',help=st('不查询额外免密钥来源','Skip additional keyless sources'))
    ipq.add_argument('--mail-probes',action='store_true',help=st('额外查询PTR并测试单目标出站TCP/25；不发送邮件','Query PTR and one outbound TCP/25 target; sends no email'))
    ipq.add_argument('--json-output',type=Path)
    bandwidth = sub.add_parser('bandwidth',lang=lang,help=st('仅运行多来源多轮测速','Run only repeated multi-source bandwidth tests'))
    bandwidth.add_argument('--lang',choices=('zh','en'),default=lang)
    bandwidth.add_argument('--color',choices=('auto','always','never'),default='auto')
    bandwidth.add_argument('--sample-mib',type=int,choices=range(1,21),default=4,metavar='1..20')
    bandwidth.add_argument('--rounds','--bandwidth-rounds',type=int,choices=range(3,9),default=3,metavar='3..8')
    bandwidth.add_argument('--source','--bandwidth-source',choices=tuple(SOURCES),action='append',help=st('可重复指定；默认 Cloudflare + OVHcloud','Repeat to select; default Cloudflare + OVHcloud'))
    bandwidth.add_argument('--allow-bandwidth',action='store_true',help=st('明确允许消耗流量和带宽；请求载荷预算将在执行前显示','Consent to traffic and bandwidth use; payload budget is printed before execution'))
    bandwidth.add_argument('--china',action='store_true',help=st('选择大陆三运营商候选；缺失来源如实显示','Select three mainland-carrier candidates; missing sources stay unknown'))
    bandwidth.add_argument('--json-output',type=Path,help=st('保存脱敏检测依据，不覆盖文件','Save redacted evidence; never overwrite'))
    media = sub.add_parser('media',lang=lang,help=st('仅检测流媒体，不重复测速','Check media without repeating bandwidth tests'))
    media.add_argument('--lang',choices=('zh','en'),default=lang)
    media.add_argument('--color',choices=('auto','always','never'),default='auto')
    media.add_argument('--json-output',type=Path,help=st('保存脱敏检测依据，不覆盖文件','Save redacted evidence; never overwrite'))
    suite = sub.add_parser('suite',aliases=['all'],lang=lang,help=st('一键综合检测：all（suite 兼容入口）','One-command diagnostics: all (suite compatible)'))
    suite.add_argument('--full',action='store_true',help=st('all 扩展模式；带宽仍需独立授权','Extended all mode; bandwidth still requires consent'))
    suite.add_argument('--total-timeout',type=int,choices=range(30,901),metavar='30..900',help=st('all 总秒数预算，默认300/full600','all total seconds; default 300/full600'))
    suite.add_argument('--module-timeout',type=int,choices=range(5,121),default=60,metavar='5..120',help=st('all 每模块秒数预算，默认60','all per-module seconds, default 60'))
    suite.add_argument('--lang',choices=('zh','en'),default=lang)
    suite.add_argument('--allow-bandwidth',action='store_true',help=st('明确允许带宽测速（默认跳过）','Consent to bandwidth tests (skipped by default)'))
    suite.add_argument('--offline',action='store_true',help=st('跳过联网检测','Skip outbound requests'))
    suite.add_argument('--port',type=int,default=8388,help=st('体检目标端口，默认 8388','Target port to inspect (default 8388)'))
    suite.add_argument('--show-ip',action='store_true',help=st('终端显示出口 IP；文件仍脱敏','Show egress IP in terminal; exports stay redacted'))
    suite.add_argument('--no-ip-enrichment',action='store_true',help=st('不查询额外 IP 风险来源','Skip additional IP risk sources'))
    suite.add_argument('--mail-probes',action='store_true',help=st('额外执行PTR与单目标出站TCP/25检查','Include PTR and one outbound TCP/25 check'))
    suite.add_argument('--sample-mib',type=int,choices=range(1,21),default=4,metavar='1..20',help=st('每轮每方向 MiB，默认 4','MiB per round per direction (default 4)'))
    suite.add_argument('--bandwidth-rounds',type=int,choices=range(3,9),default=3,metavar='3..8',help=st('每方向测速轮数，默认 3','Measured rounds per direction (default 3)'))
    suite.add_argument('--bandwidth-source',choices=tuple(SOURCES),action='append',help=st('可重复指定；默认 Cloudflare + OVHcloud','Repeat to select; default Cloudflare + OVHcloud'))
    suite.add_argument('--skip-route',action='store_true',help=st('跳过路由追踪','Skip route trace'))
    suite.add_argument('--json-output',type=Path,help=st('保存脱敏检测依据，不覆盖文件','Save redacted evidence; never overwrite'))
    suite.add_argument('--route-target',default='1.1.1.1',help=st('路由目标，IPv4 或 IPv6 地址','Numeric IPv4 or IPv6 route destination'))
    suite.add_argument('--besttrace',type=Path,help=st('本地 BestTrace 可执行文件','Local BestTrace executable'))
    suite.add_argument('--region-script',type=Path,help=st('已审阅的本地 RegionRestrictionCheck 脚本','Reviewed local RegionRestrictionCheck script'))
    suite.add_argument('--max-hops',type=int,choices=range(1,65),default=30,metavar='1..64')
    suite.add_argument('--route-probes',type=int,choices=range(1,4),default=3,help=st('路由重复探测轮数1..3；共享90秒预算','Repeat route probes 1..3 times; shared 90s budget'))
    suite.add_argument('--no-geo',action='store_true',help=st('不查询路由 IP 位置','Skip route IP geolocation lookups'))
    suite.add_argument('--color',choices=('auto','always','never'),default='auto')
    suite.add_argument('--theme', choices=('default','iprisk','framed'), default='default', help=st('终端版式：default/iprisk/framed','Terminal theme: default/iprisk/framed'))
    suite.add_argument('--show-unavailable', action='store_true', help=st('显示无数据与跳过的条目（完整报告始终保留）','Show unavailable/skipped rows (always retained in reports)'))
    suite.add_argument('--route-method',choices=('udp','icmp','tcp'),default='udp')
    suite.add_argument('--tcp-port',type=int,default=443)
    suite.add_argument('--china-speed',action='store_true',help=st('启用大陆三运营商候选测速；仍需 --allow-bandwidth','Select mainland carrier speed candidates; requires --allow-bandwidth'))
    suite.add_argument('--include-return-routes',action='store_true',help=st('额外运行三城三运营商方向追踪','Add three-city × three-carrier outbound traces'))
    suite.add_argument('--include-bgp',action='store_true',help=st('查询出口 IP 的 RIPE RIS BGP 观测','Query RIPE RIS BGP observations for egress IP'))
    for name,description in (('trace',st('单目标 UDP/ICMP/TCP 路由','Single-target UDP/ICMP/TCP trace')),
                             ('return-route',st('三城三运营商逐跳追踪','Three cities × three carriers traces')),
                             ('bgp',st('查询前缀、起源 ASN、邻居及 RIS AS_PATH','Query prefix, origin ASN, neighbours and RIS AS_PATH')),
                             ('cn-nodes',st('小流量探测候选测速节点','Probe candidate speed nodes with small samples'))):
        command=sub.add_parser(name,lang=lang,help=description)
        command.add_argument('--color',choices=('auto','always','never'),default='auto')
        command.add_argument('--json-output',type=Path)
        if name in ('trace','bgp'):command.add_argument('--target',required=True)
        if name in ('trace','return-route'):
            command.add_argument('--method',choices=('udp','icmp','tcp'),default='udp')
            command.add_argument('--tcp-port',type=int,default=443)
            command.add_argument('--max-hops',type=int,choices=range(1,65),default=30)
            command.add_argument('--geo',action='store_true',help=st('额外查询逐跳估计位置','Query estimated per-hop location'))
        if name=='return-route':command.add_argument('--family',type=int,choices=(4,6),default=4)
    args = parser.parse_args(remaining)
    if args.command in ('trace','return-route','bgp','cn-nodes'):
        from .console import Console
        from .session import ScanSession
        out=Console(lang,args.color)
        out.line(release_label(lang),'unknown')
        if args.json_output and (args.json_output.exists() or not args.json_output.parent.is_dir()):
            parser.error(st('输出文件已存在或目录不存在','Output already exists or directory is missing'))
        if hasattr(args,'tcp_port') and not 1<=args.tcp_port<=65535:parser.error(t('端口必须在 1～65535 之间'))
        if hasattr(args,'target'):
            try:target=ipaddress.ip_address(args.target)
            except ValueError:parser.error(st('目标必须是数字 IP 地址','Target must be a numeric IP address'))
            if args.command=='bgp' and not target.is_global:parser.error(st('BGP 需要公网 IP','BGP requires a public IP'))
        key={'trace':'route','return-route':'return_routes','bgp':'bgp','cn-nodes':'carrier_nodes'}[args.command]
        with ScanSession(key,args.json_output,lang) as scan:
            data=scan.report[key]
            if args.command=='trace':
                from .routes import trace_method,summarize_hops
                data.update(target=str(target),method=args.method,hops=[])
                code=trace_method(str(target),lambda line,**kw:out.line(line),method=args.method,tcp_port=args.tcp_port,
                                  hops=args.max_hops,geo=args.geo,lang=lang,records=data['hops'],on_result=scan.checkpoint,summary=data)
                data.update(statistics=summarize_hops(data['hops']))
                out.row(st('追踪结果','Trace result'),data['state']+(' / '+data['error_code'] if data.get('error_code') else ''),'ok' if code==0 else 'unknown')
            elif args.command=='return-route':
                from .carriers import return_routes
                out.line(st('方向：本机 → 中国目标；不包含中国侧到本机的探测','Direction: this host → China targets; reverse probes not included'),'unknown')
                return_routes(method=args.method,family=args.family,hops=args.max_hops,geo=args.geo,tcp_port=args.tcp_port,
                              destination=data,on_result=scan.checkpoint,out=out)
                code=0 if data['status']=='success' else 1
            elif args.command=='bgp':
                from .bgp import collect,render
                collect(str(target),data,scan.checkpoint);render(data,out)
                code=0 if data['status']=='success' else 1
            else:
                from .carriers import collect_nodes
                collect_nodes(data,scan.checkpoint,out)
                code=0 if data['status']=='success' else 1
                out.row(st('大陆三网覆盖','Mainland carrier coverage'),json.dumps(data['coverage']),'ok' if code==0 else 'unknown')
            if code:scan.report['result']='incomplete'
        sys.exit(1 if scan.failed else code)
    if args.command in ('report','recover'):
        from .reporting import load_report, export_report
        from .reports import recover_latest
        try:
            if args.command == 'report':
                document = load_report(args.input)
                format = 'markdown'
            else:
                document = recover_latest(args.journal)
                if document is None:
                    raise ValueError('No complete recovery event')
                document['recovery'] = {'kind':'last_complete_journal_snapshot','new_measurement':False}
                if document.get('result') in (None,'running'):
                    document['result'] = 'recovered_partial'
                format = args.format
            export_report(document,args.output,format=format,lang=lang)
        except (OSError,ValueError,TypeError,AttributeError,RecursionError):
            parser.error(st('导出失败：检查输入格式、读取上限与路径；输出文件必须不存在','Export failed: check input format, read limits and paths; output must not exist'))
        print(st('已保存脱敏报告；分享前请人工检查：','Redacted report saved; review before sharing: ')+str(args.output))
        sys.exit(0)
    if args.command == 'ipquality':
        from .ipquality import collect,render
        from .console import Console
        if args.json_output and (args.json_output.exists() or not args.json_output.parent.is_dir()):
            parser.error(st('输出文件已存在或目录不存在','Output already exists or directory is missing'))
        from .session import ScanSession
        with ScanSession('ip_quality',args.json_output,lang) as scan:
            result=collect(enrich=not args.no_enrichment,mail=args.mail_probes,
                           destination=scan.report['ip_quality'],on_result=scan.checkpoint)
            render(result,Console(lang,args.color),args.show_ip)
            incomplete=not result['coverage']['complete']
            if incomplete:scan.report['result']='incomplete'
        sys.exit(1 if incomplete or scan.failed else 0)
    if args.command == 'bandwidth':
        if not args.allow_bandwidth:
            parser.error(st('测速消耗流量和带宽；请添加 --allow-bandwidth 明确允许','Bandwidth tests use traffic and capacity; add --allow-bandwidth to consent'))
        from .bandwidth import run_console, is_complete
        if args.json_output and (args.json_output.exists() or not args.json_output.parent.is_dir()):
            parser.error(st('输出文件已存在或目录不存在','Output already exists or directory is missing'))
        from .session import ScanSession
        with ScanSession('bandwidth',args.json_output,lang) as scan:
            result=run_console(lang,args.color,args.rounds,args.sample_mib,args.source or (CHINA_SOURCES if args.china else None),
                               destination=scan.report['bandwidth'],on_result=scan.checkpoint)
            incomplete=not is_complete(result)
            if incomplete:scan.report['result']='incomplete'
        sys.exit(1 if incomplete or scan.failed else 0)
    if args.command == 'media':
        from .media import run_console
        if args.json_output and (args.json_output.exists() or not args.json_output.parent.is_dir()):
            parser.error(st('输出文件已存在或目录不存在','Output already exists or directory is missing'))
        print(st('流媒体可达性检测 · 不验证解锁或播放','Media reachability · Unlock and playback not tested'),flush=True)
        from .session import ScanSession
        with ScanSession('media',args.json_output,lang) as scan:
            run_console(lang,args.color,results=scan.report['media'],on_result=scan.checkpoint)
            incomplete=any(item.get('state')!='reachable' for item in scan.report['media'].values())
            if incomplete:scan.report['result']='incomplete'
        sys.exit(1 if incomplete or scan.failed else 0)
    if args.command in ('suite','all'):
        is_all=args.command=='all'
        if args.full and not is_all:parser.error('--full requires all')
        if is_all and args.allow_bandwidth and not args.full:parser.error('all bandwidth requires --full --allow-bandwidth')
        if is_all and args.full:
            args.mail_probes=True
            args.include_return_routes=True
        if is_all and args.allow_bandwidth:
            selected=args.bandwidth_source or (CHINA_SOURCES if args.china_speed else ('cloudflare','ovh'))
            if args.sample_mib*args.bandwidth_rounds*len(set(selected))*2>64:
                parser.error('all bandwidth payload budget is at most 64 MiB; reduce sources/sample size/rounds')
        if not 1<=args.tcp_port<=65535:parser.error(t('端口必须在 1～65535 之间'))
        if args.china_speed and not args.allow_bandwidth:
            parser.error(st('--china-speed 需要 --allow-bandwidth','--china-speed requires --allow-bandwidth'))
        if args.besttrace or args.region_script:
            parser.error(st('安全流程暂停第三方程序调用，请使用原生检测','External programs are disabled in the safe workflow; use native checks'))
        if not 1<=args.port<=65535: parser.error(t('端口必须在 1～65535 之间'))
        if args.json_output and args.json_output.exists():
            parser.error(st('输出文件已存在，请换一个文件名','Output already exists; choose another --json-output path'))
        if args.json_output and not args.json_output.parent.is_dir():
            parser.error(st('输出目录不存在','Output directory does not exist'))
        try:
            ipaddress.ip_address(args.route_target)
        except ValueError:
            parser.error(st('--route-target 必须是 IPv4 或 IPv6 地址','Invalid --route-target: use an IPv4 or IPv6 address'))
        try:
            code=run_suite(lang=lang,offline=args.offline,sample_mib=args.sample_mib,
                           route_target=args.route_target,besttrace=args.besttrace,region_script=args.region_script,
                           max_hops=args.max_hops,geo=not args.no_geo,color=args.color,
                           bandwidth_rounds=args.bandwidth_rounds,skip_route=args.skip_route,json_output=args.json_output,
                           bandwidth_sources=args.bandwidth_source or (CHINA_SOURCES if args.china_speed else None),port=args.port,show_ip=args.show_ip,ip_enrichment=not args.no_ip_enrichment,allow_bandwidth=args.allow_bandwidth,mail_probes=args.mail_probes,route_probes=args.route_probes,theme=args.theme,
                           route_method='udp' if is_all else args.route_method,tcp_port=args.tcp_port,include_return_routes=args.include_return_routes,include_bgp=args.include_bgp or is_all,show_unavailable=args.show_unavailable,
                           comprehensive=is_all,total_timeout=args.total_timeout or (600 if args.full else 300),module_timeout=args.module_timeout)
        except OSError:
            parser.error(st('无法保存报告，请检查输出目录和文件权限','Unable to save report; check the output directory and file permissions'))
        sys.exit(code)
    if args.command == 'quality':
        from .connectivity import run_console as run_connectivity
        from .session import ScanSession
        with ScanSession('network',None,lang) as scan:
            code=run_connectivity(lang=lang,color=args.color,report=scan.report['network'],on_result=scan.checkpoint)
            if code:scan.report['result']='incomplete'
        sys.exit(1 if scan.failed else code)
    if args.command == 'nodequality':
        parser.error(st('该第三方流程可能上传报告，当前安全版本已禁用；请使用 suite','This third-party workflow may upload reports and is disabled; use suite'))
        if not args.script.is_file():
            parser.error(t("找不到本地脚本文件"))
        bash = shutil.which('bash')
        if bash is None:
            parser.error(t("未找到 bash，无法运行脚本"))
        print(t("即将运行第三方 NodeQuality；其可能下载组件、进行网络及性能测试，并向第三方上传结果。输出可能包含公网 IP。"), flush=True)
        try:
            result = subprocess.run([bash, str(args.script.resolve())], check=False)
        except OSError:
            parser.error(t("无法启动 NodeQuality 脚本"))
        sys.exit(result.returncode if result.returncode >= 0 else 128 - result.returncode)
    if not 1 <= args.port <= 65535:
        parser.error(t("端口必须在 1～65535 之间"))
    if args.public_ip:
        try:
            ipaddress.ip_address(args.public_ip)
        except ValueError:
            parser.error(t("--public-ip 必须是有效 IPv4 或 IPv6 地址"))
    raw_data = inspect(port=args.port, public_ip=args.public_ip, lang=lang, detect_public_ip=args.detect_public_ip)
    from .resources import collect as collect_resources, render as render_resources
    try:
        raw_data['resources'] = collect_resources()
    except Exception:
        raw_data['resources'] = {'status': 'unknown', 'error_code': 'RESOURCE_MODULE_ERROR'}
    from .security import collect as collect_security, render as render_security
    try:
        raw_data['security'] = collect_security()
    except Exception:
        raw_data['security'] = {'status':'unknown','error_code':'SECURITY_MODULE_ERROR'}
    from .schema import normalize_report
    normalize_report(raw_data)
    safe_data = redact(raw_data, lang)
    data = raw_data if args.show_ip else safe_data
    serialized = json.dumps(safe_data, ensure_ascii=False, indent=2)
    if args.output:
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(serialized + "\n")
        except OSError as exc:
            parser.error(t("无法保存报告：{error}", error=exc))
    if args.as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        from .console import Console, can_render_cjk
        console = Console(lang, getattr(args, 'color', 'auto'))
        theme = getattr(args, 'theme', 'default')
        use_theme = theme in ('iprisk', 'framed')
        separator = ": " if lang == "en" else "："
        info_ids = {'system', 'architecture', 'kernel', 'cpu', 'memory_total', 'memory', 'disk_capacity', 'disk', 'interfaces', 'public_ip'}
        status_color = {'pass': 'ok', 'warn': 'bad', 'fail': 'bad', 'unknown': 'unknown', 'skip': 'unknown'}
        if theme == 'framed':
            console.frame_open(st('VPSMaster 检测报告','VPSMaster diagnostic report'), box_w=78, subtitle=release_label(lang) + ' · ' + __version__)
            # header key/values
            from datetime import datetime
            console.frame_keyvalue(st('扫描时间','Scan time'), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
            console.frame_keyvalue(st('语言','Language'), st('中文','English'))
            console.frame_keyvalue(st('模式','Mode'), st('只读体检','Read-only'))
            for number, (title, is_info) in enumerate(((st('服务器信息','Server information'), True), (st('体检结果','Diagnostic results'), False)), start=1):
                console.frame_section(number, title, title)
                for item in data["checks"]:
                    if item['id'] in ('memory_total','memory'):
                        continue
                    if (item['id'] in info_ids) != is_info:
                        continue
                    console.frame_keyvalue(item['title'], item['detail'], status_color.get(item['status'], 'unknown'))
                    for line in item["evidence"].splitlines():
                        console.frame_line(st('依据','Evidence') + separator + line, 'muted')
        elif theme == 'iprisk':
            console.banner('  VPSMaster  ' + ('v' + __version__))
            console.line(release_label(lang), 'unknown')
            console.keyvalue(st('只读体检报告','Read-only diagnostic report'),
                             st('已请求 ipify 查询出口 IP' if args.detect_public_ip else '默认不请求外部网络','ipify egress query' if args.detect_public_ip else 'no external requests by default'), 'title')
            console.hrule()
            for number, (title, is_info) in enumerate(((st('服务器信息','Server information'), True), (st('体检结果','Diagnostic results'), False)), start=1):
                console.theme_section(number, title, title, 'b_cyan')
                for item in data["checks"]:
                    if item['id'] in ('memory_total','memory'):
                        continue
                    if (item['id'] in info_ids) != is_info:
                        continue
                    console.keyvalue(item['title'], item['detail'], status_color.get(item['status'], 'unknown'))
                    for line in item["evidence"].splitlines():
                        print('      ' + console.paint(st('依据','Evidence'), 'muted') + separator + line, flush=True)
        else:
            print(release_label(lang) + f" · {__version__}\n" + t("只读体检 · 已请求 ipify 查询出口 IP" if args.detect_public_ip else "只读体检 · 默认不请求外部网络") + "\n")
            for heading, is_info in ((t('服务器信息'), True), (t('体检结果'), False)):
                print(f"{heading}:")
                for item in data["checks"]:
                    if item['id'] in ('memory_total','memory'):
                        continue
                    if (item['id'] in info_ids) != is_info:
                        continue
                    print(f"[{t(LABELS[item['status']])}] {item['title']}{separator}{item['detail']}")
                    for line in item["evidence"].splitlines():
                        print("  " + t("依据") + separator + line)
                print()
        counts = {t(label): sum(item["status"] == status for item in data["checks"])
                  for status, label in LABELS.items()}
        if data['resources']['status'] in ('partial','unsupported'):
            if console._framed:
                console.frame_section(3, '资源限制', 'Resource limits')
            render_resources(data['resources'], console)
        else:
            if console._framed:
                console.frame_line('RESOURCE_MODULE_ERROR', 'bad')
            else:
                print('RESOURCE_MODULE_ERROR')
        if data['security']['status'] in ('partial','unsupported'):
            if console._framed:
                console.frame_section(4, '安全与权限', 'Security & permissions')
            render_security(data['security'], console)
        else:
            if console._framed:
                console.frame_line('SECURITY_MODULE_ERROR', 'bad')
            else:
                print('SECURITY_MODULE_ERROR')
        if console._framed:
            summary = " / ".join(f"{key} {value}" for key, value in counts.items())
            console.frame_section(5, st('汇总','Summary'), 'Summary')
            summary_status = 'bad' if any(row['status'] in ('warn','fail') for row in data['checks']) or data['security'].get('review_count') else 'unknown' if any(row['status']=='unknown' for row in data['checks']) else 'ok'
            console.frame_line(summary, summary_status)
            console.frame_line(st('终端完整 IP；文件脱敏。','Full terminal IP; exports redacted.') if args.show_ip else t('报告默认隐藏 IP。'), 'muted')
            console.frame_close()
        else:
            print("\n" + " / ".join(f"{key} {value}" for key, value in counts.items()))
            print(st('终端完整 IP；文件脱敏。','Full terminal IP; exports redacted.') if args.show_ip else t('报告默认隐藏 IP。'))
    # Stable automation contract: 1 = findings, 2 = invalid usage or export error.
    return_code = 1 if any(item["status"] in {"warn", "fail"} for item in data["checks"]) or data['security'].get('review_count',0) else 0
    sys.exit(return_code)


def main():
    import os
    from .worker import reset,cancel_all
    previous=os.environ.get('PROXYDOCTOR_NETWORK_WORKERS')
    os.environ['PROXYDOCTOR_NETWORK_WORKERS']='1'
    reset()
    try:
        return _main()
    except KeyboardInterrupt:
        cancel_all()
        raise
    finally:
        if previous is None:os.environ.pop('PROXYDOCTOR_NETWORK_WORKERS',None)
        else:os.environ['PROXYDOCTOR_NETWORK_WORKERS']=previous
