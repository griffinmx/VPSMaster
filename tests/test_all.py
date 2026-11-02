import contextlib
import json
import signal
import sys
import time
from pathlib import Path
import pytest
from proxydoctor import cli,suite,worker
from proxydoctor.runner import ModuleRunner


def test_cli_all_reuses_suite(monkeypatch):
    captured={}
    monkeypatch.setattr(sys,'argv',['vpsmaster','all','--offline','--lang','en'])
    monkeypatch.setattr(cli,'run_suite',lambda **kw:captured.update(kw) or 0)
    with pytest.raises(SystemExit) as ex:cli._main()
    assert ex.value.code==0
    assert captured['comprehensive'] and captured['include_bgp'] and captured['offline']
    assert not captured['allow_bandwidth'] and not captured['include_return_routes']


def test_full_requires_bandwidth_consent_and_no_implicit_china(monkeypatch):
    captured={}
    monkeypatch.setattr(cli,'run_suite',lambda **kw:captured.update(kw) or 0)
    monkeypatch.setattr(sys,'argv',['vpsmaster','all','--full'])
    with pytest.raises(SystemExit) as ex:cli._main()
    assert ex.value.code==0 and not captured['allow_bandwidth']
    assert captured['include_return_routes'] and captured['mail_probes']
    assert captured['bandwidth_sources'] is None
    monkeypatch.setattr(sys,'argv',['vpsmaster','all','--allow-bandwidth'])
    with pytest.raises(SystemExit) as ex:cli._main()
    assert ex.value.code==2


@pytest.mark.parametrize('lang',['zh','en'])
def test_all_offline_keeps_skips_without_network(tmp_path,monkeypatch,capsys,lang):
    import proxydoctor.runner as runner
    monkeypatch.setattr(runner,'bounded',lambda n:contextlib.nullcontext())
    monkeypatch.chdir(tmp_path)
    def blocked(*a,**kw):raise AssertionError('Offline initiated network')
    for name in ('collect_ipquality','run_media','protocol_trace','native_trace','measure_bandwidth'):
        monkeypatch.setattr(suite,name,blocked)
    monkeypatch.setattr('proxydoctor.connectivity.run_console',blocked)
    monkeypatch.setattr('proxydoctor.bgp.collect',blocked)
    path=tmp_path/'offline.json'
    assert suite.run_suite(comprehensive=True,offline=True,lang=lang,color='never',json_output=path) in (0,1)
    report=json.loads(path.read_text(encoding='utf-8'))
    assert report['command']=='all' and len(report['modules'])==11
    for name in ('network','ip_quality','route','route_icmp','route_tcp','bgp','media'):
        assert report['modules'][name]['status']=='skipped'
    assert sum(report['summary']['module_counts'].values())==11
    text=capsys.readouterr().out
    assert '11/11' in text and '\x1b[' not in text


def test_module_failure_and_budget_continue_without_fake_success():
    report={};events=[]
    runner=ModuleRunner(report,lambda:None,lambda _:None,observe=lambda n,s,end:events.append((n,end)))
    def bad():raise ValueError('secret must not be displayed')
    runner.run('bad',bad);runner.run('good',lambda:None)
    runner.deadline=time.monotonic()-1
    runner.run('budget',lambda:pytest.fail('Expired budget executed operation'))
    assert report['modules']['bad']['status']=='failure'
    assert report['modules']['good']['status']=='success'
    assert report['modules']['budget']['reason']=='TOTAL_TIME_BUDGET'
    assert len(events)==6


@pytest.mark.skipif(not hasattr(signal,'setitimer'),reason='Linux scoped deadline test')
def test_module_timeout_reaps_child_and_next_module_runs():
    report={};worker.reset();started=time.monotonic()
    runner=ModuleRunner(report,lambda:None,lambda _:None,module_timeout=.15)
    runner.run('timeout',lambda:worker.local_command([sys.executable,'-c','import time;time.sleep(30)'],timeout=35))
    runner.run('next',lambda:None)
    assert time.monotonic()-started<3
    assert report['modules']['timeout']['error_code']=='MODULE_TIMEOUT'
    assert report['modules']['next']['status']=='success'
    assert not worker._active
    assert signal.getitimer(signal.ITIMER_REAL)[0]==0


def test_missing_trace_dependency_has_structured_reason(tmp_path,monkeypatch,capsys):
    import proxydoctor.runner as runner
    from test_suite import unavailable_ip
    monkeypatch.setattr(runner,'bounded',lambda n:contextlib.nullcontext())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(suite,'collect_ipquality',unavailable_ip)
    monkeypatch.setattr('proxydoctor.connectivity.run_console',lambda *a,**kw:1)
    monkeypatch.setattr(suite,'native_trace',lambda *a,**kw:1)
    monkeypatch.setattr(suite,'protocol_trace',lambda *a,**kw:kw['summary'].update(state='dependency_missing',error_code='TRACEROUTE_DEPENDENCY_MISSING') or 1)
    monkeypatch.setattr(suite,'run_media',lambda *a,**kw:kw['results'].update(Netflix={'state':'unknown'}))
    path=tmp_path/'online.json'
    assert suite.run_suite(comprehensive=True,json_output=path,color='never')==1
    report=json.loads(path.read_text())
    assert report['modules']['route_icmp']['status']=='skipped'
    assert report['modules']['route_tcp']['error_code']=='TRACEROUTE_DEPENDENCY_MISSING'
    assert report['modules']['bgp']['status']=='unknown'
    assert report['summary']['failed_modules']==0
    assert '11/11' in capsys.readouterr().out
