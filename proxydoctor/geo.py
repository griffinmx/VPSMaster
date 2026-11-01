"""Best-effort IP database location, not physical-location verification."""
import ipaddress
import json
import urllib.error
import urllib.request
from .console import clean
from .reports import utc_now


class GeoLocator:
    def __init__(self, lang='zh', enabled=True):
        self.lang,self.enabled,self.cache=lang,enabled,{}
        self.metadata={}
        self.lookups=0

    def remember(self,address,data):
        values=list(dict.fromkeys(clean(data[k])[:160] for k in ('country','region','city') if isinstance(data.get(k),str) and data[k]))
        connection=data.get('connection') if isinstance(data.get('connection'),dict) else {}
        asn=connection.get('asn')
        if type(asn) is not int or not 1<=asn<=4294967295:asn=None
        operator=connection.get('isp') or connection.get('org')
        self.metadata[address]={'asn':asn,'operator':clean(operator)[:160] if isinstance(operator,str) else None,
                                'source':'https://ipwho.is/','observed_at':utc_now(),'geography':'database_estimate'}
        return ' / '.join(values) if values else ('位置未知' if self.lang=='zh' else 'Unknown location')

    def details(self,address):
        location=self.lookup(address)
        return {'location':location,**self.metadata.get(address,{'asn':None,'operator':None,'source':None,'geography':'unconfirmed'})}

    def lookup(self,address):
        addr=ipaddress.ip_address(address)
        if not addr.is_global:
            return '内网/保留地址' if self.lang=='zh' else 'Private/reserved'
        unknown='位置未知' if self.lang=='zh' else 'Unknown location'
        if not self.enabled: return unknown
        if address in self.cache: return self.cache[address]
        if self.lookups>=12:return unknown
        self.lookups+=1
        result=unknown
        from .worker import enabled
        if enabled():
            from .net import request_json
            language='zh-CN' if self.lang=='zh' else 'en'
            data,state=request_json('https://ipwho.is/'+str(addr)+'?lang='+language)
            if state=='rate_limited':self.enabled=False
            if state=='ok' and data.get('success') is True and data.get('ip',str(addr))==str(addr):
                result=self.remember(address,data)
            self.cache[address]=result
            return result
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args): return None
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
            language='zh-CN' if self.lang=='zh' else 'en'
            with opener.open('https://ipwho.is/'+str(addr)+'?lang='+language,timeout=2) as response:
                payload=response.read(16385)
            if len(payload)<=16384:
                data=json.loads(payload)
                if isinstance(data,dict) and data.get('success') is True and data.get('ip',str(addr))==str(addr):
                    result=self.remember(address,data)
        except urllib.error.HTTPError as exc:
            if exc.code==429: self.enabled=False
            exc.close()
        except (OSError,ValueError,urllib.error.URLError): pass
        self.cache[address]=result
        return result
