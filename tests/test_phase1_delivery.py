import json
import socket
import struct

from proxydoctor import ipquality as iq, media, routes, suite


def test_keyless_risk_sources_preserve_disagreement_and_identity(monkeypatch):
    monkeypatch.delenv('PROXYDOCTOR_ABUSEIPDB_KEY',raising=False)
    monkeypatch.delenv('PROXYDOCTOR_IPAPI_KEY',raising=False)
    calls=[]
    def request(url,**kwargs):
        calls.append(url)
        if 'api.ipapi.is' in url: return {'ip':'8.8.8.8','is_proxy':False,'company':'Primary'},'ok'
        if 'proxycheck.io' in url:
            return {'status':'ok','8.8.8.8':{'network':{'type':'Hosting','asn':'AS15169'},
                    'detections':{'proxy':True,'vpn':False,'hosting':True,'tor':False,'risk':33,'confidence':90},
                    'attack_history':{'login_attempt':2}}},'ok'
        return {'ip':'1.1.1.1','country_name':'Wrong IP','is_proxy':False},'ok'
    monkeypatch.setattr(iq,'request_json',request)
    result=iq.collect()
    assert len(calls)==3
    assert result['values']['is_proxy'] is None
    assert result['conflicts']['is_proxy']=={'ipapi.is':False,'proxycheck.io':True}
    assert result['values']['is_datacenter'] is True
    assert result['values']['company']=='Primary'
    assert result['field_sources']['is_vpn']==['proxycheck.io']
    assert result['provider_risk']['proxycheck.io']['risk']==33
    assert result['provider_risk']['proxycheck.io']['attack_count']==2
    assert result['sources']['IP2Location']['state']=='invalid_response'
    assert 'Wrong IP' not in json.dumps(result)


def test_egress_fallback_then_keyless_sources_do_not_change_target(monkeypatch):
    monkeypatch.delenv('PROXYDOCTOR_ABUSEIPDB_KEY',raising=False)
    def request(url,**kwargs):
        if 'ipapi' in url: return None,'rate_limited'
        if 'ipify' in url: return {'ip':'8.8.8.8'},'ok'
        if 'proxycheck' in url: return None,'rate_limited'
        assert 'ip=8.8.8.8' in url
        return {'ip':'8.8.8.8','country_name':'Example','asn':'15169','is_proxy':False},'ok'
    monkeypatch.setattr(iq,'request_json',request)
    result=iq.collect()
    assert result['ip']=='8.8.8.8' and result['values']['country']=='Example'
    assert result['values']['is_proxy'] is None  # A limited open-proxy flag is not a general guarantee.
    assert result['sources']['proxycheck.io']['state']=='rate_limited'
    assert result['provider_risk']['IP2Location']['open_proxy_flag'] is False


def test_malformed_provider_risk_does_not_invent_values():
    assert iq.valid_ip(134744072) is None
    values=iq.normalize_proxycheck({'detections':{'proxy':'false','hosting':0}})
    assert values['is_proxy'] is None and values['is_datacenter'] is None


def test_bbc_geo_json_needs_repeat_and_does_not_fetch_media(monkeypatch):
    calls=[]
    def page(url):
        calls.append(url)
        return media.Page(403,json.dumps({'result':'geolocation'}))
    monkeypatch.setattr(media,'fetch_page',page)
    result=media.check('BBC iPlayer')
    assert result['state']=='restricted' and result['scope']=='bbc_one_metadata'
    assert result['playback']=='not_tested'
    assert calls==[media.BBC_SELECTOR]*2
    assert media.classify_bbc_metadata(media.Page(403,'Access denied geolocation'))['state']=='unknown'


def test_bbc_metadata_does_not_export_signed_stream_url(monkeypatch):
    page=media.Page(200,json.dumps({'media':[{'kind':'video','connection':[{'href':'https://media.example/live.m3u8?token=private'}]}]}))
    monkeypatch.setattr(media,'fetch_page',lambda url:page)
    result=media.check('BBC iPlayer')
    assert result['state']=='metadata_available' and result['playback']=='not_tested'
    assert 'private' not in json.dumps(result)


def test_ipv6_trace_uses_icmp6_error_queue_and_exports_hop(monkeypatch):
    monkeypatch.setattr(routes.sys,'platform','linux')
    monkeypatch.setattr(routes.GeoLocator,'lookup',lambda self,ip:'Estimated place')
    target='2606:4700:4700::1111'
    seen=[]
    class Socket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def setsockopt(self,*args):seen.append(args)
        def setblocking(self,*args):pass
        def sendto(self,data,destination):self.destination=destination
        def recvmsg(self,*args):
            extended=struct.pack('=IBBBBII',111,3,1,4,0,0,0)
            offender=struct.pack('=HHI',socket.AF_INET6,0,0)+socket.inet_pton(socket.AF_INET6,target)+b'\x00'*4
            return b'',[(socket.IPPROTO_IPV6,25,extended+offender)],0,self.destination
    monkeypatch.setattr(routes.socket,'socket',lambda family,kind:Socket())
    records=[]
    assert routes.trace(target,records=records,emit=lambda *a,**k:None)==0
    assert (socket.IPPROTO_IPV6,25,1) in seen
    assert records[0]['ip']==target and records[0]['state']=='reached'


def test_suite_includes_security_network_and_route_evidence(monkeypatch,tmp_path,capsys):
    from test_suite import unavailable_bandwidth,unavailable_ip
    monkeypatch.setattr(suite,'measure_bandwidth',unavailable_bandwidth)
    monkeypatch.setattr(suite,'collect_ipquality',unavailable_ip)
    monkeypatch.setattr(suite,'run_media',lambda *args:{'Netflix':{'state':'unknown','playback':'not_tested'}})
    def network(*args,**kwargs):kwargs['report'].update(dns={'status':'pass'},tcp=[]);return 0
    monkeypatch.setattr(suite,'run_quality',network)
    def trace(*args,**kwargs):kwargs['records'].append({'hop':1,'ip':'8.8.8.8','latency_ms':2});return 0
    monkeypatch.setattr(suite,'native_trace',trace)
    path=tmp_path/'suite.json'
    assert suite.run_suite(lang='en',port=2222,json_output=path)==1
    result=json.loads(path.read_text(encoding='utf-8'))
    output=capsys.readouterr().out
    assert 'SSH port guard' in output and 'Local port 2222' in output
    assert result['schema_version']==2 and result['target_port']==2222
    assert result['network']['dns']['status']=='pass'
    assert result['route']['state']=='reached'
    assert result['route']['hops'][0]['ip']!='8.8.8.8'
    assert result['summary']['playback']=='not_tested'
