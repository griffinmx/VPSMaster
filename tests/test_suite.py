import subprocess
import sys

import pytest

from proxydoctor import suite
from proxydoctor import bandwidth, ipquality


def unavailable_bandwidth(**kwargs):
    return {'sources':{'cloudflare':{'directions':{direction:bandwidth.summarize([bandwidth.Sample(direction,1024,error='request_failed')]*3)
                          for direction in ('download','upload')}}}}


def unavailable_ip(**kwargs):
    from unittest.mock import patch
    with patch.object(ipquality,'request_json',return_value=(None,'request_failed')):
        return ipquality.collect()


def test_offline_suite_never_calls_network_or_providers(monkeypatch,capsys):
    def unexpected(*args,**kwargs): raise AssertionError('unexpected network/provider')
    monkeypatch.setattr(suite,'measure_bandwidth',unexpected)
    monkeypatch.setattr('proxydoctor.connectivity.run_console',unexpected)
    monkeypatch.setattr(suite,'run_media',unexpected)
    monkeypatch.setattr(suite,'collect_ipquality',unexpected)
    monkeypatch.setattr(suite,'execute_provider',unexpected)
    monkeypatch.setattr(suite,'native_trace',unexpected)
    import platform
    assert suite.run_suite(offline=True,show_unavailable=True)==(0 if platform.system()=='Linux' else 1)
    text=capsys.readouterr().out
    assert all(f'===== {number}.' in text for number in range(1,5))


def test_suite_continues_when_network_and_providers_unavailable(monkeypatch,capsys):
    monkeypatch.setattr(suite,'measure_bandwidth',unavailable_bandwidth)
    monkeypatch.setattr('proxydoctor.connectivity.run_console',lambda *args,**kwargs: 1)
    monkeypatch.setattr(suite.shutil,'which',lambda *args,**kwargs: None)
    monkeypatch.setattr('proxydoctor.media.check_reachability',lambda *args: {'state':'access_denied','http':403,'evidence':'http_response'})
    monkeypatch.setattr(suite,'collect_ipquality',unavailable_ip)
    monkeypatch.setattr(suite,'native_trace',lambda *args,**kwargs: 1)
    assert suite.run_suite(lang='en')==1
    output=capsys.readouterr().out
    assert 'up to 30 hops' in output
    assert 'Access denied' in output


def test_besttrace_is_rejected_before_execution(tmp_path,monkeypatch):
    executable=tmp_path/'best trace'
    executable.write_text('example',encoding='utf-8')
    monkeypatch.setattr(suite,'measure_bandwidth',unavailable_bandwidth)
    monkeypatch.setattr(suite,'run_quality',lambda *args,**kwargs: 0)
    monkeypatch.setattr('proxydoctor.media.check',lambda *args: {'state':'unknown','http':200,'evidence':'playback_not_verified'})
    monkeypatch.setattr(suite,'collect_ipquality',unavailable_ip)
    calls=[]
    monkeypatch.setattr(suite,'execute_provider',lambda argv,timeout: calls.append(argv) or 0)
    with pytest.raises(ValueError,match='disabled'):
        suite.run_suite(besttrace=executable)
    assert calls==[]


@pytest.mark.parametrize('target',[';reboot','--help','not-a-host'])
def test_suite_rejects_invalid_route_target(target):
    result=subprocess.run([sys.executable,'-m','proxydoctor','suite','--offline','--route-target='+target],capture_output=True)
    assert result.returncode==2


def test_short_download_is_not_reported_as_bandwidth(monkeypatch):
    import io
    class Response:
        status=200
        headers={}
        read=io.BytesIO(b'short').read
        def __enter__(self): return self
        def __exit__(self,*args): pass
    class Opener:
        def open(self,*args,**kwargs): return Response()
    monkeypatch.setattr(bandwidth,'opener',lambda: Opener())
    sample=bandwidth.transfer('download',1024)
    assert sample.mbps is None and sample.error=='short_response'
