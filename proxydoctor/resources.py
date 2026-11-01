"""Read-only Linux resources; numeric results independent of terminal language."""
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import time

from .reports import utc_now


def read_text(path):
    try:
        with Path(path).open(encoding='utf-8') as stream:
            value = stream.read(262145)
        return value if len(value) <= 262144 else None
    except (OSError, UnicodeError):
        return None


def number(value):
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else None
    except (ValueError, TypeError):
        return None


def meminfo(text):
    result = {}
    for line in (text or '').splitlines():
        match = re.fullmatch(r'(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+(\d+) kB', line)
        if match:
            result[match[1]] = int(match[2]) * 1024
    return result


def pressure(text):
    result = {}
    for line in (text or '').splitlines():
        fields = line.split()
        if not fields or fields[0] not in ('some', 'full'):
            continue
        try:
            values = dict(item.split('=', 1) for item in fields[1:])
            row = {key: float(values[key]) for key in ('avg10','avg60','avg300')}
            row['total_us'] = int(values['total'])
            if all(math.isfinite(row[key]) and 0 <= row[key] <= 100 for key in ('avg10','avg60','avg300')) and row['total_us'] >= 0:
                result[fields[0]] = row
        except (KeyError, ValueError):
            continue
    return result or None


def cpu_ticks(text):
    line = next((line for line in (text or '').splitlines() if line.startswith('cpu ')), '')
    try:
        values = [int(value) for value in line.split()[1:]]
        # Guest and guest_nice are already included in user and nice.
        return values[:8] if len(values) >= 8 and all(value >= 0 for value in values) else None
    except ValueError:
        return None


def steal_delta(before, after):
    if before is None or after is None:
        return None
    deltas = [b-a for a,b in zip(before,after)]
    total = sum(deltas)
    return round(100*deltas[7]/total, 3) if total > 0 and all(value >= 0 for value in deltas) else None


def unescape_mount(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)


def cgroup_locations(membership, mounts, controller):
    """Map process membership onto visible mount roots, including ancestors.

    Hidden namespace ancestors cannot be inspected; never infer unlimited host
    resources from the visible root. Limit traversal to 64 visible ancestors.
    """
    memberships = []
    for line in (membership or '').splitlines():
        parts = line.split(':', 2)
        if len(parts) == 3 and (parts[0] == '0' or controller in parts[1].split(',')):
            memberships.append((parts[0] == '0', parts[2]))
    for line in (mounts or '').splitlines():
        left, separator, right = line.partition(' - ')
        fields, info = left.split(), right.split()
        if not separator or len(fields) < 6 or len(info) < 3 or info[0] not in ('cgroup','cgroup2'):
            continue
        v2 = info[0] == 'cgroup2'
        if not v2 and controller not in info[2].split(','):
            continue
        mount_root, mount = (PurePosixPath(unescape_mount(fields[index])) for index in (3,4))
        for unified, member in memberships:
            path = PurePosixPath(member)
            if unified != v2 or not path.is_absolute() or '..' in path.parts or '..' in mount.parts:
                continue
            try:
                relative = path.relative_to(mount_root)
            except ValueError:
                continue
            current = mount / relative
            for _ in range(64):
                yield v2, str(current)
                if current == mount:
                    break
                current = current.parent


