"""Read-only checks. No shell, privilege escalation or system mutations."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import ipaddress
import json
import os
import platform
import re
from pathlib import Path
import shutil
import subprocess
import urllib.error
import urllib.request

from .i18n import translator
from . import __version__


@dataclass
class Result:
    id: str
    status: str
    title: str
    detail: str
    evidence: str = ""
    advice: str = ""


@dataclass
class Command:
    code: int | None
    output: str = ""
    reason: str = ""


# Only these fixed command arguments may reach subprocess.
ALLOWED = {
    ("ip", "-j", "address", "show"),
    ("ip", "-j", "-4", "route", "show", "default"),
    ("ip", "-j", "-6", "route", "show", "default"),
    ("ss", "-H", "-lntu"),
    ("sshd", "-T"),
    ("ufw", "status"),
    ("nft", "list", "ruleset"),
    ("iptables", "-S"),
    ("systemctl", "is-active", "sing-box.service"),
    ("systemctl", "is-enabled", "sing-box.service"),
}
SYSTEM_PATH = "/usr/sbin:/usr/bin:/sbin:/bin"
OUTPUT_LIMIT = 131072


class Host:
    def __init__(self, lang="zh"):
        self.lang = lang

    def system(self):
        return platform.system(), platform.machine()

    def read(self, path):
        try:
            return Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None

    def disk_free(self):
        return shutil.disk_usage("/").free

    def disk_total(self):
        return shutil.disk_usage("/").total

    def cpu_count(self):
        return os.cpu_count()

    def kernel(self):
        return platform.release()

    def ssh_connection(self):
        return os.environ.get("SSH_CONNECTION", "")

    def detect_public_ip(self):
        # Explicit opt-in; no environment proxies or redirects.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open('https://api64.ipify.org', timeout=5) as response:
                payload = response.read(129)
            if len(payload) > 128:
                return None
            address = ipaddress.ip_address(payload.decode('ascii').strip())
            return str(address) if address.is_global else None
        except (urllib.error.URLError, OSError, UnicodeError, ValueError):
            return None

    def run(self, *args):
        t = translator(self.lang)
        if args not in ALLOWED:
            raise ValueError("Command is not allowlisted")
        # Ignore the caller's PATH, especially when a user chooses to run as root.
        executable = shutil.which(args[0], path=SYSTEM_PATH)
        if executable is None and args[0] in {"sshd", "ufw", "nft", "iptables"}:
            for directory in ("/usr/sbin", "/sbin"):
                candidate = Path(directory) / args[0]
                if candidate.is_file():
                    executable = str(candidate)
                    break
        if executable is None:
            return Command(None, reason=t("命令不可用"))
        try:
            proc = subprocess.run(
                [executable, *args[1:]], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=8, check=False,
                env={"PATH": SYSTEM_PATH, "LC_ALL": "C"},
            )
            # Never return stderr: it can contain unrelated host details.
            if len(proc.stdout) > OUTPUT_LIMIT:
                return Command(None, reason=t("输出超过读取上限，不能作为完整检查结果"))
            return Command(proc.returncode, proc.stdout,
                           t("读取命令失败，可能是权限、配置或服务状态问题") if proc.returncode else "")
        except subprocess.TimeoutExpired:
            return Command(None, reason=t("读取超时（8 秒）"))
        except OSError:
            return Command(None, reason=t("无法执行读取命令"))


def parse_os(text):
    values = {}
    for line in (text or "").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    return values


def port_rows(text):
    """Parse ss -H -lntu without relying on process ownership visibility."""
    rows = []
    malformed = False
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 6 or fields[0] not in {"tcp", "udp"}:
            malformed = True
            continue
        endpoint = fields[4]
        try:
            port = int(endpoint.rsplit(":", 1)[1])
            if not 1 <= port <= 65535:
                raise ValueError("Invalid port")
        except (ValueError, IndexError):
            malformed = True
            continue
        rows.append((fields[0], endpoint, port))
    return rows, malformed


def ubuntu_version(value):
    """Parse VERSION_ID numerically; never infer Ubuntu from ID_LIKE."""
    if not re.fullmatch(r"[0-9]{2}\.(04|10)", value or ""):
        return None
    return tuple(int(part) for part in value.split("."))


def route_check(host, t):
    evidence, valid, failed = [], 0, False
    for family in ("-4", "-6"):
        result = host.run("ip", "-j", family, "route", "show", "default")
        try:
            if result.code != 0:
                raise ValueError
            routes = json.loads(result.output)
            if not isinstance(routes, list):
                raise ValueError
            for route in routes:
                if not isinstance(route, dict) or route.get("dst") not in ("default", "0.0.0.0/0", "::/0"):
                    raise ValueError
                if route.get("type", "unicast") != "unicast":
                    continue
                dev = route.get("dev")
                gateway = route.get("gateway")
                if not isinstance(dev, str) or not dev or (gateway is not None and not isinstance(gateway, str)):
                    raise ValueError
                if gateway is not None:
                    address = ipaddress.ip_address(gateway)
                    if address.version != (4 if family == "-4" else 6):
                        raise ValueError
                evidence.append(f"IPv{family[-1]}: {dev}" + (f" via {gateway}" if gateway else ""))
                valid += 1
        except (ValueError, TypeError, KeyError):
            failed = True
            evidence.append(f"IPv{family[-1]}: " + t("路由读取失败或格式无法解析"))
    return Result("default_route", "pass" if valid and not failed else "unknown", t("默认路由"),
                  t("已读取默认路由；不代表互联网或目标地址可达") if valid and not failed else
                  t("默认路由信息不完整或未找到，无法确认网络出口"), "\n".join(evidence),
                  t("仅检查当前网络命名空间的默认路由，不覆盖策略路由。"))


def dns_check(host, t):
    content = host.read("/etc/resolv.conf")
    if content is None:
        return Result("dns_config", "unknown", t("DNS 配置"), t("无法读取 DNS 配置"))
    addresses, invalid = [], False
    for line in content.splitlines():
        line = line.split("#", 1)[0].split(";", 1)[0].strip()
        fields = line.split()
        if fields and fields[0] == "nameserver":
            if len(fields) != 2:
                invalid = True
                continue
            try:
                address = ipaddress.ip_address(fields[1])
                if address.is_unspecified or address.is_multicast:
                    raise ValueError
                addresses.append(address)
            except ValueError:
                invalid = True
    evidence = "\n".join(str(addr) for addr in addresses)
    stub = any(addr.is_loopback for addr in addresses)
    status = "unknown" if invalid or not addresses or stub else "pass"
    detail = (t("DNS 配置不完整或没有有效的服务器地址") if invalid or not addresses else
              t("DNS 指向本机解析器；上游配置及解析是否成功尚未验证") if stub else
              t("已读取 DNS 服务器配置；尚未验证解析是否成功"))
    return Result("dns_config", status, t("DNS 配置"), detail, evidence,
                  t("仅检查 resolv.conf，不主动发送 DNS 请求；实际解析路径可能不同。"))


def ssh_port_check(host, ssh, port, t):
    configured, malformed = [], False
    if ssh.code == 0:
        for line in ssh.output.splitlines():
            fields = line.split()
            if fields and fields[0] == "port":
                try:
                    if len(fields) != 2 or not 1 <= int(fields[1]) <= 65535:
                        raise ValueError
                    configured.append(int(fields[1]))
                except ValueError:
                    malformed = True
    try:
        session = host.ssh_connection()
    except AttributeError:
        session = ""
    session_port = None
    if session:
        try:
            fields = session.split()
            if len(fields) != 4:
                raise ValueError
            ipaddress.ip_address(fields[0]); ipaddress.ip_address(fields[2])
            if not 1 <= int(fields[1]) <= 65535 or not 1 <= int(fields[3]) <= 65535:
                raise ValueError
            session_port = int(fields[3])
        except ValueError:
            session_port = None
    evidence = []
    if configured:
        evidence.append(t("sshd 默认配置端口：{ports}", ports=", ".join(map(str, sorted(set(configured))))))
    if session_port is not None:
        evidence.append(t("当前 SSH 会话本地端口：{port}", port=session_port))
    matched = port in configured or port == session_port
    detail = t("目标端口与 SSH 已知端口冲突；不要用于代理") if matched else t("未能排除与运行中 SSH 端口冲突")
    advice = t("检查运行中 SSH、socket 激活及自定义实例；证据不足时不要进行端口或防火墙修改。")
    if malformed:
        evidence.append(t("SSH 端口输出不完整或无效"))
    return Result("ssh_port_safety", "warn" if matched else "unknown", t("SSH 端口保护"), detail, "\n".join(evidence), advice)


def inspect(host=None, port=8388, public_ip=None, lang="zh", detect_public_ip=False):
    t = translator(lang)
    host = host or Host(lang)
    results = []
    add = results.append
    system, arch = host.system()
    os_info = parse_os(host.read("/etc/os-release")) if system == "Linux" else {}
    version = ubuntu_version(os_info.get("VERSION_ID"))
    is_ubuntu = os_info.get("ID") == "ubuntu"
    supported = is_ubuntu and version is not None and version >= (22, 4)
    os_unknown = system == "Linux" and not os_info.get("ID")
    version_unknown = is_ubuntu and version is None
    add(Result("system", "pass" if supported else "unknown" if version_unknown or os_unknown else "warn", t("操作系统"),
               t("版本符合 Ubuntu 22.04 最低要求；不代表已完成实机兼容验证") if supported else
               t("无法读取 Linux 发行版标识，不能确认系统要求") if os_unknown else
               t("无法解析 Ubuntu 版本，不能确认是否符合最低要求") if version_unknown else t("需要 Ubuntu 22.04 或更新版本"),
               f"{system}; {os_info.get('PRETTY_NAME', t('版本未知'))}; {arch}",
               t("版本检查不验证官方维护状态；Ubuntu 22.04 及更新版本仍需分别进行实机测试。") if supported else
               t("其他系统的结果仅供参考；请使用 Ubuntu 22.04 或更新版本验证。")))
    add(Result("architecture", "pass" if arch.lower() in {"x86_64", "amd64", "aarch64", "arm64"} else "unknown",
               t("系统架构"), t("检测架构；本阶段不验证安装包兼容性"), arch))
    try:
        count = host.cpu_count()
    except (AttributeError, OSError):
        count = None
    cpuinfo = host.read('/proc/cpuinfo') if system == 'Linux' else None
    model = next((line.split(':', 1)[1].strip() for line in (cpuinfo or '').splitlines()
                  if line.split(':', 1)[0].strip() in ('model name', 'Hardware') and ':' in line), None)
    add(Result('cpu', 'pass' if count else 'unknown', t('CPU 信息'),
               t('系统可见逻辑 CPU：{count}', count=count) if count else t('逻辑 CPU 数量未知'),
               t('处理器型号：{model}', model=model) if model else t('处理器型号未知'),
               t('逻辑 CPU 数不一定等于物理核心数；配额限制可能不同。')))
    try:
        kernel = host.kernel()
    except (AttributeError, OSError):
        kernel = None
    add(Result('kernel', 'pass' if kernel else 'unknown', t('内核版本'), kernel or t('无法读取')))
    try:
        free = host.disk_free() / 1024**3
        add(Result("disk", "pass" if free >= 1 else "warn", t("根分区可用空间"),
                   t("可用 {free:.1f} GiB（体检提示阈值 1 GiB，不代表完整安装要求）", free=free)))
    except OSError:
        add(Result("disk", "unknown", t("根分区可用空间"), t("无法读取")))
    try:
        total, free = host.disk_total() / 1024**3, host.disk_free() / 1024**3
        add(Result('disk_capacity', 'pass', t('根分区容量'),
                   t('总容量 {total:.1f} GiB，可用 {free:.1f} GiB', total=total, free=free),
                   advice=t('这是根文件系统容量，不一定等于 VPS 购买的磁盘总容量。')))
    except (AttributeError, OSError):
        add(Result('disk_capacity', 'unknown', t('根分区容量'), t('无法读取')))
    if public_ip and detect_public_ip:
        raise ValueError("public_ip and detect_public_ip are mutually exclusive")
    if detect_public_ip:
        address = host.detect_public_ip()
        add(Result("public_ip", "unknown", t("公网 IP"),
                   t("已通过 ipify 查询出口地址；未验证入站可达性或归属") if address else t("出口 IP 查询失败，无法确定公网地址"),
                   address or "", t("出口地址可能是 NAT 或代理地址；不是入站可达性证明。")))
    elif public_ip:
        addr = ipaddress.ip_address(public_ip)
        add(Result("public_ip", "unknown" if addr.is_global else "warn", t("公网 IP"),
                   t("用户提供的地址具备公网地址属性，但未验证归属或可达性") if addr.is_global else t("提供的地址不是全局可路由公网地址"),
                   str(addr)))
    else:
        add(Result("public_ip", "unknown", t("公网 IP"), t("默认不向第三方查询出口 IP"),
                   advice=t("可用 --public-ip 填写云控制台地址；地址归属及入站可达性仍需外部验证。")))
    add(Result("cloud_firewall", "unknown", t("云防火墙与外部可达性"),
               t("本机读取不能确认云安全组、NAT 或外部网络路径"),
               advice=t("后续从客户端独立测试；不能仅据此认定端口已开放或被封锁。")))
    if system != "Linux":
        for key, title in (("memory", t("内存")), ("interfaces", t("网络地址")),
                           ("default_route", t("默认路由")), ("dns_config", t("DNS 配置")),
                           ("ports", t("端口占用")), ("ssh", t("SSH 配置")),
                           ("ssh_port_safety", t("SSH 端口保护")),
                           ("firewall", t("本机防火墙")), ("service", t("sing-box 服务")),
                           ("service_startup", t("sing-box 开机启动"))):
            add(Result(key, "skip", title, t("此项需要 Linux；当前主机仅验证程序运行")))
        return report(results, port, lang)
    memory = host.read("/proc/meminfo")
    total_line = next((line for line in (memory or '').splitlines() if line.startswith('MemTotal:')), '')
    try:
        total_mib = int(total_line.split()[1]) / 1024
        add(Result('memory_total', 'pass', t('内存总量'), t('系统可见 {total:.0f} MiB', total=total_mib),
                   advice=t('系统可见内存可能与商家标称或容器限额不同。')))
    except (ValueError, IndexError):
        add(Result('memory_total', 'unknown', t('内存总量'), t('无法读取')))
    available = next((line for line in (memory or "").splitlines() if line.startswith("MemAvailable:")), "")
    try:
        mib = int(available.split()[1]) / 1024
        add(Result("memory", "pass" if mib >= 256 else "warn", t("可用内存"),
                   t("约 {mib:.0f} MiB（体检提示阈值 256 MiB，不代表完整安装要求）", mib=mib)))
    except (ValueError, IndexError):
        add(Result("memory", "unknown", t("可用内存"), t("无法读取 MemAvailable")))
    network = host.run("ip", "-j", "address", "show")
    try:
        interfaces = json.loads(network.output) if network.code == 0 else None
        addresses = [f"{item['ifname']}: {addr['local']}" for item in interfaces
                     for addr in item.get("addr_info", []) if addr.get("scope") != "host"]
        add(Result("interfaces", "pass" if addresses else "unknown", t("网络地址"),
                   t("仅表示本机接口地址；不证明互联网可达"), "\n".join(addresses)))
    except (TypeError, ValueError, KeyError, AttributeError):
        add(Result("interfaces", "unknown", t("网络地址"), t(network.reason) or t("无法解析接口信息")))
    add(route_check(host, t))
    add(dns_check(host, t))
    ports = host.run("ss", "-H", "-lntu")
    rows, malformed = port_rows(ports.output)
    conflicts = [f"{proto} {endpoint}" for proto, endpoint, number in rows if number == port]
    add(Result("ports", "warn" if conflicts else "unknown" if ports.code != 0 or malformed else "pass",
               t("目标端口占用"), t("目标 TCP/UDP 端口 {port} 已有监听", port=port) if conflicts else
               t("无法完整确认端口占用") if ports.code != 0 or malformed else t("当前未发现 TCP/UDP 端口 {port} 的监听；不保证之后绑定成功", port=port),
               "\n".join(conflicts), t("选择未占用端口；不会停止已有服务。") if conflicts else ""))
    ssh = host.run("sshd", "-T")
    add(ssh_port_check(host, ssh, port, t))
    # Only retain selected settings, never dump full ssh configuration.
    settings = dict(line.split(None, 1) for line in ssh.output.splitlines() if len(line.split(None, 1)) == 2)
    selected = {key: settings[key] for key in ("port", "permitrootlogin", "passwordauthentication", "pubkeyauthentication") if key in settings}
    risk = settings.get("permitrootlogin") == "yes" or settings.get("passwordauthentication") == "yes"
    ssh_complete = all(key in settings for key in ("permitrootlogin", "passwordauthentication"))
    add(Result("ssh", "unknown" if ssh.code != 0 else "warn" if risk else "unknown", t("SSH 配置"),
               (t(ssh.reason) or t("读取失败")) if ssh.code != 0 else t("允许 root 登录或密码认证，建议人工审阅") if risk else
               t("SSH 输出缺少关键字段，无法完成风险判断") if not ssh_complete else t("未发现这两项宽松设置；不能据此认定 SSH 安全"),
               "\n".join(line for line in ssh.output.splitlines() if line.split() and line.split()[0] in selected) if ssh.code == 0 else "",
               t("sshd -T 读取默认配置；权限不足、配置错误或 SSH 运行目录尚未创建均可能导致失败。结果可能与运行中服务或 Match 条件不同；不自动修改 SSH。")))
    firewall = []
    any_rules = False
    complete = True
    for args in (("ufw", "status"), ("nft", "list", "ruleset"), ("iptables", "-S")):
        cmd = host.run(*args)
        if cmd.code != 0:
            complete = False
            firewall.append(f"{args[0]}: {t(cmd.reason) or t('读取失败')}")
        else:
            meaningful = bool(cmd.output.strip()) and not cmd.output.strip().startswith("Status: inactive")
            any_rules |= meaningful
            firewall.append(f"{args[0]}: " + t("已读取；") + (t("存在状态或规则信息") if meaningful else t("未发现活动状态或规则")))
    add(Result("firewall", "unknown", t("本机防火墙"),
               t("发现防火墙状态或规则；未判断规则是否允许目标端口") if any_rules else t("没有足够证据确认防火墙保护状态"),
               "\n".join(firewall), t("部分工具不可用或权限不足。") if not complete else t("规则存在不等于配置安全。")))
    active = host.run("systemctl", "is-active", "sing-box.service")
    enabled = host.run("systemctl", "is-enabled", "sing-box.service")
    running = active.code == 0 and active.output.strip() == "active"
    failed = active.output.strip() == "failed"
    add(Result("service", "warn" if failed else "pass" if running else "unknown", t("sing-box 服务"),
               t("sing-box 服务处于 failed 状态，需要检查启动失败原因") if failed else
               t("服务处于 active；不代表代理连接成功") if running else t("未确认 sing-box 服务运行；新系统尚未安装属于正常情况"),
               f"active: {active.output.strip() or t(active.reason)}\nenabled: {enabled.output.strip() or t(enabled.reason)}"))
    startup = enabled.output.strip()
    startup_ok = enabled.code == 0 and startup == "enabled"
    startup_warn = startup in {"disabled", "masked", "enabled-runtime", "masked-runtime"}
    add(Result("service_startup", "pass" if startup_ok else "warn" if startup_warn else "unknown",
               t("sing-box 开机启动"), t("已配置持久开机启动；尚未实际重启验证") if startup_ok else
               t("未配置持久开机启动或服务被屏蔽，重启后可能不可用") if startup_warn else
               t("无法确认 sing-box 的持久开机启动状态"), startup or t(enabled.reason)))
    return report(results, port, lang)


def report(results, port, lang="zh"):
    return {"schema_version": 1, "language": lang, "tool_version": __version__,
            "generated_at": datetime.now(timezone.utc).isoformat(), "mode": "read-only",
            "target_port": port, "checks": [asdict(result) for result in results]}
