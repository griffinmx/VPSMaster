import json
import subprocess
import sys

import pytest

from proxydoctor.reporting import export_report, load_report, markdown, sharing_copy
from proxydoctor.reports import recover_latest


def test_markdown_escapes_injected_markup_and_preserves_uncertainty():
    document={'schema_version':3,'modules':{'<script>alert(1)</script>|':{'status':'skipped','reason':'offline'}},
              'media':{'Netflix':{'state':'unknown','evidence':'</pre><script>x</script>'}}}
    text=markdown(document,'en')
    assert '&lt;script&gt;' in text  # table cells remain escaped
    assert '```json\n' in text
    # The provider string is literal JSON inside a code fence, not raw HTML.
    assert '"evidence": "</pre><script>x</script>"' in text.split('```json\n')[1].split('\n```')[0]
    assert 'unknown' in text and 'skipped' in text


def test_markdown_provider_cannot_close_json_fence():
    payload='```\n# forged section\n``````\n<script>x</script>'
    text=markdown({'schema_version':3,'media':{'raw':payload}},'en')
    assert '```````json\n' in text
    block=text.split('```````json\n')[1].split('\n```````')[0]
    assert json.loads(block)=={'raw':payload}


def test_sharing_redaction_hides_credentials_queries_and_ip():
    safe=sharing_copy({'api_key':'my-secret','nested':{'password':'p'},
                       'evidence':'https://user:pass@example.com/test?token=secret#fragment Bearer abc123 8.8.8.8'})
    text=json.dumps(safe)
    assert all(value not in text for value in ('my-secret','user:pass','token=secret','abc123','8.8.8.8'))
    assert 'https://example.com/test' in text


def test_export_does_not_overwrite(tmp_path):
    destination=tmp_path/'report.md'
    export_report({'schema_version':3},destination)
    initial=destination.read_bytes()
    with pytest.raises(FileExistsError):
        export_report({'schema_version':3,'result':'different'},destination)
    assert destination.read_bytes()==initial


def test_loader_rejects_unsupported_schema_and_size(tmp_path):
    path=tmp_path/'input.json';path.write_text('{"schema_version":999}')
    with pytest.raises(ValueError):load_report(path)
    with pytest.raises(ValueError):load_report(path,max_bytes=2)


def test_recovery_read_budget_is_enforced(tmp_path):
    path=tmp_path/'events';path.write_bytes(b'12345678\n')
    with pytest.raises(ValueError):recover_latest(path,max_line_bytes=4)


@pytest.mark.parametrize('lang',['zh','en'])
def test_actual_offline_export_and_partial_recovery_cli(tmp_path,lang):
    document={'schema_version':3,'result':'running','modules':{'network':{'status':'running'}},'api_key':'private-test-value'}
    source=tmp_path/'source.json';source.write_text(json.dumps(document),encoding='utf-8')
    journal=tmp_path/'journal.jsonl'
    journal.write_text(json.dumps({'event_version':1,'snapshot':document})+'\n'+ '{"partial":',encoding='utf-8')
    report=tmp_path/'report.md';recovered=tmp_path/'recovered.json'
    def cli(*args):
        return subprocess.run([sys.executable,'-m','proxydoctor',*args,'--lang',lang],capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert cli('report','--input',str(source),'--output',str(report)).returncode==0
    assert 'private-test-value' not in report.read_text(encoding='utf-8')
    assert cli('recover','--journal',str(journal),'--output',str(recovered)).returncode==0
    result=json.loads(recovered.read_text(encoding='utf-8'))
    assert result['result']=='recovered_partial'
    assert result['recovery']['new_measurement'] is False
    assert cli('recover','--journal',str(journal),'--output',str(recovered)).returncode==2
