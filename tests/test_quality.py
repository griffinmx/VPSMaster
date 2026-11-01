import json
import socket
import subprocess

import pytest

from proxydoctor import quality
from proxydoctor.i18n import translator


def test_dns_success_and_hard_timeout(monkeypatch):
    monkeypatch.setattr(quality.subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a, 0, json.dumps([int(socket.AF_INET)])))
    assert quality.dns_check()['ipv4'] is True
    def timeout(*args, **kwargs):
        assert kwargs['timeout'] == quality.TIMEOUT
        raise subprocess.TimeoutExpired(args[0], 5)
    monkeypatch.setattr(quality.subprocess, 'run', timeout)
    assert quality.dns_check() == {'status':'unknown', 'reason':'timeout'}


def test_tcp_failure_does_not_claim_cause(monkeypatch):
    def fail(*args, **kwargs): raise OSError('refused')
    monkeypatch.setattr(quality.socket, 'create_connection', fail)
    assert quality.tcp_check('test', '127.0.0.1', 443)['status'] == 'unknown'


@pytest.mark.parametrize('lang', ['zh', 'en'])
def test_streaming_continues_after_failure_and_propagates_status(monkeypatch,lang):
    monkeypatch.setattr(quality, 'dns_check', lambda: {'status':'unknown','reason':'timeout'})
    called=[]
    def tcp(label, ip, port):
        called.append(label)
        return {'status':'pass','target':label,'port':port,'elapsed_ms':7}
    monkeypatch.setattr(quality, 'tcp_check', tcp)
    output=[]
    result=quality.run_quality(translator(lang),lambda text, **kwargs: output.append(text))
    assert result==1 and called==['Cloudflare','Google']
    assert len(output)==8
    assert ('DNS 查询未成功' if lang=='zh' else 'DNS lookup did not succeed') in ' '.join(output)