def cgroup_limits(read):
    membership, mounts = read('/proc/self/cgroup'), read('/proc/self/mountinfo')
    result = {'cpu_quota_cores': None, 'memory_limit_bytes': None,
              'observations': [], 'scope': 'visible_cgroup_ancestors_only'}
    for controller in ('cpu','memory'):
        for v2, directory in cgroup_locations(membership, mounts, controller):
            leaf = ('cpu.max' if v2 else 'cpu.cfs_quota_us') if controller == 'cpu' else ('memory.max' if v2 else 'memory.limit_in_bytes')
            source = directory + '/' + leaf
            raw = read(source)
            if raw is None:
                continue
            value = None
            state = 'unknown'
            if controller == 'cpu':
                tokens = raw.split()
                quota = tokens[0] if tokens else ''
                period = number(tokens[1] if v2 and len(tokens) == 2 else read(directory+'/cpu.cfs_period_us'))
                if quota == ('max' if v2 else '-1'):
                    state = 'no_visible_limit'
                elif number(quota) is not None and number(quota) > 0 and period:
                    value = int(quota)/period
                    state = 'measured'
                key = 'cpu_quota_cores'
            else:
                value = number(raw.strip())
                if raw.strip() == 'max' or (not v2 and value is not None and value >= 2**60):
                    value = None
                    state = 'no_visible_limit'
                elif value is not None:
                    state = 'measured'
                key = 'memory_limit_bytes'
            result['observations'].append({'source': source, 'status': state, 'value': value,
                                           'controller': controller, 'version': 2 if v2 else 1})
            if value is not None:
                prior = result[key]
                result[key] = value if prior is None else min(value, prior)
    return result


def collect(read=read_text, *, interval=0.2, sleep=time.sleep, clock=time.monotonic,
            system=None, cpu_count=os.cpu_count, affinity=None):
    if not 0.05 <= interval <= 1:
        raise ValueError('Resource observation interval must be 0.05..1 seconds')
    report = {'schema_version': 1, 'observed_at': utc_now(), 'method': 'linux_readonly_snapshot',
              'status': 'unsupported', 'metrics': {}, 'limitations': [
                  'Visible resources and cgroup limits are not purchased specifications or dedicated capacity.',
                  'Hidden ancestor limits cannot be excluded; steal/PSI describe a short observation, not long-term contention.',
                  'Host-visible PSI/meminfo/CPU counters may differ from container scope.']}
    if (system or platform.system()) != 'Linux':
        return report
    memory = meminfo(read('/proc/meminfo'))
    limits = cgroup_limits(read)
    container_markers = [path for path in ('/.dockerenv','/run/.containerenv','/run/systemd/container')
                         if read(path) is not None]
    try:
        visible = cpu_count()
    except OSError:
        visible = None
    try:
        allowed = len(affinity() if affinity else os.sched_getaffinity(0))
    except (OSError, AttributeError):
        allowed = None
    bounds = [v for v in (visible, allowed, limits['cpu_quota_cores']) if v is not None and v > 0]
    ram = [v for v in (memory.get('MemTotal'), limits['memory_limit_bytes']) if v is not None]
    before = cpu_ticks(read('/proc/stat'))
    started = clock()
    sleep(interval)  # Passive observation, no CPU workload or benchmark.
    after = cpu_ticks(read('/proc/stat'))
    elapsed = clock()-started
    swap_total, swap_free = memory.get('SwapTotal'), memory.get('SwapFree')
    metrics = {'logical_cpus': visible, 'affinity_cpus': allowed,
               'visible_cpu_upper_bound_cores': min(bounds) if bounds else None,
               'memory_total_bytes': memory.get('MemTotal'),
               'memory_available_bytes': memory.get('MemAvailable'),
               'visible_memory_upper_bound_bytes': min(ram) if ram else None,
               'swap_total_bytes': swap_total, 'swap_free_bytes': swap_free,
               'swap_used_bytes': swap_total-swap_free if swap_total is not None and swap_free is not None and swap_free <= swap_total else None,
               'steal_percent': steal_delta(before, after), 'sample_elapsed_seconds': round(elapsed, 4),
               'pressure': {kind: pressure(read('/proc/pressure/'+kind)) for kind in ('cpu','memory','io')}}
    current = next((row for row in limits['observations'] if row['controller'] == 'memory'), None)
    metrics['cgroup_memory_current_bytes'] = number(read(current['source'].rsplit('/',1)[0] +
                                                        ('/memory.current' if current['version'] == 2 else '/memory.usage_in_bytes'))) if current else None
    # Keep allocation evidence distinct from the underlying OS view. No local
    # observation can certify provider-side CPU exclusivity or reservation.
    report['allocation'] = {
        'cpu_limit_cores': metrics['visible_cpu_upper_bound_cores'],
        'cpu_basis': 'affinity_and_visible_quota' if limits['cpu_quota_cores'] is not None else 'visible_cpu_and_affinity_only',
        'memory_limit_bytes': limits['memory_limit_bytes'] if limits['memory_limit_bytes'] is not None else
                              None if container_markers else memory.get('MemTotal'),
        'memory_basis': 'visible_cgroup_limit' if limits['memory_limit_bytes'] is not None else
                        'unconfirmed_container_allocation' if container_markers else 'guest_or_os_visible_memory',
        'dedicated_cpu': 'unknown', 'reserved_memory': 'unknown',
        'container_evidence': container_markers,
    }
    report.update(status='partial', metrics=metrics, cgroup=limits,
                  sources=['/proc/meminfo','/proc/stat','/proc/pressure/{cpu,memory,io}',
                           '/proc/self/cgroup','/proc/self/mountinfo','sched_getaffinity'])
    return report


