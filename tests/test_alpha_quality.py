import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from proxydoctor.schema import normalize_report,STATUSES
from proxydoctor.reports import ReportStore,recover_latest
from proxydoctor import worker


def test_uniform_envelope_preserves_unknown_and_restriction():
    report={'generated_at':'2026-11-01','modules':{'network':{'status':'running'}},
            'media':{'Netflix':{'state':'catalog_visible'},'Disney+':{'state':'restricted'}}}
    rows=normalize_report(report)
    assert {row['status'] for row in rows}<=STATUSES
    assert next(row for row in rows if row['check_id']=='media.Netflix')['status']=='unknown'
    assert next(row for row in rows if row['check_id']=='media.Disney+')['status']=='failure'
    assert all(set(('check_id','observed_at','method','source','metrics','limitations','error_code'))<=set(row) for row in rows)


def test_route_statistics_count_only_actual_probe_records():
    from proxydoctor.routes import summarize_hops
    rows=[{'hop':1,'ip':'192.0.2.1','latency_ms':10,'probes_sent':1,'responses':1},
          {'hop':1,'ip':None,'latency_ms':None,'probes_sent':1,'responses':0},
          {'hop':1,'ip':'192.0.2.1','latency_ms':20,'probes_sent':1,'responses':1}]
    result=summarize_hops(rows)[0]
    assert result['probes_sent']==3 and result['responses']==2 and result['timeouts']==1
    assert result['response_loss_percent']==33.33
    assert result['median_rtt_ms']==15
    assert 'not_end_to_end' in result['scope']


def test_journal_budget_preserves_previous_complete_record(tmp_path):
    store=ReportStore(tmp_path/'report.json',lambda x:x)
    assert store.checkpoint({'small':1})
    store.bytes_written=64*1024**2
    assert not store.checkpoint({'small':2})
    store.close()
    assert recover_latest(store.journal_path)=={'small':1}


def test_network_worker_timeout_kills_and_reaps(monkeypatch):
    processes=[]
    real=worker.subprocess.Popen
    def child(*args,**kwargs):
        process=real([sys.executable,'-c','import time;time.sleep(30)'],**kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(worker.subprocess,'Popen',child)
    worker.reset()
    started=time.monotonic()
    assert worker.invoke('json',{},timeout=0.1) is None
    assert time.monotonic()-started<5
    assert processes[0].poll() is not None


def test_worker_cancellation_prevents_new_requests():
    worker.cancel_all()
    try:assert worker.invoke('json',{}) is None
    finally:worker.reset()


def test_installer_integrity_detects_tampering(tmp_path):
    source=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('alpha_install',source/'install.py')
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    files=installer.verify(source)
    assert 'proxydoctor/cli.py' in files
    # A changed copy must fail before creating any environment or executing code.
    import shutil
    copied=tmp_path/'bundle';copied.mkdir()
    for name in files:
        target=copied/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
    shutil.copyfile(source/'MANIFEST.sha256.json',copied/'MANIFEST.sha256.json')
    (copied/'proxydoctor/cli.py').write_text('tampered')
    with pytest.raises(ValueError,match='integrity'):installer.verify(copied)


def test_installer_manifest_cannot_escape_source(tmp_path):
    source=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('alpha_install',source/'install.py')
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    bad={'version':installer.VERSION,'files':{'../outside.py':'x'}}
    (tmp_path/'MANIFEST.sha256.json').write_text(json.dumps(bad))
    with pytest.raises(ValueError):installer.verify(tmp_path)


@pytest.mark.parametrize('failure',[KeyboardInterrupt,subprocess.TimeoutExpired])
def test_installer_failure_cleans_reserved_directory_only(tmp_path,monkeypatch,failure):
    source=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('alpha_install',source/'install.py')
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    monkeypatch.setattr(installer.sys,'platform','linux')
    def broken(*args,**kwargs):
        if failure is KeyboardInterrupt:raise KeyboardInterrupt
        raise subprocess.TimeoutExpired('venv',45)
    monkeypatch.setattr(installer.subprocess,'run',broken)
    neighbor=tmp_path/'keep.txt';neighbor.write_text('keep')
    with pytest.raises(failure):installer.install(source,tmp_path/'new-prefix')
    assert not (tmp_path/'new-prefix').exists()
    assert neighbor.read_text()=='keep'
