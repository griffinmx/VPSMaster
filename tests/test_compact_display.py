"""Display filtering must not hide findings or alter machine-readable evidence."""
import json
import pytest
from proxydoctor.console import Console


@pytest.mark.parametrize('lang,empty', [('zh','未知'), ('en','Unknown')])
@pytest.mark.parametrize('framed', [False, True])
def test_only_empty_observations_hidden(capsys, lang, empty, framed):
    out=Console(lang,'never',hide_unavailable=True)
    if framed:out.frame_open('Test')
    out.row('missing-row',empty,'unknown')
    out.row('measured-failure','connection refused','bad')
    out.row('limit','Exclusivity unconfirmed','unknown')
    if framed:out.frame_close()
    text=capsys.readouterr().out
    assert 'missing-row' not in text
    assert 'connection refused' in text
    assert 'Exclusivity unconfirmed' in text


def test_verbose_display_preserves_unknown(capsys):
    Console('en','never').row('missing','Unknown','unknown')
    assert 'Unknown' in capsys.readouterr().out


def test_offline_compact_report_keeps_skipped_modules(tmp_path, monkeypatch, capsys):
    from proxydoctor.suite import run_suite
    monkeypatch.chdir(tmp_path)
    report=tmp_path/'compact.json'
    code=run_suite(lang='en',offline=True,json_output=report,color='never')
    assert code in (0,1)
    text=capsys.readouterr().out
    assert 'Skipped offline' not in text
    data=json.loads(report.read_text())
    for name in ('network','route','media','ip_quality'):
        assert data['modules'][name]['status']=='skipped'
    verbose=tmp_path/'verbose.json'
    assert run_suite(lang='en',offline=True,json_output=verbose,color='never',show_unavailable=True) in (0,1)
    assert 'Skipped offline' in capsys.readouterr().out
