import os
import sys
import subprocess
from proxydoctor import routes, worker
from proxydoctor.geo import GeoLocator
from proxydoctor.console import Console, clean, width


def test_interrupt_during_first_fsync_preserves_cancelled_report(tmp_path, monkeypatch):
    import json
    import pytest
    from proxydoctor.session import ScanSession
    from proxydoctor.reports import recover_latest
    from proxydoctor import worker
    path = tmp_path/'startup.json'
    session = ScanSession('route', path, 'en')
    original = os.fsync
    calls = []
    def interrupt_once(fd):
        original(fd)
        if not calls:
            calls.append(True)
            raise KeyboardInterrupt
    monkeypatch.setattr(os, 'fsync', interrupt_once)
    try:
        with pytest.raises(KeyboardInterrupt):
            with session:
                raise AssertionError('Operation must not begin')
        assert json.loads(path.read_text())['result'] == 'cancelled'
        assert recover_latest(str(path)+'.events.jsonl')['result'] == 'cancelled'
        assert session.store.stream.closed
    finally:worker.reset()


def test_real_command_error_is_classified_without_leaking_stderr():
    code, text, error = worker.local_command([sys.executable, '-B', '-c',
        'import sys;sys.stderr.write("socket: Operation not permitted: synthetic-secret");sys.exit(1)'])
    assert code == 1 and not text and error == 'PERMISSION_DENIED'


def test_trace_preserves_permission_and_missing_dependency(monkeypatch):
    monkeypatch.setattr(routes.sys, 'platform', 'linux')
    monkeypatch.setattr(routes.shutil, 'which', lambda *a, **k: '/usr/bin/traceroute')
    monkeypatch.setattr(worker, 'local_command', lambda *a, **k: (1, '', 'PERMISSION_DENIED'))
    result = {}; rows = []
    assert routes.trace_method('127.0.0.1', lambda *a, **k: None, method='tcp', records=rows, summary=result) == 1
    assert result == {'state': 'permission_denied', 'error_code': 'PERMISSION_DENIED'} and not rows
    monkeypatch.setattr(routes.shutil, 'which', lambda *a, **k: None)
    routes.trace_method('127.0.0.1', lambda *a, **k: None, method='tcp', summary=result)
    assert result['state'] == 'dependency_missing'


def test_geo_metadata_bounded_validated_and_terminal_safe(monkeypatch):
    locator = GeoLocator('en')
    location = locator.remember('8.8.8.8', {'country': 'US', 'connection': {'asn': 15169, 'isp': '\x1b[31mGoogle\u202e'}})
    locator.cache['8.8.8.8'] = location
    result = locator.details('8.8.8.8')
    assert result['asn'] == 15169 and result['source'] == 'https://ipwho.is/'
    assert result['geography'] == 'database_estimate' and result['observed_at']
    assert '\x1b' not in result['operator'] and '\u202e' not in result['operator']
    assert locator.details('127.0.0.1')['asn'] is None
    locator.lookups = 12
    assert locator.details('1.1.1.1')['asn'] is None


def test_narrow_terminal_frame_preserves_all_text(monkeypatch, capsys):
    monkeypatch.setattr(sys.stdout, 'isatty', lambda: True)
    monkeypatch.setattr('proxydoctor.console.shutil.get_terminal_size', lambda: os.terminal_size((32, 24)))
    out = Console('zh', 'never')
    out.frame_open('公测版'); out.frame_keyvalue('字段', '位置数据'*25); out.frame_close()
    lines = capsys.readouterr().out.splitlines()
    assert all(width(line) == 32 for line in lines)
    assert '位置数据'*25 in ''.join(line[1:-1].strip() for line in lines if line.startswith('║'))
    assert clean('\u202eevil\u2069\x1b') == 'evil'
