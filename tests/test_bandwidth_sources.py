import io

import pytest

from proxydoctor import bandwidth as bw


class Response(io.BytesIO):
    def __init__(self,body,status=206,headers=None):
        super().__init__(body)
        self.status=status
        self.headers=headers or {}


def fake_response(monkeypatch,response):
    requests=[]
    class Opener:
        def open(self,request,timeout):
            requests.append(request)
            return response
    monkeypatch.setattr(bw,'opener',lambda:Opener())
    return requests


@pytest.mark.parametrize('source',['hetzner-fsn','ovh-rbx'])
def test_official_download_sources_use_exact_validated_range(monkeypatch,source):
    clock=iter(range(10))
    monkeypatch.setattr(bw.time,'monotonic',lambda:next(clock))
    requests=fake_response(monkeypatch,Response(b'x'*100,headers={'Content-Range':'bytes 0-99/104857600','Content-Length':'100'}))
    sample=bw.transfer('download',100,source)
    assert sample.mbps is not None and sample.error is None
    assert sample.source==source
    assert requests[0].get_header('Range')=='bytes=0-99'
    assert requests[0].full_url==bw.SOURCES[source].download_url


def test_ignored_range_never_reads_full_large_file(monkeypatch):
    class FullFile(Response):
        def read1(self,*args): raise AssertionError('Must not read a full-file response')
        def read(self,*args): raise AssertionError('Must not read a full-file response')
    fake_response(monkeypatch,FullFile(b'',status=200))
    sample=bw.transfer('download',100,'hetzner-fsn')
    assert sample.error=='range_not_supported' and sample.mbps is None


@pytest.mark.parametrize('range_header,length',[
    ('bytes 1-100/104857600','100'),('bytes 0-100/104857600','100'),
    ('bytes 0-99/99','100'),('bytes 0-99/*','100'),('', '100'),
    ('bytes 0-99/104857600','101'),
])
def test_wrong_content_range_never_becomes_speed(monkeypatch,range_header,length):
    fake_response(monkeypatch,Response(b'x'*100,headers={'Content-Range':range_header,'Content-Length':length}))
    sample=bw.transfer('download',100,'ovh-rbx')
    assert sample.mbps is None and sample.error=='invalid_content_range'


def test_partial_payload_and_html_cannot_be_valid_samples(monkeypatch):
    fake_response(monkeypatch,Response(b'x'*99,headers={'Content-Range':'bytes 0-99/104857600'}))
    assert bw.transfer('download',100,'ovh-rbx').error=='short_response'
    fake_response(monkeypatch,Response(b'x'*100,headers={'Content-Range':'bytes 0-99/104857600','Content-Type':'text/html'}))
    assert bw.transfer('download',100,'hetzner-fsn').error=='unexpected_content'


@pytest.mark.parametrize('source',['hetzner-fsn','ovh-rbx'])
def test_download_only_never_attempts_upload(monkeypatch,source):
    monkeypatch.setattr(bw,'opener',lambda:pytest.fail('Unexpected upload request'))
    assert bw.transfer('upload',100,source).error=='unsupported'


def test_multiple_sources_stay_separate_with_correct_budget(monkeypatch):
    calls=[];events=[];samples=[]
    def transfer(direction,size,source='cloudflare'):
        calls.append((source,direction,size))
        speed={'cloudflare':10,'hetzner-fsn':30,'ovh-rbx':50}[source]
        return bw.Sample(direction,size,2,speed,source=source)
    monkeypatch.setattr(bw,'transfer',transfer)
    report=bw.measure_many(sources=tuple(bw.SOURCES),on_source=lambda *args:events.append(args[:2]),on_sample=lambda *args:samples.append(args))
    assert report['payload_budget_bytes']==int(48.5*1024**2)
    assert len(calls)==16 and len(samples)==12
    assert report['sources']['hetzner-fsn']['directions']['download']['median_mbps']==30
    assert report['sources']['ovh-rbx']['directions']['download']['median_mbps']==50
    assert 'upload' not in report['sources']['ovh-rbx']['directions']
    assert 'median_mbps' not in report and bw.is_complete(report)
    assert events==[(s,event) for s in bw.SOURCES for event in ('start','complete')]


def test_failed_source_is_not_silently_replaced_and_next_source_runs(monkeypatch):
    calls=[]
    def transfer(direction,size,source='cloudflare'):
        calls.append(source)
        return bw.Sample(direction,size,2,20 if source=='ovh-rbx' else None,
                         error=None if source=='ovh-rbx' else 'range_not_supported',source=source)
    monkeypatch.setattr(bw,'transfer',transfer)
    report=bw.measure_many(sources=['hetzner-fsn','ovh-rbx'])
    assert calls.count('hetzner-fsn')==1
    assert report['sources']['hetzner-fsn']['directions']['download']['successful']==0
    assert report['sources']['ovh-rbx']['directions']['download']['successful']==3
    assert not bw.is_complete(report)


def test_source_selection_deduplicates_and_rejects_arbitrary_urls():
    assert bw.source_ids()==('cloudflare','ovh-rbx')
    assert bw.payload_budget(3,4)==int(36.375*1024**2)
    assert bw.source_ids(['ovh-rbx','ovh-rbx'])==('ovh-rbx',)
    assert bw.payload_budget(3,4,['ovh-rbx'])==int(12.125*1024**2)
    for selected in ([],['https://example.com/'],['not-a-source']):
        with pytest.raises(ValueError): bw.source_ids(selected)


def test_console_reports_download_only_without_calling_it_failed(monkeypatch,capsys):
    monkeypatch.setattr(bw,'transfer',lambda direction,size,source='cloudflare':bw.Sample(direction,size,2,12,source=source))
    bw.run_console('en','always',sources=['ovh-rbx'])
    output=capsys.readouterr().out
    assert 'OVHcloud' in output and 'FR / Roubaix' in output
    assert 'Not supported (download-only source)' in output
    assert 'Download summary' in output and 'Upload summary' not in output
    assert '\x1b[32m' in output
