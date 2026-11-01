import io
import json
import urllib.error

import pytest

from proxydoctor import bandwidth as bw, ipquality as iq, media, net


def test_bandwidth_median_excludes_failures_and_marks_insufficient():
    samples=[bw.Sample('download',1024,2,10),bw.Sample('download',1024,3,30),
             bw.Sample('download',1024,error='request_failed')]
    result=bw.summarize(samples)
    assert result['median_mbps']==20 and result['successful']==2
    assert result['quality']=='insufficient'
    assert result['min_mbps']==10 and result['max_mbps']==30


def test_fast_and_variable_samples_are_not_claimed_consistent():
    assert bw.summarize([bw.Sample('download',1024,.1,10)]*3)['quality']=='short_samples'
    assert bw.summarize([bw.Sample('download',1024,2,n) for n in (10,20,100)])['quality']=='variable'
    assert bw.summarize([bw.Sample('download',1024,2,n) for n in (10,11,12)])['quality']=='consistent'


def test_warmups_are_excluded_and_each_round_streamed(monkeypatch):
    calls=[];emitted=[]
    def transfer(direction,size):
        calls.append((direction,size))
        return bw.Sample(direction,size,2,999 if size==131072 else 12)
    monkeypatch.setattr(bw,'transfer',transfer)
    result=bw.measure(rounds=3,sample_mib=4,on_sample=lambda *args:emitted.append(args))
    assert len(calls)==8 and len(emitted)==6
    assert result['directions']['download']['median_mbps']==12
    assert result['payload_budget_bytes']==int(24.25*1024**2)


def test_provider_refusal_stops_further_transfers(monkeypatch):
    calls=[]
    def transfer(direction,size):
        calls.append(direction)
        return bw.Sample(direction,size,error='http_429')
    monkeypatch.setattr(bw,'transfer',transfer)
    result=bw.measure()
    assert calls==['download','upload']
    assert result['directions']['download']['successful']==0


@pytest.mark.parametrize('rounds,size',[(2,4),(9,4),(3,0),(3,21)])
def test_traffic_limits_validated(rounds,size):
    with pytest.raises(ValueError): bw.measure(rounds,size)


def test_anonymous_missing_flags_never_become_false(monkeypatch):
    monkeypatch.delenv('PROXYDOCTOR_IPAPI_KEY',raising=False)
    monkeypatch.delenv('PROXYDOCTOR_ABUSEIPDB_KEY',raising=False)
    monkeypatch.setattr(iq,'request_json',lambda *a,**k:({'ip':'8.8.8.8','company':'Example','country':'US'},'ok'))
    result=iq.collect()
    assert result['values']['is_proxy'] is None
    assert result['sources']['AbuseIPDB']['state']=='key_required'
    assert result['coverage']['complete'] is False


def test_keys_are_never_in_result_or_urls_and_abuse_ip_must_match(monkeypatch):
    monkeypatch.setenv('PROXYDOCTOR_IPAPI_KEY','secret-one')
    monkeypatch.setenv('PROXYDOCTOR_ABUSEIPDB_KEY','secret-two')
    calls=[]
    def request(url,**kwargs):
        calls.append((url,kwargs))
        return ({'ip':'8.8.8.8','is_vpn':'false'},'ok') if 'ipapi.is' in url else ({'data':{'ipAddress':'1.1.1.1','abuseConfidenceScore':0}},'ok')
    monkeypatch.setattr(iq,'request_json',request)
    result=iq.collect()
    assert calls[0][1]['payload']=={'key':'secret-one'}
    assert calls[1][1]['headers']=={'Key':'secret-two'}
    assert all('secret' not in url for url,_ in calls)
    assert 'secret' not in json.dumps(result)
    assert result['values']['is_vpn'] is None
    assert result['reputation']['score'] is None
    assert result['sources']['AbuseIPDB']['state']=='invalid_response'


def test_full_ip_and_abuse_response_with_zero_reports_is_preserved(monkeypatch):
    monkeypatch.setenv('PROXYDOCTOR_IPAPI_KEY','key')
    monkeypatch.setenv('PROXYDOCTOR_ABUSEIPDB_KEY','key')
    fixture={'ip':'8.8.8.8','company':{'name':'Example','type':'business','abuser_score':'0 (Very Low)'},
             'asn':{'asn':15169,'org':'Example'},'location':{'country':'US','region':'CA','city':'Test','timezone':'Etc/UTC'},
             **dict.fromkeys(iq.FLAGS,False)}
    def request(url,**kwargs):
        return (fixture,'ok') if 'ipapi.is' in url else ({'data':{'ipAddress':'8.8.8.8','abuseConfidenceScore':0,
                          'totalReports':0,'numDistinctUsers':0,'lastReportedAt':None}},'ok')
    monkeypatch.setattr(iq,'request_json',request)
    result=iq.collect()
    assert result['coverage']['complete'] is True
    assert result['reputation']['score']==0
    assert result['reputation']['last_reported_at'] is None


def test_private_egress_does_not_trigger_abuse_lookup(monkeypatch):
    monkeypatch.setenv('PROXYDOCTOR_ABUSEIPDB_KEY','key')
    calls=[]
    monkeypatch.setattr(iq,'request_json',lambda url,**kw:calls.append(url) or ({'ip':'127.0.0.1'},'ok'))
    result=iq.collect()
    assert result['sources']['ipapi.is']['state']=='invalid_response'
    assert len(calls)==1


