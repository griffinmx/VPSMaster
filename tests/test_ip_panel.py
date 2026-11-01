import re
import unicodedata
from proxydoctor.console import Console
from proxydoctor import ipquality


def test_panel_wraps_cjk_and_strips_control_characters(capsys):
    Console('zh','never').panel('概览',[('地区','陕西省'*40+'\x1b[31m','unknown')],width=50)
    lines=capsys.readouterr().out.splitlines()
    assert '\x1b' not in '\n'.join(lines)
    for line in lines:
        assert sum(2 if unicodedata.east_asian_width(ch) in ('W','F') else 0 if unicodedata.combining(ch) else 1 for ch in line)==50


def test_ip_panel_keeps_missing_risk_unknown_and_hides_ip(monkeypatch,capsys):
    monkeypatch.setattr(ipquality,'request_json',lambda *args,**kwargs:({'ip':'8.8.8.8'},'ok'))
    result=ipquality.collect(enrich=False)
    ipquality.render(result,Console('zh','never'))
    output=capsys.readouterr().out
    assert 'IP 质量概览' in output
    assert '8.8.8.8' not in output
    assert '不代表安全' in output
