"""Uniform evidence envelopes; legacy raw module payloads remain available."""
from .reports import utc_now

STATUSES=frozenset(('success','failure','skipped','unsupported','unknown'))


def normalize_report(report):
    rows=[]
    def add(identifier,category,status,method,source,data,error=None,limitations=None):
        rows.append({'check_id':identifier,'category':category,
                     'status':status if status in STATUSES else 'unknown',
                     'observed_at':data.get('observed_at',data.get('checked_at',report.get('generated_at',utc_now()))),
                     'method':method,'source':source,'metrics':data,'error_code':error,
                     'confidence':'provider_report' if method=='provider_query' else 'execution_only' if category=='execution' else 'direct_observation' if status in ('success','failure') else 'limited_or_unconfirmed',
                     'limitations':limitations or ['Limited observation; not a complete security or availability guarantee.']})
    for name,item in report.get('modules',{}).items():
        add('module.'+name,'execution',item.get('status'),'module_execution','local',item,item.get('error_code') or item.get('reason'))
    for item in (report.get('system') or report).get('checks',[]):
        add('system.'+item['id'],'system',{'pass':'success','fail':'failure','skip':'skipped'}.get(item.get('status'),'unknown'),
            'readonly_check','local',item)
    for name in ('resources','security','bandwidth'):
        item=report.get(name)
        if item:
            add(name,name,'unsupported' if item.get('status')=='unsupported' else 'unknown',
                item.get('method','readonly_observation'),'local' if name!='bandwidth' else 'selected_https_sources',item,
                limitations=item.get('limitations'))
    network=report.get('network') or {}
    for i,item in enumerate(network.get('dns',[])):
        add(f'network.dns.{i}','network',item.get('status'),'system_resolver',item.get('target','example.com'),item,item.get('error_code'))
    for i,item in enumerate(network.get('transports',[])):
        for stage in ('tcp','tls'):
            evidence=item.get(stage,{})
            add(f'network.{stage}.{i}','network',evidence.get('status'),stage,item.get('hostname',item.get('target')),evidence,evidence.get('error_code'))
    route=report.get('route')
    if route:
        add('route.destination','route','success' if route.get('state')=='reached' else 'unknown',
            route.get('method','udp')+'_trace',route.get('target'),{'state':route.get('state')},
            limitations=['Router silence is not end-to-end packet loss; location is estimated.'])
        for i,item in enumerate(route.get('hops',[])):
            add(f'route.hop.{i}','route','success' if item.get('state') in ('reply','reached') else 'unknown',
                'single_'+route.get('method','udp')+'_probe',item.get('ip'),item,limitations=['One probe per TTL; response loss is not forwarding loss.'])
    for name in ('bgp','carrier_nodes','return_routes'):
        item=report.get(name)
        if item:
            add(name,name,'success' if item.get('status')=='success' else 'unknown',
                'provider_query' if name=='bgp' else 'active_network_observation',
                item.get('source','fixed_public_targets'),item,item.get('error_code'),item.get('limitations'))
    for name,item in (report.get('ip_quality') or {}).get('sources',{}).items():
        add('ip.'+name,'ip_quality','success' if item.get('state')=='ok' else 'skipped' if item.get('state')=='key_required' else 'unknown',
            'provider_query',name,item,item.get('state') if item.get('state')!='ok' else None)
    for name,item in report.get('media',{}).items():
        status = 'success' if item.get('scope')=='public_page_reachability' and item.get('state')=='reachable' else 'failure' if item.get('state')=='restricted' else 'unknown'
        add('media.'+name,'media',status,'http_reachability' if item.get('scope')=='public_page_reachability' else 'anonymous_service_evidence',name,item,
            limitations=['HTTP/catalog/offer visibility does not prove account playback.'])
    report['result_schema_version']=1
    report['result_items']=rows
    return rows