def test_region_needs_repeat_confirmation(monkeypatch):
    responses=iter([media.Page(200,'Netflix is not available in your country'),media.Page(200,'Welcome')])
    monkeypatch.setattr(media,'fetch_page',lambda url:next(responses))
    result=media.check('Netflix')
    assert result['state']=='unknown' and result['evidence']=='inconsistent_results'
    assert result['playback']=='not_tested' and len(result['probes'])==2


def test_priced_offer_needs_visible_specific_evidence_and_is_not_playback(monkeypatch):
    page=media.Page(200,'<h1>Get YouTube Premium</h1><p>$13.99 / month</p>')
    monkeypatch.setattr(media,'fetch_page',lambda url:page)
    result=media.check('YouTube Premium')
    assert result['state']=='offer_available' and result['playback']=='not_tested'
    assert result['evidence']=='confirmed_visible_priced_subscription'
    assert media.classify('YouTube Premium',media.Page(200,'YouTube Premium'))['state']=='unknown'
    assert media.classify('YouTube Premium',media.Page(200,'<script>Get YouTube Premium $13.99</script>'))['state']=='unknown'


def test_waf_never_becomes_region_or_offer():
    assert media.classify('Netflix',media.Page(403,'Netflix is not available in your country'))['state']=='unknown'
    assert media.classify('YouTube Premium',media.Page(200,'Verify you are human. Get YouTube Premium $10'))['state']=='unknown'


def test_netflix_structured_title_is_catalog_only(monkeypatch):
    def page(url):
        if '/title/' not in url: return media.Page(200,'Welcome')
        body=json.dumps({'@context':'https://schema.org','@type':'TVSeries','name':'Example','url':url})
        return media.Page(200,'<script type="application/ld+json">'+body+'</script>')
    monkeypatch.setattr(media,'fetch_page',page)
    result=media.check('Netflix')
    assert result['state']=='catalog_visible' and result['catalog_titles_observed']==2
    assert result['playback']=='not_tested'
    assert not media.title_evidence(media.Page(200,'80057281 TVSeries'), '80057281')
    assert not media.title_evidence(media.Page(200,'<script type="application/ld+json">{"@type":"TVSeries","name":"X","url":"https://evil.com/title/80057281"}</script>'),'80057281')


def test_json_transport_error_does_not_echo_provider_body_or_key(monkeypatch):
    class Opener:
        def open(self,*args,**kwargs):
            raise urllib.error.HTTPError('https://api.example/?secret',429,'secret',{},io.BytesIO(b'secret'))
    monkeypatch.setattr(net,'opener',lambda:Opener())
    assert net.request_json('https://api.example',headers={'Key':'secret'})==(None,'rate_limited')


def test_bounded_read_rejects_oversize_and_deadline():
    with pytest.raises(ValueError): net.read_limited(io.BytesIO(b'12345'),4,float('inf'))
    with pytest.raises(TimeoutError): net.read_limited(io.BytesIO(b'1'),4,0)


def test_media_redirects_only_allow_explicit_https_canonical_hosts(monkeypatch):
    import urllib.request
    seen=[]
    class Response(io.BytesIO):
        code=200
        def geturl(self): return 'https://www.max.com/'
    class Opener:
        def open(self,request,timeout): return Response(b'<p>Welcome</p>')
    def build(*handlers):
        seen.extend(handlers)
        return Opener()
    monkeypatch.setattr(media.urllib.request,'build_opener',build)
    media.fetch_page('https://www.max.com/')
    handler=next(h for h in seen if isinstance(h,urllib.request.HTTPRedirectHandler))
    request=urllib.request.Request('https://www.max.com/')
    for url in ('http://www.max.com/','https://www.max.com.evil.test/','https://evil.test/',
                'https://www.max.com:444/','https://name:password@www.max.com/'):
        assert handler.redirect_request(request,None,302,'',{},url) is None
    redirected=handler.redirect_request(request,None,302,'',{},'https://www.hbomax.com/')
    assert redirected.full_url=='https://www.hbomax.com/'


def test_media_console_failure_does_not_abort_other_services(monkeypatch,capsys):
    monkeypatch.setattr(media,'SERVICES',{'Netflix':None,'Spotify':None})
    def check(name):
        if name=='Netflix': raise RuntimeError('private response data')
        return {'state':'restricted','http':200,'evidence':'confirmed_explicit_region_message'}
    monkeypatch.setattr(media,'check',check)
    results=media.run_console('en','always')
    output=capsys.readouterr().out
    assert len(results)==2 and '\x1b[31m' in output
    assert 'private response data' not in output


def test_offline_json_stays_local_and_cannot_overwrite(tmp_path):
    from proxydoctor.suite import run_suite
    path=tmp_path/'result.json'
    assert run_suite(offline=True,json_output=path)==0
    result=json.loads(path.read_text(encoding='utf-8'))
    assert result['offline'] and result['bandwidth'] is None and result['media']=={}
    assert result['result']=='local_execution_complete'
    original=path.read_bytes()
    with pytest.raises(FileExistsError): run_suite(offline=True,json_output=path)
    assert path.read_bytes()==original
