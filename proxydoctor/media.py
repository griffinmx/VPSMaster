"""Conservative, independent media checks. No cookies, accounts or upstream scripts."""
from dataclasses import dataclass
from html.parser import HTMLParser
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .net import read_limited

SERVICES = {
    'Netflix': ('https://www.netflix.com/', ('netflix is not available in your country',
                                           'netflix is not available in your region')),
    'Disney+': ('https://www.disneyplus.com/', ('disney+ is not available in your region',
                                             'disney+ is not available in your country',
                                             'disney plus is not available in your region')),
    'YouTube Premium': ('https://www.youtube.com/premium', ('premium is not available in your country',
                                                         'premium is not available in your region')),
    'Spotify': ('https://www.spotify.com/', ('spotify is currently not available in your country',
                                           'spotify is not available in your country')),
    'Prime Video': ('https://www.primevideo.com/', ('prime video is not available in your location',
                                                  'prime video is not available in your country')),
    'Max': ('https://www.max.com/', ('max is not available in your region',
                                   'max is not available in your country',
                                   'not available in your region yet')),
    'Apple TV+': ('https://tv.apple.com/', ('apple tv is not available in your country',
                                         'apple tv+ is not available in your region')),
    'Hulu': ('https://www.hulu.com/', ('hulu is not available in your region',
                                     'hulu is only available in the u.s.',
                                     'hulu is only available in the united states')),
    'BBC iPlayer': ('https://www.bbc.co.uk/iplayer', ('bbc iplayer only works in the uk',
                                                   'bbc iplayer is only available in the uk')),
    'Paramount+': ('https://www.paramountplus.com/', ('paramount+ is not available in your region',
                                                    'paramount+ is not available in your country')),
}
LIMIT = 4 * 1024 * 1024
BBC_SELECTOR='https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/bbc_one_london/format/json'
REDIRECT_HOSTS = (
    frozenset(('netflix.com','www.netflix.com')),
    frozenset(('disneyplus.com','www.disneyplus.com')),
    frozenset(('www.youtube.com','consent.youtube.com')),
    frozenset(('spotify.com','www.spotify.com','open.spotify.com')),
    frozenset(('max.com','www.max.com','hbomax.com','www.hbomax.com')),
    frozenset(('www.bbc.co.uk','www.bbc.com')),
    frozenset(('hulu.com','www.hulu.com')),
    frozenset(('paramountplus.com','www.paramountplus.com')),
)


@dataclass
class Page:
    status: int | None
    body: str = ''
    reason: str = ''
    url: str = ''


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocked = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        values=dict(attrs)
        style=re.sub(r'\s+','',values.get('style','').lower())
        hidden=('hidden' in values or values.get('aria-hidden','').lower()=='true'
                or 'display:none' in style or 'visibility:hidden' in style)
        if (self.blocked or tag in ('script','style','template') or hidden) and tag not in ('br','img','input','meta','link','hr','source','wbr','area','base','embed','param','track','col'):
            self.blocked.append(tag)

    def handle_endtag(self, tag):
        if tag in self.blocked:
            index=len(self.blocked)-1-self.blocked[::-1].index(tag)
            del self.blocked[index:]

    def handle_data(self, text):
        if not self.blocked: self.parts.append(text)


def fetch_page(url):
    from .worker import enabled,invoke
    if enabled():
        result=invoke('page',{'url':url})
        return Page(**result) if isinstance(result,dict) else Page(None,reason='network_timeout_or_error')
    expected = urllib.parse.urlparse(url).hostname
    allowed = next((hosts for hosts in REDIRECT_HOSTS if expected in hosts),frozenset((expected,)))
    deadline = time.monotonic() + 15
    class SameSiteRedirect(urllib.request.HTTPRedirectHandler):
        max_redirections = 4
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            parsed=urllib.parse.urlparse(newurl)
            if (parsed.scheme!='https' or parsed.hostname not in allowed
                    or parsed.username or parsed.password or parsed.port not in (None,443)
                    or time.monotonic() >= deadline):
                return None
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),SameSiteRedirect())
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 VPSMaster/1.0.0b1','Accept-Language':'en-US,en;q=0.9','Accept-Encoding':'identity'})
    try:
        response=opener.open(req,timeout=8)
    except urllib.error.HTTPError as exc:
        response=exc
    except (ValueError,OSError,urllib.error.URLError):
        return Page(None,reason='network_error')
    try:
        with response:
            body=read_limited(response,LIMIT,deadline)
            return Page(response.code,body.decode('utf-8',errors='replace'),url=response.geturl())
    except ValueError:
        return Page(response.code,reason='response_too_large')
    except OSError:
        return Page(None,reason='read_failed')


