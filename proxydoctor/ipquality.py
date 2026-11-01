"""IP ownership, type and reputation with provenance and explicit missing data."""
from datetime import datetime, timezone
import ipaddress
import os
import urllib.parse

from .net import request_json

FLAGS = ('is_datacenter', 'is_proxy', 'is_vpn', 'is_tor', 'is_abuser',
         'is_mobile', 'is_satellite', 'is_anycast', 'is_bogon')
FIELDS = ('company', 'asn', 'country', 'region', 'city', 'timezone', 'network_type',
          'network_abuser_score') + FLAGS


def valid_ip(value):
    if not isinstance(value,str): return None
    try:
        address = ipaddress.ip_address(value)
        return str(address) if address.is_global else None
    except (ValueError, TypeError):
        return None


def text(value):
    return value[:200] if isinstance(value, str) and value.strip() else None


def normalize(data):
    values = {field: None for field in FIELDS}
    company = data.get('company')
    asn = data.get('asn')
    location = data.get('location') if isinstance(data.get('location'), dict) else data
    if isinstance(company, dict):
        values['company'] = text(company.get('name'))
        values['network_type'] = text(company.get('type'))
        values['network_abuser_score'] = text(company.get('abuser_score'))
    else:
        values['company'] = text(company)
    if isinstance(asn, dict):
        number = asn.get('asn')
        if isinstance(number, int) and not isinstance(number, bool) and number > 0:
            values['asn'] = 'AS' + str(number) + (' ' + text(asn.get('org')) if text(asn.get('org')) else '')
        values['network_type'] = values['network_type'] or text(asn.get('type'))
    else:
        values['asn'] = text(asn)
    for name in ('country', 'region', 'city', 'timezone'):
        values[name] = text(location.get(name))
    for name in FLAGS:
        if type(data.get(name)) is bool:
            values[name] = data[name]
    return values


def normalize_proxycheck(item):
    values={field:None for field in FIELDS}
    network=item.get('network') if isinstance(item.get('network'),dict) else {}
    location=item.get('location') if isinstance(item.get('location'),dict) else {}
    detections=item.get('detections') if isinstance(item.get('detections'),dict) else {}
    values.update(company=text(network.get('provider')),asn=text(network.get('asn')),
                  network_type=text(network.get('type')))
    for target,source in [('country','country_name'),('region','region_name'),('city','city_name'),('timezone','timezone')]:
        values[target]=text(location.get(source))
    for target,source in [('is_datacenter','hosting'),('is_proxy','proxy'),('is_vpn','vpn'),('is_tor','tor')]:
        if type(detections.get(source)) is bool: values[target]=detections[source]
    return values


def normalize_ip2location(item):
    values={field:None for field in FIELDS}
    values['company']=text(item.get('isp')) or text(item.get('as'))
    number=item.get('asn')
    if isinstance(number,(int,str)) and not isinstance(number,bool) and str(number).isdigit():
        values['asn']='AS'+str(number)
    for target,source in [('country','country_name'),('region','region_name'),('city','city_name'),('timezone','time_zone')]:
        values[target]=text(item.get(source))
    # The free plan's proxy flag excludes some VPN types. Do not merge it into
    # the common proxy/VPN flags; keep it as a provider-specific observation.
    return values


def reconcile(report):
    observations=report['observations']
    report['field_sources']={}
    report['conflicts']={}
    for name in FIELDS:
        candidates={source:values[name] for source,values in observations.items() if values.get(name) is not None}
        if name in FLAGS and len(set(candidates.values()))>1:
            report['values'][name]=None
            report['conflicts'][name]=candidates
            report['field_sources'][name]=list(candidates)
        elif candidates:
            first=next(iter(candidates.values()))
            report['values'][name]=first
            report['field_sources'][name]=[source for source,value in candidates.items() if value==first]
    available=sum(value is not None for value in report['values'].values())
    report['coverage']={'available':available,'total':len(FIELDS),
                        'complete':available==len(FIELDS) and report['sources']['AbuseIPDB']['state']=='ok'}


