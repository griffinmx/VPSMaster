"""Best-effort IP database location, not physical-location verification."""
import ipaddress
import json
import urllib.error
import urllib.request


class GeoLocator:
    def __init__(self, lang='zh', enabled=True):
        self.lang,self.enabled,self.cache=lang,enabled,{}

    def lookup(self,address):
        addr=ipaddress.ip_address(address)
        if not addr.is_global:
            return '内网/保留地址' if self.lang=='zh' else 'Private/reserved'
        unknown='位置未知' if self.lang=='zh' else 'Unknown location'
        if not self.enabled: return unknown
        if address in self.cache: return self.cache[address]
        result=unknown
        from .worker import enabled
        if enabled():
            from .net import request_json
            language='zh-CN' if self.lang=='zh' else 'en'
            data,state=request_json('https://ipwho.is/'+str(addr)+'?lang='+language)
            if state=='ok' and data.get('success') is True:
                values=list(dict.fromkeys(data[k] for k in ('country','region','city') if isinstance(data.get(k),str) and data[k]))
                if values:result=' / '.join(values)
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
                if isinstance(data,dict) and data.get('success') is True:
                    location=[data.get(k) for k in ('country','region','city')]
                    values=list(dict.fromkeys(v for v in location if isinstance(v,str) and v))
                    if values: result=' / '.join(values)
        except urllib.error.HTTPError as exc:
            if exc.code==429: self.enabled=False
            exc.close()
        except (OSError,ValueError,urllib.error.URLError): pass
        self.cache[address]=result
        return result
