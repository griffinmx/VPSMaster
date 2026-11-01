import io
import json

from proxydoctor.console import Console
from proxydoctor.geo import GeoLocator


def test_colour_can_be_forced_or_disabled():
    assert '\x1b[32m' in Console(color='always').paint('2 CPUs')
    assert '\x1b[31m' in Console(color='always').paint('Restricted','bad')
    assert '\x1b' not in Console(color='never').paint('2 CPUs')
    assert '\x1b' not in Console(color='never').paint('\x1b[31mmalicious')


def test_private_hops_never_query_geolocation(monkeypatch):
    monkeypatch.setattr('proxydoctor.geo.urllib.request.build_opener',lambda *args: (_ for _ in ()).throw(AssertionError()))
    assert '内网' in GeoLocator().lookup('192.168.1.1')
    assert '内网' in GeoLocator().lookup('100.64.0.1')


def test_public_hop_location_cached_and_deduplicated(monkeypatch):
    calls=[]
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,size): return json.dumps({'success':True,'country':'Test country','region':'Test city','city':'Test city'}).encode()
    class Opener:
        def open(self,url,timeout): calls.append(url);return Response()
    monkeypatch.setattr('proxydoctor.geo.urllib.request.build_opener',lambda *args:Opener())
    geo=GeoLocator()
    assert geo.lookup('20.150.176.1')=='Test country / Test city'
    assert geo.lookup('20.150.176.1')=='Test country / Test city'
    assert len(calls)==1