def enrich_report(report):
    address=report['ip']
    if not address: return
    url='https://proxycheck.io/v3/'+urllib.parse.quote(address,safe=':')+'?tag=0&ver=24-June-2026'
    data,state=request_json(url)
    item=None
    if state=='ok':
        if data.get('status')!='ok': state='provider_error'
        else:
            item=next((value for key,value in data.items() if valid_ip(key)==address),None)
            if not isinstance(item,dict) or not isinstance(item.get('detections'),dict):
                state='invalid_response'
    report['sources']['proxycheck.io']={'state':state,'access':'anonymous'}
    if state=='ok':
        report['observations']['proxycheck.io']=normalize_proxycheck(item)
        detections=item['detections']
        risk={key:detections.get(key) if type(detections.get(key)) is int and 0<=detections[key]<=100 else None
              for key in ('risk','confidence')}
        for key in ('anonymous','compromised','scraper'):
            risk[key]=detections.get(key) if type(detections.get(key)) is bool else None
        history=item.get('attack_history')
        risk['attack_count']=sum(history.values()) if isinstance(history,dict) and all(type(n) is int and 0<=n<=2**31 for n in history.values()) else None
        report['provider_risk']['proxycheck.io']=risk
    data,state=request_json('https://api.ip2location.io/?'+urllib.parse.urlencode({'ip':address,'format':'json'}))
    if state=='ok' and valid_ip(data.get('ip'))!=address: state='invalid_response'
    report['sources']['IP2Location']={'state':state,'access':'anonymous'}
    if state=='ok':
        report['observations']['IP2Location']=normalize_ip2location(data)
        report['provider_risk']['IP2Location']={'open_proxy_flag':data.get('is_proxy') if type(data.get('is_proxy')) is bool else None}


def collect(enrich=True):
    """Keys only via environment; never kept in results, URLs or error messages."""
    key = os.environ.get('PROXYDOCTOR_IPAPI_KEY', '').strip()
    abuse_key = os.environ.get('PROXYDOCTOR_ABUSEIPDB_KEY', '').strip()
    data, state = request_json('https://api.ipapi.is/', payload={'key': key} if key else None)
    address = valid_ip(data.get('ip')) if data else None
    if state == 'ok' and (not address or data.get('error')):
        state = 'invalid_response'
    if state != 'ok':
        address = None
    values = normalize(data) if state == 'ok' else {field: None for field in FIELDS}
    missing = [name for name, value in values.items() if value is None]
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'ip': address,
              'ip_family': ipaddress.ip_address(address).version if address else None,
              'scope': 'request_egress_only', 'values': values,
              'sources': {'ipapi.is': {'state': state, 'access': 'key' if key else 'anonymous',
                                      'missing_fields': missing}},
              'reputation': {'score': None, 'total_reports': None, 'distinct_reporters': None,
                             'last_reported_at': None, 'window_days': 90}}
    report['observations']={'ipapi.is':values.copy()}
    report['provider_risk']={}
    if not address and data is None:
        fallback,fallback_state=request_json('https://api.ipify.org?format=json')
        address=valid_ip(fallback.get('ip')) if fallback else None
        if fallback_state=='ok' and not address: fallback_state='invalid_response'
        report['sources']['ipify']={'state':fallback_state}
        report['ip']=address
        report['ip_family']=ipaddress.ip_address(address).version if address else None
    abuse_state = 'key_required' if not abuse_key else 'ip_unavailable'
    if abuse_key and address:
        url = 'https://api.abuseipdb.com/api/v2/check?' + urllib.parse.urlencode(
            {'ipAddress': address, 'maxAgeInDays': 90})
        abuse, abuse_state = request_json(url, headers={'Key': abuse_key})
        item = abuse.get('data') if abuse else None
        if abuse_state == 'ok':
            if not isinstance(item, dict) or valid_ip(item.get('ipAddress')) != address:
                abuse_state = 'invalid_response'
            else:
                for source, target, maximum in [('abuseConfidenceScore', 'score', 100),
                                               ('totalReports', 'total_reports', None),
                                               ('numDistinctUsers', 'distinct_reporters', None)]:
                    value = item.get(source)
                    if type(value) is int and value >= 0 and (maximum is None or value <= maximum):
                        report['reputation'][target] = value
                report['reputation']['last_reported_at'] = text(item.get('lastReportedAt'))
                if any(report['reputation'][k] is None for k in ('score', 'total_reports', 'distinct_reporters')):
                    abuse_state = 'partial_response'
    report['sources']['AbuseIPDB'] = {'state': abuse_state}
    if enrich: enrich_report(report)
    reconcile(report)
    return report