def classify(service,page):
    # An HTTP 200, sign-up offer, HTTP 403 or WAF challenge alone is not proof
    # of successful playback or geographical blocking.
    if page.reason:
        return {'state':'unknown','http':page.status,'evidence':page.reason}
    parser=VisibleText()
    parser.feed(page.body)
    text=re.sub(r'\s+',' ',' '.join(parser.parts)).lower()
    # A WAF/login/challenge response cannot establish region or entitlement.
    if page.status in (401,403,407,429,451) or page.status is None or page.status >= 500:
        evidence = {401:'login_required',403:'access_denied',407:'access_denied',
                    429:'rate_limited',451:'legal_restriction'}.get(page.status,'service_error')
        return {'state':'unknown','http':page.status,'evidence':evidence}
    if any(marker in text for marker in ('verify you are human','checking your browser',
                                        'enable javascript and cookies to continue','access denied')):
        return {'state':'unknown','http':page.status,'evidence':'challenge_page'}
    if 'before you continue to youtube' in text:
        return {'state':'unknown','http':page.status,'evidence':'consent_required'}
    if page.status == 200 and any(phrase in text for phrase in SERVICES[service][1]):
        return {'state':'restricted','http':page.status,'evidence':'explicit_region_message'}
    # Only a named subscription offer AND an actual price is positive evidence.
    # This proves an offer is displayed, never that DRM/account playback works.
    offers = {'YouTube Premium': ('get youtube premium','try youtube premium'),
              'Spotify': ('get premium individual','premium individual'),
              'Disney+': ('disney+ premium','disney+ standard'),
              'Hulu': ('hulu (with ads)','hulu (no ads)'),
              'Paramount+': ('paramount+ essential','paramount+ premium')}
    if page.status == 200 and service in offers:
        phrases = offers[service]
        priced_offer = any(re.search(re.escape(phrase) + r'.{0,180}(?:[$€£¥₹]\s*\d|\d[\d.,]*\s*(?:usd|eur|gbp|jpy|inr))',text)
                           or re.search(r'(?:[$€£¥₹]\s*\d|\d[\d.,]*\s*(?:usd|eur|gbp|jpy|inr)).{0,180}' + re.escape(phrase),text)
                           for phrase in phrases)
        if priced_offer:
            return {'state':'offer_available','http':page.status,'evidence':'visible_priced_subscription'}
    return {'state':'unknown','http':page.status,'evidence':'playback_not_verified'}


