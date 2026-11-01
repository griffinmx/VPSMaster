from proxydoctor.checks import inspect
from test_checks import Ubuntu, by_id


def test_server_information_uses_visible_resources():
    host = Ubuntu()
    original_read = host.read
    host.read = lambda path: {'/proc/cpuinfo': 'processor : 0\nmodel name : Example CPU\n',
                              '/proc/meminfo': 'MemTotal: 2097152 kB\nMemAvailable: 1048576 kB\n'}.get(path, original_read(path))
    host.cpu_count = lambda: 2
    host.kernel = lambda: '6.8.0-test'
    host.disk_total = lambda: 20 * 1024**3
    data = inspect(host, lang='en')
    assert '2' in by_id(data, 'cpu')['detail']
    assert 'Example CPU' in by_id(data, 'cpu')['evidence']
    assert '2048 MiB' in by_id(data, 'memory_total')['detail']
    assert '20.0 GiB' in by_id(data, 'disk_capacity')['detail']
    assert '6.8.0-test' in by_id(data, 'kernel')['detail']


def test_unavailable_hardware_information_is_explicitly_unknown():
    data = inspect(Ubuntu())
    for key in ('cpu', 'kernel', 'memory_total', 'disk_capacity'):
        assert by_id(data, key)['status'] == 'unknown'
