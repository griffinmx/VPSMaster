import json
import subprocess
import sys

import pytest

from proxydoctor.checks import Command, inspect
from proxydoctor.cli import redact
from test_checks import Ubuntu, by_id


class ConfiguredHost(Ubuntu):
    def __init__(self, routes4='[]', routes6='[]', dns='nameserver 8.8.8.8\n', ssh=None, session=''):
        commands = {
            ('ip','-j','-4','route','show','default'): Command(0, routes4),
            ('ip','-j','-6','route','show','default'): Command(0, routes6),
            ('sshd','-T'): ssh or Command(None, reason='命令不可用'),
        }
        super().__init__(commands)
        self.dns, self.session = dns, session

    def read(self, path):
        return self.dns if path == '/etc/resolv.conf' else super().read(path)

    def ssh_connection(self):
        return self.session


@pytest.mark.parametrize('lang', ['zh','en'])
def test_ipv4_default_route_detected_without_connectivity_claim(lang):
    host = ConfiguredHost(routes4=json.dumps([{'dst':'default', 'dev':'eth0', 'gateway':'192.0.2.1'}]))
    result = by_id(inspect(host, lang=lang), 'default_route')
    assert result['status'] == 'pass'
    assert 'eth0' in result['evidence']
    assert '192.0.2.1' not in str(redact(result, lang))


@pytest.mark.parametrize('routes4,routes6', [
    ('[]','[]'), ('broken','[]'), ('{}','[]'),
    ('[{"dst":"default"}]','[]'),
    ('[{"dst":"default","dev":"eth0","gateway":"not-an-ip"}]','[]'),
    ('[{"dst":"default","type":"blackhole"}]','[]'),
    ('[{"dst":"default","dev":"eth0"}]','broken'),
])
def test_routes_incomplete_or_malformed_never_pass(routes4,routes6):
    assert by_id(inspect(ConfiguredHost(routes4, routes6)), 'default_route')['status'] == 'unknown'


@pytest.mark.parametrize('dns,status', [
    ('nameserver 1.1.1.1\nnameserver 2001:4860:4860::8888\n','pass'),
    ('nameserver 127.0.0.53\n','unknown'),
    ('nameserver ::1\n','unknown'), ('','unknown'), (None,'unknown'),
    ('nameserver invalid\n','unknown'), ('nameserver 0.0.0.0\n','unknown'),
    ('nameserver 1.1.1.1\nnameserver invalid','unknown'),
    ('# nameserver 1.1.1.1\nsearch example.com','unknown'),
])
def test_dns_config_results_do_not_claim_resolution(dns,status):
    result=by_id(inspect(ConfiguredHost(dns=dns)), 'dns_config')
    assert result['status']==status
    assert '不主动发送 DNS' in result.get('advice','') or dns is None
    assert '1.1.1.1' not in str(redact(result))


@pytest.mark.parametrize('config,session,port,status', [
    ('port 22\nport 2222\n','',22,'warn'),
    ('port 22\nport 2222\n','',2222,'warn'),
    ('port 2222\n','',8388,'unknown'),
    ('','192.0.2.1 50000 192.0.2.2 2200',2200,'warn'),
    ('','bad session',22,'unknown'),
    ('port invalid\n','',22,'unknown'),
    ('','',22,'unknown'),
])
@pytest.mark.parametrize('lang',['zh','en'])
def test_ssh_protection_warns_known_ports_otherwise_remains_unknown(config,session,port,status,lang):
    host=ConfiguredHost(ssh=Command(0,config),session=session)
    result=by_id(inspect(host,port=port,lang=lang),'ssh_port_safety')
    assert result['status']==status
    assert '192.0.2.' not in json.dumps(result)


def test_failed_ssh_configuration_does_not_suppress_valid_active_session():
    host=ConfiguredHost(ssh=Command(1,''),session='192.0.2.1 40000 192.0.2.2 2222')
    assert by_id(inspect(host,port=2222),'ssh_port_safety')['status']=='warn'


def test_failed_route_command_is_unknown_even_when_other_family_has_route():
    host=ConfiguredHost(routes4='[{"dst":"default","dev":"eth0"}]')
    host.commands[('ip','-j','-6','route','show','default')]=Command(None,reason='命令不可用')
    assert by_id(inspect(host),'default_route')['status']=='unknown'


def test_public_ip_lookup_is_opt_in_and_never_implies_inbound_reachability():
    host=ConfiguredHost()
    calls=[]
    host.detect_public_ip=lambda: calls.append(True) or '8.8.8.8'
    inspect(host)
    assert not calls
    result=by_id(inspect(host,detect_public_ip=True,lang='en'),'public_ip')
    assert calls == [True]
    assert result['status']=='unknown'
    assert 'inbound reachability' in result['detail']
    assert '8.8.8.8' not in str(redact(result,'en'))


def test_public_ip_lookup_failure_remains_unknown():
    host=ConfiguredHost()
    host.detect_public_ip=lambda: None
    result=by_id(inspect(host,detect_public_ip=True),'public_ip')
    assert result['status']=='unknown'
    assert '失败' in result['detail']


def test_public_ip_lookup_disabled_by_default_in_cli(monkeypatch):
    from proxydoctor.checks import Host
    def unexpected(_):
        raise AssertionError('network used without opt-in')
    monkeypatch.setattr(Host,'detect_public_ip',unexpected)
    inspect(Host())


@pytest.mark.parametrize('payload,expected', [(b'8.8.8.8\n','8.8.8.8'), (b'127.0.0.1',None), (b'bad',None), (b'9'*129,None)])
def test_public_ip_lookup_validates_bounded_response(monkeypatch,payload,expected):
    from proxydoctor.checks import Host
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,size):
            assert size==129
            return payload
    class Opener:
        def open(self,url,timeout):
            assert url=='https://api64.ipify.org' and timeout==5
            return Response()
    monkeypatch.setattr('proxydoctor.checks.urllib.request.build_opener',lambda *args: Opener())
    assert Host().detect_public_ip()==expected


def test_public_ip_options_are_mutually_exclusive():
    command=[sys.executable,'-m','proxydoctor','check','--public-ip','8.8.8.8','--detect-public-ip']
    assert subprocess.run(command,capture_output=True).returncode==2


def test_show_ip_only_affects_terminal_never_saved_report(tmp_path):
    report=tmp_path/'report.json'
    command=[sys.executable,'-m','proxydoctor','check','--public-ip','8.8.8.8','--show-ip','--json','--output',str(report)]
    result=subprocess.run(command,capture_output=True,encoding='utf-8')
    assert result.returncode in (0,1)
    assert '8.8.8.8' in result.stdout
    assert '8.8.8.8' not in report.read_text(encoding='utf-8')