def render(report,out,show_ip=False):
    tr=out.text;values=report['values'];unknown=tr('未知','Unknown')
    address=report['ip']
    out.row(tr('出口地址','Egress IP'),address if address and show_ip else tr('已隐藏（--show-ip 显示）','Hidden (use --show-ip)') if address else unknown,'ok' if address else 'unknown')
    for key,zh,en in [('company','运营商','ISP'),('asn','ASN','ASN'),('country','国家','Country'),
                      ('region','地区','Region'),('city','城市','City'),('timezone','时区','Timezone'),
                      ('network_type','网络类型','Network type'),('network_abuser_score','网段滥用比例','Network abuse share')]:
        value=values.get(key)
        out.row(tr(zh,en),value if value is not None else unknown,'ok' if value is not None else 'unknown')
    labels=[('数据中心','Datacenter'),('代理','Proxy'),('VPN','VPN'),('Tor','Tor'),('近期滥用','Recent abuse'),
            ('移动网络','Mobile'),('卫星','Satellite'),('Anycast','Anycast'),('保留地址','Bogon')]
    for key,(zh,en) in zip(FLAGS,labels):
        value=values.get(key);risk=key in ('is_proxy','is_vpn','is_tor','is_abuser','is_bogon')
        label=tr('来源不一致','Sources disagree') if key in report.get('conflicts',{}) else tr('是','Yes') if value is True else tr('否','No') if value is False else unknown
        out.row(tr(zh,en),label,'unknown' if value is None else 'bad' if risk and value else 'ok')
    pc=report.get('provider_risk',{}).get('proxycheck.io',{})
    risk=pc.get('risk');confidence=pc.get('confidence')
    out.row('proxycheck.io',unknown if risk is None else tr(f'风险分 {risk}/100 · 置信度 {confidence if confidence is not None else "?"}/100',
                                                         f'Risk {risk}/100 · Confidence {confidence if confidence is not None else "?"}/100'),
            'unknown' if risk is None else 'bad' if risk>25 else 'ok')
    reputation=report['reputation'];score=reputation['score']
    out.row('AbuseIPDB',unknown if score is None else tr(
        f"评分 {score}/100 · 90 天举报 {reputation['total_reports']} · 举报者 {reputation['distinct_reporters']}",
        f"Score {score}/100 · 90-day reports {reputation['total_reports']} · Reporters {reputation['distinct_reporters']}"),
        'unknown' if score is None else 'bad' if score>0 else 'ok')
    coverage=report['coverage']
    out.row(tr('IP 数据覆盖','IP data coverage'),f"{coverage['available']}/{coverage['total']} · IPv{report['ip_family'] or '?'}",
            'ok' if coverage['complete'] else 'unknown')
    labels={'ok':('成功','OK'),'key_required':('需要密钥','Key required'),'rate_limited':('限流','Rate limited'),
            'invalid_response':('响应格式异常','Invalid response'),'request_failed':('请求失败','Request failed')}
    for source,item in report['sources'].items():
        state=item['state'];name=labels.get(state,(state,state))[0 if out.lang=='zh' else 1]
        out.row(source+' API',name,'ok' if state=='ok' else 'unknown')
    if not coverage['complete']:
        print(tr('  可选扩展字段：PROXYDOCTOR_IPAPI_KEY；举报数据：PROXYDOCTOR_ABUSEIPDB_KEY。',
                 '  Optional extended fields: PROXYDOCTOR_IPAPI_KEY; reports: PROXYDOCTOR_ABUSEIPDB_KEY.'),flush=True)