def render(report, out):
    """Render numeric evidence without parsing translated human descriptions."""
    tr = out.text
    if report['status'] == 'unsupported':
        out.row(tr('资源限制','Resource limits'),tr('当前系统不支持','Unsupported on this system'),'unknown')
        return
    metrics, limits = report['metrics'], report['cgroup']
    def row(zh, en, value, suffix=''):
        out.row(tr(zh,en), tr('未知','Unknown') if value is None else f'{value:g}{suffix}',
                'unknown' if value is None else 'ok')
    allocation = report['allocation']
    row('本进程 CPU 上限','Process CPU limit',allocation['cpu_limit_cores'],' vCPU')
    out.row(tr('CPU 额度依据','CPU limit basis'),tr('CPU 范围与可见配额','Affinity and visible quota')
            if limits['cpu_quota_cores'] is not None else tr('仅系统可见 CPU/进程范围，配额未确认','OS-visible CPUs/affinity only; quota unconfirmed'),'unknown')
    value = allocation['memory_limit_bytes']
    row('内存额度/可见量','RAM limit/visible',None if value is None else value/1024**2,' MiB')
    basis = allocation['memory_basis']
    out.row(tr('内存额度依据','RAM limit basis'),
            tr('可见 cgroup 限额（可能与同组进程共享）','Visible cgroup limit (may be shared within the group)') if basis == 'visible_cgroup_limit' else
            tr('容器额度未确认；不展示宿主机内存作额度','Container allocation unknown; host RAM is not an allocation') if basis == 'unconfirmed_container_allocation' else
            tr('虚拟机/系统可见量；独享保障未确认','Guest/OS-visible amount; reservation unconfirmed'),'unknown')
    out.row(tr('CPU/内存独享性','CPU/RAM dedication'),tr('无法从本机确认','Cannot be verified locally'),'unknown')
    if not allocation['container_evidence']:
        for zh,en,key in [('Swap 总量','Swap total','swap_total_bytes'),('Swap 已用','Swap used','swap_used_bytes')]:
            value = metrics[key]
            row(zh,en,None if value is None else value/1024**2,' MiB')
    row('CPU steal（短采样）','CPU steal (short)',metrics['steal_percent'],'%')
    row('实际采样时间','Observation time',metrics['sample_elapsed_seconds'],' s')
    for kind in ('cpu','memory','io'):
        psi = metrics['pressure'][kind]
        row(f'{kind} 压力 some/10s',f'{kind} PSI some/10s',psi.get('some',{}).get('avg10') if psi else None,'%')
    out.row(tr('范围说明','Scope'),tr('可见配额；独享性未确认；压力为短采样',
                                      'Visible quota; exclusivity unconfirmed; short pressure sample'),'unknown')
