import json
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from proxydoctor import mailquality


def test_mail_checks_keep_forward_mismatch_and_no_blacklist_claim():
    report=mailquality.collect('8.8.8.8',query=lambda mode,ip:{'status':'observed','forward_matches':False} if mode=='ptr' else {'status':'unknown'})
    assert report['ptr']['forward_matches'] is False
    assert report['dnsbl']['status']=='skipped'
    assert 'score' not in report


def test_mail_missing_ip_does_not_probe():
    def unexpected(*args):raise AssertionError('No target')
    assert mailquality.collect(None,query=unexpected)['ptr']['status']=='skipped'


@pytest.mark.parametrize('address',['127.0.0.1','192.168.1.1','not-ip'])
def test_probe_rejects_non_public_target(address):
    with pytest.raises(ValueError):mailquality.probe('ptr',address)


def test_probe_timeout_stays_unknown_without_exception_details():
    with patch.object(mailquality.subprocess,'run',side_effect=subprocess.TimeoutExpired('secret',5)):
        row=mailquality.probe('ptr','8.8.8.8')
    assert row['error_code']=='PROBE_TIMEOUT'
    assert 'secret' not in json.dumps(row)


def test_ptr_failure_does_not_drop_smtp_probe():
    calls=[]
    def query(mode,ip):
        calls.append(mode)
        if mode=='ptr':raise RuntimeError('secret')
        return {'status':'reachable'}
    result=mailquality.collect('8.8.8.8',query=query)
    assert calls==['ptr','smtp']
    assert result['smtp_tcp']['status']=='reachable'
