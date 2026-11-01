import argparse
import ipaddress
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from . import __version__
from .checks import inspect
from .i18n import translator
from .quality import run_quality
from .suite import run_suite
from .bandwidth import SOURCES


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


def main():
    # Support Windows consoles that cannot encode Chinese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    # Discover language before building help/errors. --lang works on either side of check.
    language_parser = argparse.ArgumentParser(add_help=False)
    language_parser.add_argument("--lang", choices=("zh", "en"), default="zh")
    language_args, remaining = language_parser.parse_known_args()
    lang = language_args.lang
    t = translator(lang)
    parser = LocalizedParser(lang=lang, description=("ProxyDoctor 只读体检：check 默认离线；suite 会联网" if lang=='zh' else 'ProxyDoctor read-only diagnostics: check defaults offline; suite contacts external services'))
    parser.add_argument("--version", action="version", version=__version__, help=t("显示版本并退出"))
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
    node = sub.add_parser("nodequality", lang=lang, help=t("运行本地 NodeQuality 脚本并实时显示输出"))
    node.add_argument("--lang", choices=("zh", "en"), default=lang, help=t("界面和报告语言：zh 中文，en 英文（默认 zh）"))
    node.add_argument("--script", type=Path, required=True, help=t("已下载并检查的 NodeQuality 脚本路径"))
    quality = sub.add_parser('quality', lang=lang, help=t('联网检测 DNS 和 TCP 连接并实时显示结果'))
    quality.add_argument('--lang', choices=('zh','en'), default=lang, help=t('界面和报告语言：zh 中文，en 英文（默认 zh）'))
    st=lambda zh,en: zh if lang=='zh' else en
    ipq = sub.add_parser('ipquality',lang=lang,help=st('只查询 IP 归属与风险，按来源保留证据','Query IP ownership and provider-specific risk evidence'))
    ipq.add_argument('--lang',choices=('zh','en'),default=lang)
    ipq.add_argument('--color',choices=('auto','always','never'),default='auto')
    ipq.add_argument('--show-ip',action='store_true',help=st('终端显示出口 IP；文件仍脱敏','Show egress IP in terminal; exports stay redacted'))
    ipq.add_argument('--no-enrichment',action='store_true',help=st('不查询额外免密钥来源','Skip additional keyless sources'))
    ipq.add_argument('--json-output',type=Path)
    bandwidth = sub.add_parser('bandwidth',lang=lang,help=st('仅运行多来源多轮测速','Run only repeated multi-source bandwidth tests'))
    bandwidth.add_argument('--lang',choices=('zh','en'),default=lang)
    bandwidth.add_argument('--color',choices=('auto','always','never'),default='auto')
    bandwidth.add_argument('--sample-mib',type=int,choices=range(1,21),default=4,metavar='1..20')
    bandwidth.add_argument('--rounds','--bandwidth-rounds',type=int,choices=range(3,9),default=3,metavar='3..8')
    bandwidth.add_argument('--source','--bandwidth-source',choices=tuple(SOURCES),action='append',help=st('可重复指定；默认 Cloudflare + OVHcloud','Repeat to select; default Cloudflare + OVHcloud'))
    bandwidth.add_argument('--json-output',type=Path,help=st('保存脱敏检测依据，不覆盖文件','Save redacted evidence; never overwrite'))
    media = sub.add_parser('media',lang=lang,help=st('仅检测流媒体，不重复测速','Check media without repeating bandwidth tests'))
    media.add_argument('--lang',choices=('zh','en'),default=lang)
    media.add_argument('--color',choices=('auto','always','never'),default='auto')
    media.add_argument('--json-output',type=Path,help=st('保存脱敏检测依据，不覆盖文件','Save redacted evidence; never overwrite'))
    suite = sub.add_parser('suite',lang=lang,help=st('VPS / 网络质量 / 路由 / 流媒体','VPS / network / routes / streaming'))
    suite.add_argument('--lang',choices=('zh','en'),default=lang)
    suite.add_argument('--offline',action='store_true',help=st('跳过联网检测','Skip outbound requests'))
    suite.add_argument('--port',type=int,default=8388,help=st('体检目标端口，默认 8388','Target port to inspect (default 8388)'))
    suite.add_argument('--show-ip',action='store_true',help=st('终端显示出口 IP；文件仍脱敏','Show egress IP in terminal; exports stay redacted'))
    suite.add_argument('--no-ip-enrichment',action='store_true',help=st('不查询额外 IP 风险来源','Skip additional IP risk sources'))
    suite.add_argument('--sample-mib',type=int,choices=range(1,21),default=4,metavar='1..20',help=st('每轮每方向 MiB，默认 4','MiB per round per direction (default 4)'))
    suite.add_argument('--bandwidth-rounds',type=int,choices=range(3,9),default=3,metavar='3..8',help=st('每方向测速轮数，默认 3','Measured rounds per direction (default 3)'))
    suite.add_argument('--bandwidth-source',choices=tuple(SOURCES),action='append',help=st('可重复指定；默认 Cloudflare + OVHcloud','Repeat to select; default Cloudflare + OVHcloud'))
    suite.add_argument('--skip-route',action='store_true',help=st('跳过路由追踪','Skip route trace'))
    suite.add_argument('--json-output',type=Path,help=st('保存脱敏检测依据，不覆盖文件','Save redacted evidence; never overwrite'))
    suite.add_argument('--route-target',default='1.1.1.1',help=st('路由目标，IPv4 或 IPv6 地址','Numeric IPv4 or IPv6 route destination'))
    suite.add_argument('--besttrace',type=Path,help=st('本地 BestTrace 可执行文件','Local BestTrace executable'))
    suite.add_argument('--region-script',type=Path,help=st('已审阅的本地 RegionRestrictionCheck 脚本','Reviewed local RegionRestrictionCheck script'))
    suite.add_argument('--max-hops',type=int,choices=range(1,65),default=30,metavar='1..64')
    suite.add_argument('--no-geo',action='store_true',help=st('不查询路由 IP 位置','Skip route IP geolocation lookups'))
    suite.add_argument('--color',choices=('auto','always','never'),default='auto')
    args = parser.parse_args(remaining)
    if args.command == 'ipquality':
        from .ipquality import collect,render
        from .console import Console
        if args.json_output and (args.json_output.exists() or not args.json_output.parent.is_dir()):
            parser.error(st('输出文件已存在或目录不存在','Output already exists or directory is missing'))
        result=collect(enrich=not args.no_enrichment)
        render(result,Console(lang,args.color),args.show_ip)
        print(st('第三方记录可能缺失或不一致；不同评分不可合并；无举报不保证安全。',
                 'Provider records may be missing or disagree; scores are not interchangeable; zero reports do not guarantee safety.'),flush=True)
        if args.json_output:
            try:
                with args.json_output.open('x',encoding='utf-8') as stream:
                    json.dump(redact({'tool_version':__version__,'ip_quality':result},lang),stream,ensure_ascii=False,indent=2)
            except OSError: parser.error(st('无法保存报告','Unable to save report'))
        sys.exit(0 if result['coverage']['complete'] else 1)
    if args.command == 'bandwidth':
        from .bandwidth import run_console, is_complete
        if args.json_output and (args.json_output.exists() or not args.json_output.parent.is_dir()):
            parser.error(st('输出文件已存在或目录不存在','Output already exists or directory is missing'))
        result=run_console(lang,args.color,args.rounds,args.sample_mib,args.source)
        print(st('说明：不同来源分别统计；只支持下载的来源不测上传；HTTPS 吞吐包含建连，不能认定线路容量。',
                 'Notes: sources are summarized separately; download-only sources do not upload. HTTPS throughput includes setup and does not establish line capacity.'),flush=True)
        if args.json_output:
            try:
                with args.json_output.open('x',encoding='utf-8') as stream:
                    json.dump(redact({'tool_version':__version__,'bandwidth':result},lang),stream,ensure_ascii=False,indent=2)
            except OSError:
                parser.error(st('无法保存报告','Unable to save report'))
        sys.exit(0 if is_complete(result) else 1)
    if args.command == 'media':
        from .media import run_console
        if args.json_output and (args.json_output.exists() or not args.json_output.parent.is_dir()):
            parser.error(st('输出文件已存在或目录不存在','Output already exists or directory is missing'))
        print(st('流媒体地区检测 · 未登录，不验证账号播放','Media region checks · Anonymous; account playback not tested'),flush=True)
        results=run_console(lang,args.color)
        if args.json_output:
            try:
                with args.json_output.open('x',encoding='utf-8') as stream:
                    json.dump(redact({'tool_version':__version__,'media':results},lang),stream,ensure_ascii=False,indent=2)
            except OSError:
                parser.error(st('无法保存报告','Unable to save report'))
        sys.exit(1)  # Playback entitlement remains untested.
    if args.command == 'suite':
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
                           bandwidth_sources=args.bandwidth_source,port=args.port,show_ip=args.show_ip,ip_enrichment=not args.no_ip_enrichment)
        except OSError:
            parser.error(st('无法保存报告，请检查输出目录和文件权限','Unable to save report; check the output directory and file permissions'))
        sys.exit(code)
    if args.command == 'quality':
        sys.exit(run_quality(t))
    if args.command == 'nodequality':
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
        print(f"ProxyDoctor {__version__} · " + t("只读体检 · 已请求 ipify 查询出口 IP" if args.detect_public_ip else "只读体检 · 默认不请求外部网络") + "\n")
        separator = ": " if lang == "en" else "："
        info_ids = {'system', 'architecture', 'kernel', 'cpu', 'memory_total', 'memory', 'disk_capacity', 'disk', 'interfaces', 'public_ip'}
        for heading, is_info in ((t('服务器信息'), True), (t('体检结果'), False)):
            print(f"{heading}:")
            for item in data["checks"]:
                if (item['id'] in info_ids) != is_info:
                    continue
                print(f"[{t(LABELS[item['status']])}] {item['title']}{separator}{item['detail']}")
                for line in item["evidence"].splitlines():
                    print("  " + t("依据") + separator + line)
                if item["advice"]:
                    print("  " + t("建议") + separator + item['advice'])
            print()
        counts = {t(label): sum(item["status"] == status for item in data["checks"])
                  for status, label in LABELS.items()}
        print("\n" + " / ".join(f"{key} {value}" for key, value in counts.items()))
        print(t("终端正在显示完整 IP；保存的报告仍脱敏，分享前请检查内容。" if args.show_ip else "报告默认隐藏 IP；分享前请检查内容。通过某一项不代表整体安全或代理可用。"))
    # Stable automation contract: 1 = findings, 2 = invalid usage or export error.
    return_code = 1 if any(item["status"] in {"warn", "fail"} for item in data["checks"]) else 0
    sys.exit(return_code)
