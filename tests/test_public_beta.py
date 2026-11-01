import json
import re
import subprocess
import sys
import time
from pathlib import Path
import pytest
from proxydoctor.console import Console,width
from proxydoctor import cli,media,bgp,carriers,routes,worker


def test_frames_wrap_wide_text_without_loss_or_border_misalignment(capsys):
    out=Console('zh','never')
    title='长标题'*40
    value='测试位置与来源'*45+'e\u0301'
    out.frame_open(title,box_w=48,subtitle='1.0 公测版（非最终版本）')
    out.frame_keyvalue('位置',value)
    out.frame_section(1,'资源','Resources')
    out.panel('IP 面板',[('数据源','未知'*60,'unknown')])
    out.frame_close()
    lines=capsys.readouterr().out.splitlines()
    assert all(width(line)==50 for line in lines)
    body=''.join(line[1:-1].strip() for line in lines if line.startswith('║'))
    assert title in body and value in body
    assert '\x1b' not in body


@pytest.mark.parametrize('language',['zh','en'])
@pytest.mark.parametrize('theme',['default','iprisk','framed'])
def test_actual_check_themes_respect_language_and_beta_identity(language,theme):
    result=subprocess.run([sys.executable,'-m','proxydoctor','check','--lang='+language,
                           '--theme',theme,'--color','never'],capture_output=True,text=True,encoding='utf-8',timeout=15)
    assert result.returncode in (0,1)
    assert ('公测版' if language=='zh' else 'public beta') in result.stdout
    assert '\x1b' not in result.stdout
    if language=='en':assert not re.search('[\u4e00-\u9fff]',result.stdout)
    if theme=='framed':assert all(width(line)==80 for line in result.stdout.splitlines())


@pytest.mark.parametrize('flag',[['--lang','zh'],['--lang=zh']])
def test_explicit_chinese_wins_over_console_fallback(monkeypatch,capsys,flag):
    monkeypatch.setattr('proxydoctor.console.can_render_cjk',lambda:False)
    monkeypatch.setattr(sys,'argv',['proxydoctor',*flag,'--version'])
    with pytest.raises(SystemExit) as exc:cli._main()
    assert exc.value.code==0
    assert '公测版' in capsys.readouterr().out


def test_quality_colour_reaches_renderer(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys,'argv',['proxydoctor','quality','--color','never','--lang','en'])
    called=[]
    def probe(**options):
        called.append(options['color']);options['report']['status']='success';return 0
    monkeypatch.setattr('proxydoctor.connectivity.run_console',probe)
    with pytest.raises(SystemExit) as exc:cli._main()
    assert exc.value.code==0 and called==['never']


@pytest.mark.parametrize('status,state',[(200,'reachable'),(403,'access_denied'),(429,'rate_limited'),(503,'http_error'),(None,'unknown')])
def test_media_cli_probe_is_reachability_only(monkeypatch,status,state):
    calls=[]
    monkeypatch.setattr(media,'fetch_page',lambda url:calls.append(url) or media.Page(status,'Netflix is not available in your country'))
    row=media.check_reachability('Netflix')
    assert row['state']==state and row['scope']=='public_page_reachability'
    assert row['unlock']==row['playback']=='not_tested'
    assert len(calls)==1
    label,_=media.display_reachability(row,'en')
    assert 'unlocked' not in label.lower() and 'playback successful' not in label.lower()


def test_provider_errors_are_visible_and_supplied_abuse_score_retained(monkeypatch,capsys):
    from proxydoctor import ipquality
    monkeypatch.setattr(ipquality,'request_json',lambda *a,**kw:({'ip':'8.8.8.8'},'ok'))
    row=ipquality.collect(enrich=False)
    row['sources']['proxycheck.io']={'state':'rate_limited'}
    row['reputation'].update(score=12,total_reports=2)
    ipquality.render(row,Console('en','never'))
    output=capsys.readouterr().out
    assert 'Rate limited' in output and 'AbuseIPDB' in output and '12/100' in output


@pytest.mark.parametrize('method',['icmp','tcp'])
def test_trace_optional_dependency_missing_is_explicit(monkeypatch,capsys,method):
    monkeypatch.setattr(routes.shutil,'which',lambda *a,**kw:None)
    assert routes.trace_method('1.1.1.1',method=method)==1
    assert 'TRACEROUTE_DEPENDENCY_MISSING' in capsys.readouterr().out


def test_tcp_trace_uses_fixed_argv_and_retains_real_rtt(monkeypatch):
    monkeypatch.setattr(routes.sys,'platform','linux')
    monkeypatch.setattr(routes.shutil,'which',lambda *a,**kw:'/usr/bin/traceroute')
    calls=[]
    monkeypatch.setattr(worker,'local_command',lambda argv,**kw:calls.append(argv) or (0,' 1  1.1.1.1  2.750 ms\n',None))
    rows=[]
    assert routes.trace_method('1.1.1.1',lambda *a,**kw:None,method='tcp',tcp_port=8443,geo=False,records=rows)==0
    assert rows[0]['latency_ms']==2.75 and rows[0]['state']=='reached'
    assert calls[0][-4:]==['-T','-p','8443','1.1.1.1']
    assert routes.parse_traceroute_hop(' 1  *',1,'1.1.1.1')['state']=='timeout'
    assert routes.parse_traceroute_hop(' 1  1.1.1.1  2.0 ms !H',1,'1.1.1.1')['state']=='unreachable'


def test_bgp_validates_prefix_and_keeps_collector_scope(monkeypatch):
    responses={'network-info':({'prefix':'8.8.8.0/24','asns':[15169]},'ok'),
               'asn-neighbours':({'neighbours':[{'asn':3356,'type':'left','power':2}]},'ok'),
               'bgp-state':({'bgp_state':[{'target_prefix':'8.8.8.0/24','path':[3356,15169],'source_id':'00-test'}]},'ok')}
    monkeypatch.setattr(bgp,'query',lambda endpoint,*a,**kw:responses[endpoint])
    row=bgp.collect('8.8.8.8')
    assert row['status']=='success' and row['paths'][0]['as_path']==[3356,15169]
    assert 'commercial upstream' in ' '.join(row['limitations'])
    monkeypatch.setattr(bgp,'query',lambda *a,**kw:({'prefix':'1.1.1.0/24','asns':[13335]},'ok'))
    assert bgp.collect('8.8.8.8')['status']=='unknown'


def test_bgp_provider_failure_keeps_unknown_and_does_not_invent_paths(monkeypatch):
    monkeypatch.setattr(bgp,'query',lambda *a,**kw:(None,'rate_limited'))
    row=bgp.collect('8.8.8.8')
    assert row['status']=='unknown' and row['paths']==[]
    assert row['sources']['network-info']=='rate_limited'


def test_hong_kong_node_never_counts_as_mainland_mobile(monkeypatch):
    monkeypatch.setattr(carriers,'probe_node',lambda name:{'identifier':name,'status':'sample_available' if name=='cm-hk' else 'unknown'})
    row=carriers.collect_nodes()
    assert row['nodes']['cm-hk']['mainland'] is False
    assert row['coverage']['mobile'] is False and row['status']=='partial'


def test_new_network_commands_reject_invalid_inputs_without_requests():
    for args in (['trace','--target',';reboot'],['bgp','--target','127.0.0.1'],
                 ['return-route','--tcp-port','0'],['suite','--offline','--china-speed']):
        result=subprocess.run([sys.executable,'-m','proxydoctor',*args],capture_output=True,timeout=10)
        assert result.returncode==2
