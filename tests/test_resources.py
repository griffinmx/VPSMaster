"""Resource parser/fixture cases; not executed in the current batch."""
from proxydoctor.resources import cgroup_limits, collect, cpu_ticks, pressure, steal_delta


def fixture_reader(files):
    return lambda path: files.get(path)


def test_nested_v2_uses_strictest_visible_ancestor():
    read = fixture_reader({
        '/proc/self/cgroup': '0::/tenant/app\n',
        '/proc/self/mountinfo': '1 0 0:1 / /sys/fs/cgroup rw - cgroup2 cgroup rw',
        '/sys/fs/cgroup/tenant/app/cpu.max': '200000 100000',
        '/sys/fs/cgroup/tenant/cpu.max': '50000 100000',
        '/sys/fs/cgroup/cpu.max': 'max 100000',
        '/sys/fs/cgroup/tenant/app/memory.max': 'max',
        '/sys/fs/cgroup/tenant/memory.max': '536870912',
    })
    result = cgroup_limits(read)
    assert result['cpu_quota_cores'] == 0.5
    assert result['memory_limit_bytes'] == 512*1024**2


def test_v1_controller_mount_and_unlimited_sentinel():
    read = fixture_reader({
        '/proc/self/cgroup': '2:cpu,cpuacct:/app\n3:memory:/app',
        '/proc/self/mountinfo': '1 0 0:1 / /cg/cpu rw - cgroup cgroup rw,cpu,cpuacct\n2 0 0:2 / /cg/memory rw - cgroup cgroup rw,memory',
        '/cg/cpu/app/cpu.cfs_quota_us': '25000',
        '/cg/cpu/app/cpu.cfs_period_us': '100000',
        '/cg/memory/app/memory.limit_in_bytes': '9223372036854771712',
    })
    result = cgroup_limits(read)
    assert result['cpu_quota_cores'] == 0.25
    assert result['memory_limit_bytes'] is None


def test_subtree_mount_maps_membership_without_escaping_visible_root():
    read = fixture_reader({
        '/proc/self/cgroup': '0::/tenant/app',
        '/proc/self/mountinfo': '1 0 0:1 /tenant /sys/fs/cgroup rw - cgroup2 cgroup rw',
        '/sys/fs/cgroup/app/cpu.max': '100000 100000',
        '/sys/fs/cgroup/cpu.max': '50000 100000',
    })
    result = cgroup_limits(read)
    assert result['cpu_quota_cores'] == 0.5
    assert all('/tenant/' not in row['source'] for row in result['observations'])


def test_missing_or_invalid_cgroup_is_unknown_not_unlimited():
    assert cgroup_limits(fixture_reader({}))['cpu_quota_cores'] is None
    assert pressure('some avg10=nan avg60=0 avg300=0 total=0') is None
    assert pressure('some avg10=0.25 avg60=0 avg300=0 total=12')['some']['avg10'] == 0.25


def test_steal_uses_delta_and_does_not_double_count_guest():
    before = cpu_ticks('cpu 100 0 0 100 0 0 0 0 90 0')
    after = cpu_ticks('cpu 120 0 0 170 0 0 0 10 100 0')
    assert steal_delta(before, after) == 10
    assert steal_delta(after, before) is None
    assert steal_delta(before, before) is None


def test_collect_keeps_numeric_units_and_passive_sampling():
    snapshots = iter(['cpu 100 0 0 100 0 0 0 0', 'cpu 120 0 0 170 0 0 0 10'])
    files = {'/proc/meminfo': 'MemTotal: 1024 kB\nMemAvailable: 512 kB\nSwapTotal: 256 kB\nSwapFree: 128 kB'}
    times = iter([10.0, 10.2])
    waits = []
    result = collect(read=lambda path: next(snapshots) if path == '/proc/stat' else files.get(path),
                     system='Linux', cpu_count=lambda: 8, affinity=lambda: {0,1},
                     sleep=waits.append, clock=lambda: next(times))
    assert waits == [0.2]
    assert result['metrics']['visible_cpu_upper_bound_cores'] == 2
    assert result['metrics']['swap_used_bytes'] == 128*1024
    assert result['metrics']['steal_percent'] == 10


def test_non_linux_does_not_read_proc_or_wait():
    def unexpected(*args):
        raise AssertionError('Unsupported system must not probe Linux files')
    assert collect(read=unexpected, sleep=unexpected, system='Windows')['status'] == 'unsupported'


def test_container_without_memory_limit_does_not_claim_host_ram():
    files = {'/.dockerenv': '', '/proc/meminfo': 'MemTotal: 67108864 kB'}
    result = collect(read=fixture_reader(files), system='Linux', sleep=lambda _: None,
                     cpu_count=lambda: 64, affinity=lambda: {0,1})
    assert result['allocation']['memory_limit_bytes'] is None
    assert result['allocation']['dedicated_cpu'] == 'unknown'
    assert result['metrics']['memory_total_bytes'] == 64*1024**3
