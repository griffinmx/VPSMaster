"""User-facing summary of existing evidence; never invent a safety score."""
def render_summary(report,out):
    tr=out.text
    out.line(tr('综合汇总（执行完成不代表目标全部可用）','Summary (execution is not target availability)'),'title')
    checks={r['id']:r for r in (report.get('system') or {}).get('checks',[])}
    system=checks.get('system',{})
    out.row(tr('系统','System'),system.get('evidence',tr('未确认','Unconfirmed')))
    allocation=(report.get('resources') or {}).get('allocation',{})
    out.row(tr('资源','Resources'),f"CPU {allocation.get('cpu_limit_cores','?')} vCPU; RAM {allocation.get('memory_limit_bytes','?')} B",'unknown')
    network=report.get('network') or {}
    dns=network.get('dns',[]);transport=network.get('transports',[])
    out.row('DNS / TCP / TLS',f"DNS {sum(r.get('status')=='success' for r in dns)}/{len(dns)}; TCP {sum(r.get('tcp',{}).get('status')=='success' for r in transport)}/{len(transport)}; TLS {sum(r.get('tls',{}).get('status')=='success' for r in transport)}/{len(transport)}",'unknown')
    ip=report.get('ip_quality') or {}
    values=ip.get('values') or {}
    out.row('IP / ASN',str(values.get('asn') or 'unknown')+' · '+str(values.get('country') or 'unknown'),'unknown')
    routes={'udp':report.get('route') or {},**report.get('additional_routes',{})}
    for method,result in routes.items():out.row(method.upper(),result.get('state','not_run'),'unknown')
    media=report.get('summary',{}).get('media',{})
    out.row(tr('网页可达','Pages reachable'),f"{media.get('reachable',0)}/{len(report.get('media',{}))} · "+tr('不代表解锁或播放','Not unlocking/playback'),'unknown')
    security=report.get('security') or {}
    high=sum(bool(set(row.get('reasons',[])) & {'WORLD_WRITABLE','SENSITIVE_WORLD_READABLE'}) for row in security.get('files',[]))
    out.row(tr('权限风险提醒','Permission risk advisory'),f'high {high}; review {security.get("review_count","?")}', 'bad' if high else 'unknown')
    out.row(tr('安全审阅','Security review'),str(security.get('review_count','unknown'))+' · '+tr('只读发现需人工评估，非漏洞严重度认证','Read-only findings need review, not certified vulnerability severity'),'unknown')
    counts=report.get('summary',{}).get('module_counts',{})
    out.row(tr('模块统计','Module counts'),'; '.join(tr(zh,en)+' '+str(counts.get(key,0)) for key,zh,en in
            [('success','完成','completed'),('failure','失败','failed'),('skipped','跳过','skipped'),('unknown','未知','unknown'),('unsupported','不支持','unsupported'),('cancelled','中断','cancelled')]),'title')
    out.line(tr('关注：未知/超时不等于安全；检查报告中的错误与权限，再决定修复。','Action: unknown/timeouts are not safe; review errors and permissions before repair.'),'unknown')
