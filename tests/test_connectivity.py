"""Dual-stack fixtures; added without running tests in this batch."""
import json
import socket
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from proxydoctor import connectivity


def test_dns_negative_answer_and_timeout_remain_unknown():
    with patch.object(connectivity.subprocess, 'run', return_value=SimpleNamespace(
            returncode=0, stdout=json.dumps({'error':socket.EAI_NONAME}))):
        assert connectivity.dns_probe(6)['error_code'] == 'DNS_NO_ADDRESS'
    with patch.object(connectivity.subprocess, 'run', side_effect=connectivity.subprocess.TimeoutExpired('resolver',2)):
        assert connectivity.dns_probe(4)['error_code'] == 'DNS_TIMEOUT'


def test_dns_rejects_wrong_family_answers():
    with patch.object(connectivity.subprocess, 'run', return_value=SimpleNamespace(
            returncode=0, stdout=json.dumps({'addresses':['1.1.1.1']}))):
        assert connectivity.dns_probe(6)['error_code'] == 'DNS_INVALID_RESPONSE'


def test_tcp_success_is_preserved_when_tls_certificate_fails():
    from contextlib import nullcontext
    raw = SimpleNamespace(settimeout=lambda value: None)
    context = SimpleNamespace(wrap_socket=lambda *args,**kwargs: (_ for _ in ()).throw(
        connectivity.ssl.SSLCertVerificationError('sensitive provider text')))
    with patch.object(connectivity.socket,'create_connection',return_value=nullcontext(raw)), \
         patch.object(connectivity.ssl,'create_default_context',return_value=context):
        result = connectivity.transport_probe('test','example.com','1.1.1.1')
    assert result['tcp']['status'] == 'success'
    assert result['tls']['error_code'] == 'TLS_CERTIFICATE_ERROR'
    assert 'sensitive' not in json.dumps(result)


def test_family_results_and_sample_counts_remain_separate():
    def dns(version):
        return {'family':version,'status':'success' if version==4 else 'unknown','elapsed_ms':1}
    def transport(label,hostname,address):
        version = connectivity.ipaddress.ip_address(address).version
        return {'family':version,'target':label,'tcp':{'status':'success'},'tls':{'status':'unknown'}}
    snapshots = []
    report = {}
    connectivity.collect(report, lambda: snapshots.append(json.dumps(report)), dns=dns, transport=transport)
    assert report['dns_summary']['4']['success_ratio'] == 1
    assert report['dns_summary']['6']['success_ratio'] == 0
    assert report['diagnostics'][1]['code'] == 'DNS_FAILED_NUMERIC_TCP_WORKS'
    assert report['status'] == 'partial'
    assert len(snapshots) == 9


def test_one_probe_exception_does_not_drop_other_targets():
    def dns(version):
        raise RuntimeError('token=secret')
    def transport(label,hostname,address):
        return {'family':connectivity.ipaddress.ip_address(address).version,
                'target':label,'tcp':{'status':'success'},'tls':{'status':'success'}}
    report = connectivity.collect(dns=dns, transport=transport)
    assert len(report['transports']) == 4
    assert 'secret' not in json.dumps(report)


def test_ctrl_c_is_not_swallowed_by_probe_isolation():
    def dns(version):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        connectivity.collect(dns=dns)