class StructuredTitles(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.blocks = []
        self.buffer = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type','').lower() == 'application/ld+json':
            self.active = True
            self.buffer = []

    def handle_data(self, data):
        if self.active:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            self.blocks.append(''.join(self.buffer))
            self.active = False


def title_evidence(page, title_id):
    if page.reason or page.status != 200:
        return False
    # Require matching structured title metadata, not arbitrary occurrences of ID.
    parser = StructuredTitles()
    parser.feed(page.body)
    def matches(item):
        if isinstance(item, list):
            return any(matches(part) for part in item)
        if not isinstance(item, dict):
            return False
        types = item.get('@type', [])
        if isinstance(types, str):
            types = [types]
        if any(kind in types for kind in ('TVSeries','Movie','VideoObject')) and item.get('name'):
            parsed = urllib.parse.urlparse(str(item.get('url','')))
            if parsed.scheme == 'https' and parsed.hostname == 'www.netflix.com' and re.search(r'/title/' + title_id + r'/?$',parsed.path):
                return True
        return matches(item.get('@graph', []))
    for block in parser.blocks:
        try:
            if matches(json.loads(block)):
                return True
        except (ValueError, RecursionError):
            continue
    return False


def classify_bbc_metadata(page):
    result={'state':'unknown','http':page.status,'evidence':page.reason or 'unrecognized_metadata'}
    if page.reason or page.status not in (200,403): return result
    try: data=json.loads(page.body)
    except (ValueError,RecursionError): return result
    if not isinstance(data,dict): return result
    if data.get('result')=='geolocation':
        return dict(result,state='restricted',evidence='geo_api')
    # Only acknowledge metadata, without following or retaining signed media URLs.
    media=data.get('media')
    if page.status==200 and isinstance(media,list):
        for item in media:
            if not isinstance(item,dict) or item.get('kind') not in ('video','audio'): continue
            connections=item.get('connection')
            if not isinstance(connections,list): continue
            for connection in connections:
                if not isinstance(connection,dict) or not isinstance(connection.get('href'),str): continue
                try: parsed=urllib.parse.urlparse(connection['href'])
                except ValueError: continue
                if parsed.scheme=='https' and parsed.hostname:
                    return dict(result,state='metadata_available',evidence='channel_metadata')
    return result


def check(service):
    if service=='BBC iPlayer':
        first=classify_bbc_metadata(fetch_page(BBC_SELECTOR))
        if first['state']!='unknown':
            second=classify_bbc_metadata(fetch_page(BBC_SELECTOR))
            return dict(first,service=service,scope='bbc_one_metadata',playback='not_tested',
                        state=first['state'] if first['state']==second['state'] else 'unknown',
                        evidence='confirmed_'+first['evidence'] if first['state']==second['state'] else 'inconsistent_results',
                        checked_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                        probes=[{'url':BBC_SELECTOR,**item} for item in (first,second)])
    url = SERVICES[service][0]
    page = fetch_page(url)
    first = classify(service,page)
    result = dict(first, service=service, scope='public_region_and_offer',
                  playback='not_tested', checked_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                  probes=[{'url':url,'final_url':page.url, **first}])
    if first['state'] in ('restricted','offer_available'):
        page = fetch_page(url)
        second = classify(service,page)
        result['probes'].append({'url':url,'final_url':page.url, **second})
        if second['state'] != first['state']:
            result.update(state='unknown',evidence='inconsistent_results')
        else:
            result['evidence'] = 'confirmed_' + first['evidence']
    elif service == 'Netflix' and first.get('http') == 200 and first['evidence'] == 'playback_not_verified':
        observed = 0
        for title_id in ('80057281','70143836'):
            title_url = url + 'title/' + title_id
            page = fetch_page(title_url)
            found = title_evidence(page,title_id)
            observed += int(found)
            result['probes'].append({'url':title_url,'final_url':page.url,'http':page.status,
                                     'evidence':'structured_catalog_title' if found else page.reason or 'no_title_evidence'})
        if observed:
            result.update(state='catalog_visible',evidence='structured_catalog_titles',catalog_titles_observed=observed)
    return result


def display(result, lang='zh'):
    """Compact human-readable result while raw evidence remains exportable."""
    zh = lang == 'zh'
    state = result.get('state')
    if result.get('scope')=='bbc_one_metadata' and state=='restricted':
        return ('测试频道区域限制（两次一致）' if zh else 'Test channel region restricted (confirmed)'), 'bad'
    labels = {'restricted':('区域限制（两次一致）','Region restricted (confirmed)'),
              'offer_available':('地区套餐可见 · 播放待验证','Regional offer visible · Playback unverified'),
              'catalog_visible':('片库条目可见 · 播放待验证','Catalog visible · Playback unverified'),
              'metadata_available':('测试频道元数据可取 · 播放待验证','Test channel metadata available · Playback unverified')}
    if state in labels:
        return labels[state][0 if zh else 1], 'bad' if state == 'restricted' else 'unknown'
    evidence = result.get('evidence')
    reasons = {'network_error':('连接失败','Request failed'), 'read_failed':('读取失败','Read failed'),
               'response_too_large':('响应超限','Response too large'),
               'access_denied':('访问被拒 · 原因未知','Access denied · Cause unknown'),
               'rate_limited':('触发限流','Rate limited'), 'challenge_page':('遇到人机验证','Challenge page'),
               'consent_required':('需要隐私授权','Consent required'),
               'inconsistent_results':('两次结果不一致','Inconsistent results'),
               'login_required':('需要登录','Login required'),
               'legal_restriction':('法律限制 · 区域原因未确定','Legal restriction · Region unknown')}
    label = reasons.get(evidence, ('解锁未知','Unlock UNKNOWN'))[0 if zh else 1]
    http = result.get('http')
    if http == 403 and evidence == 'playback_not_verified':
        label = '访问被拒 · 原因未知' if zh else 'Access denied · Cause unknown'
    return label + f' · HTTP {http if http is not None else "---"}', 'unknown'


def check_reachability(service):
    """Public page reachability only; no catalogue, region or playback verdict."""
    from .reports import utc_now
    url = SERVICES[service][0]
    started = time.monotonic()
    page = fetch_page(url)
    state = ('reachable' if page.status is not None and 200 <= page.status < 300 and not page.reason else
             'access_denied' if page.status in (401,403,451) else
             'rate_limited' if page.status == 429 else
             'http_error' if page.status is not None else 'unknown')
    return {'service':service,'scope':'public_page_reachability','state':state,
            'http':page.status,'evidence':page.reason or 'http_response',
            'checked_at':utc_now(),'elapsed_ms':round((time.monotonic()-started)*1000,3),
            'playback':'not_tested','unlock':'not_tested',
            'probes':[{'url':url,'final_url':page.url,'http':page.status}]}


def display_reachability(result,lang='zh'):
    zh=lang=='zh'
    labels={'reachable':('网页可达','Web page reachable'),
            'access_denied':('访问受限','Access denied'),
            'rate_limited':('请求限流','Rate limited'),
            'http_error':('HTTP 异常','HTTP error'),
            'unknown':('可达性未确认','Reachability unconfirmed')}
    state=result.get('state','unknown')
    label=labels.get(state,labels['unknown'])[0 if zh else 1]
    return label+' · HTTP '+str(result.get('http') or '---'), 'ok' if state=='reachable' else 'unknown'


def run_console(lang='zh', color='auto', results=None, on_result=None, *, out=None):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .console import Console
    out = out if out is not None else Console(lang,color)
    results = {} if results is None else results
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(check_reachability,service):service for service in SERVICES}
        for future in as_completed(futures):
            service = futures[future]
            try:
                result = future.result()
            except Exception:
                # Never echo raw provider exceptions (URLs may include sensitive data).
                result = {'state':'unknown','http':None,'evidence':'network_error','playback':'not_tested'}
            results[service] = result
            if on_result is not None:
                on_result()
            value, status = display_reachability(result,lang)
            out.row(service,value,status)
    return results
