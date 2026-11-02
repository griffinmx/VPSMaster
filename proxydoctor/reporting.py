"""Offline, escaped Markdown exports and conservative sharing redaction."""
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

from .reports import exclusive_text

SENSITIVE = re.compile(r'password|passwd|token|secret|api[_-]?key|private[_-]?key|authorization|cookie|subscription',re.I)


def sharing_copy(value, lang='zh'):
    from .cli import redact
    hidden = '[已隐藏]' if lang == 'zh' else '[REDACTED]'
    def walk(item):
        if isinstance(item,dict):
            return {key:hidden if SENSITIVE.search(str(key)) else walk(val) for key,val in item.items()}
        if isinstance(item,list):
            return [walk(val) for val in item]
        if not isinstance(item,str):
            return item
        def url(match):
            try:
                parsed = urlsplit(match[0])
                # Remove userinfo and all query/fragment values, including signed URLs.
                netloc = parsed.netloc.rsplit('@',1)[-1]
                return urlunsplit((parsed.scheme,netloc,parsed.path,'',''))
            except ValueError:
                return hidden
        item = re.sub(r'https?://[^\s<>"\']+',url,item)
        item = re.sub(r'(?i)\bBearer\s+\S+', 'Bearer '+hidden,item)
        item = re.sub(r'(?i)\b(password|token|secret|api[_-]?key)\s*[=:]\s*[^\s;,]+',lambda m:m[1]+'='+hidden,item)
        return item
    return redact(walk(value),lang)


def load_report(path, max_bytes=8*1024**2):
    with Path(path).open('rb') as stream:
        body = stream.read(max_bytes+1)
    if len(body)>max_bytes:
        raise ValueError('Report exceeds size limit')
    data = json.loads(body.decode('utf-8'))
    if not isinstance(data,dict) or not isinstance(data.get('schema_version'),int):
        raise ValueError('Expected a versioned report object')
    if data['schema_version'] not in (1,2,3):
        raise ValueError('Unsupported report version')
    return data


def markdown(report, lang='zh'):
    from . import release_label
    report = sharing_copy(report,lang)
    t = lambda zh,en:zh if lang=='zh' else en
    def cell(value):
        if isinstance(value,(dict,list)):
            value=json.dumps(value,ensure_ascii=False)
        return html.escape(str(value),quote=True).replace('|','&#124;').replace('`','&#96;').replace('\n','<br>').replace('\r','').replace('\x1b','')
    def table(headers,rows):
        return ['| '+' | '.join(cell(value) for value in headers)+' |',
                '| '+' | '.join('---' for _ in headers)+' |']+[
                    '| '+' | '.join(cell(value) for value in row)+' |' for row in rows]
    rows=[['schema',report.get('schema_version')],[t('版本','Tool version'),report.get('tool_version','unknown')],
          [t('检测时间','Observation time'),report.get('generated_at',report.get('observed_at','unknown'))],
          [t('运行结果','Execution result'),report.get('result','unknown')]]
    lines=['# '+t('VPSMaster · 本地检测报告','VPSMaster · local diagnostic report'),'']
    lines += [release_label(lang),'']
    lines+=table([t('项目','Item'),t('记录','Observation')],rows)
    lines+=['',t('本报告来自已有本地记录，没有重新检测。缺失指标保持未知。',
                 'This report exports existing local observations, without rerunning checks. Missing metrics remain unknown.'),'']
    if report.get('recovery'):
        lines += ['> '+t('此报告由恢复日志生成，可能仅包含中断前的部分结果。','Recovered from a journal; results may be partial.'),'']
    modules=report.get('modules',{})
    if report.get('result_items'):
        lines += ['## '+t('统一结果记录','Unified evidence records'),'']
        lines += table([t('检查','Check'),t('状态','Status'),t('方法','Method'),t('来源','Source'),t('证据范围','Confidence scope')],
                       [[row.get('check_id'),row.get('status'),row.get('method'),row.get('source'),row.get('confidence','unknown')]
                        for row in report['result_items'] if isinstance(row,dict)])
        lines += ['']
    if isinstance(modules,dict) and modules:
        lines += ['## '+t('模块执行','Module execution'),'']
        lines += table([t('模块','Module'),t('状态','Status'),t('原因/错误码','Reason/error')],
                       [[name,row.get('status','unknown'),row.get('error_code') or row.get('reason','')]
                        for name,row in modules.items() if isinstance(row,dict)])
        lines += ['']
    checks=report.get('checks',report.get('system',{}).get('checks',[]))
    if isinstance(checks,list):
        lines += ['## '+t('本机提示','Local findings'),'']
        lines += table([t('项目','Check'),t('状态','Status'),t('说明','Explanation')],
                       [[row.get('title',row.get('id','unknown')),row.get('status','unknown'),row.get('detail','')]
                        for row in checks if isinstance(row,dict)])
        lines += ['']
    for key,zh,en in [('resources','资源额度与压力','Resource limits and pressure'),
                      ('security','权限与更新缓存','Permissions and update cache'),
                      ('network','网络检测','Network observations'),('route','路由记录','Route observations'),
                      ('ip_quality','IP数据来源与限制','IP providers and limitations'),
                      ('bandwidth','带宽样本','Bandwidth samples'),('media','媒体可达性','Media reachability'),
                      ('bgp','BGP 观测','BGP observations'),('carrier_nodes','测速节点探测','Speed node probes'),
                      ('return_routes','三城三运营商方向追踪','Three-city carrier traces')]:
        data=report.get(key)
        lines += ['## '+t(zh,en),'']
        if data is None:
            lines += [t('未记录；请查看模块跳过原因。','Not recorded; inspect the module skip reason.'),'']
        else:
            # A fence longer than every backtick run in the data prevents a
            # provider string from closing the block and forging report content.
            payload=json.dumps(data,ensure_ascii=False,indent=2)
            runs=re.findall(r'`+',payload)
            fence='`'*max(3,1+max(map(len,runs),default=0))
            lines += [fence+'json',payload,fence,'']
    lines += [t('分享前请人工检查。自动脱敏不是匿名或无敏感信息保证。','Review before sharing. Automated redaction is not an anonymity or secret-free guarantee.'),'']
    return '\n'.join(lines)


def export_report(report, destination, *, format='markdown', lang='zh'):
    if format not in ('markdown','json'):
        raise ValueError('Unsupported export format')
    safe=sharing_copy(report,lang)
    text=markdown(safe,lang) if format=='markdown' else json.dumps(safe,ensure_ascii=False,indent=2)+'\n'
    with exclusive_text(destination) as stream:
        stream.write(text)
        stream.flush()
        import os
        os.fsync(stream.fileno())
