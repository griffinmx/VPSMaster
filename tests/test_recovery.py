"""Fault-injection acceptance cases. Added, not executed in this work batch."""
import json

import pytest

from proxydoctor.reports import ReportStore, recover_latest
from proxydoctor.runner import ModuleRunner


def test_module_exception_does_not_abort_next_module_or_expose_secrets():
    report = {}
    saved, notices, called = [], [], []
    runner = ModuleRunner(report, lambda: saved.append(json.dumps(report)), notices.append)

    def broken():
        raise RuntimeError('token=private-value')

    runner.run('broken', broken)
    runner.run('healthy', lambda: called.append(True))
    assert called == [True]
    assert report['modules']['broken']['error_code'] == 'MODULE_ERROR'
    assert report['modules']['healthy']['status'] == 'success'
    assert notices == ['broken']
    assert 'private-value' not in ''.join(saved)


def test_cancellation_is_checkpointed_and_propagated():
    report, saved = {}, []
    runner = ModuleRunner(report, lambda: saved.append(json.dumps(report)), lambda name: None)

    def cancel():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        runner.run('route', cancel)
    assert json.loads(saved[-1])['modules']['route']['status'] == 'cancelled'


def test_recovery_retains_last_complete_redacted_event(tmp_path):
    path = tmp_path/'report.json'
    store = ReportStore(path, lambda value: {'safe': value['safe']})
    assert store.checkpoint({'safe': 1, 'secret': 'hidden'})
    journal = store.journal_path
    store.close()
    with journal.open('a', encoding='utf-8') as stream:
        stream.write('{"interrupted":')
    assert recover_latest(journal) == {'safe': 1}
    assert 'hidden' not in journal.read_text(encoding='utf-8')


def test_final_report_race_never_overwrites_existing_file(tmp_path):
    path = tmp_path/'report.json'
    store = ReportStore(path, lambda value: value)
    path.write_text('other process', encoding='utf-8')
    assert not store.finish({'result': 'partial'})
    store.close()
    assert path.read_text(encoding='utf-8') == 'other process'
    assert recover_latest(store.journal_path)['result'] == 'partial'


def test_existing_destination_is_rejected(tmp_path):
    path = tmp_path/'report.json'
    path.write_text('existing', encoding='utf-8')
    with pytest.raises(FileExistsError):
        ReportStore(path, lambda value: value)


def test_dangling_symlink_destination_is_rejected(tmp_path):
    path = tmp_path/'report.json'
    try:
        path.symlink_to(tmp_path/'missing.json')
    except OSError:
        pytest.skip('Creating symlinks is not permitted on this host')
    with pytest.raises(FileExistsError):
        ReportStore(path, lambda value: value)


def test_flush_failure_is_reported_without_discarding_prior_event(tmp_path, monkeypatch):
    store = ReportStore(tmp_path/'report.json', lambda value: value)
    assert store.checkpoint({'completed': 'system'})

    def full_disk(fd):
        raise OSError('disk full')

    monkeypatch.setattr('proxydoctor.reports.os.fsync', full_disk)
    assert not store.checkpoint({'completed': 'network'})
    assert store.failed
    store.close()
    assert recover_latest(store.journal_path) is not None
