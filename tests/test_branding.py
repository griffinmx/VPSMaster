"""Public branding contracts while legacy Python/API entry points stay usable."""
import subprocess
import sys
from pathlib import Path
import pytest
from proxydoctor import __version__,release_label
from proxydoctor.reporting import markdown


@pytest.mark.parametrize('lang',['zh','en'])
@pytest.mark.parametrize('command',[['--version'],['--help'],['check','--theme','iprisk','--color','never'],['check','--theme','framed','--color','never']])
def test_visible_legacy_python_entry_has_current_brand(lang,command):
    p=subprocess.run([sys.executable,'-B','-m','proxydoctor',*command,'--lang',lang],capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert p.returncode in (0,1)
    assert 'VPSMaster' in p.stdout and 'ProxyDoctor' not in p.stdout and 'VPS CHECK' not in p.stdout
    assert 'Traceback' not in p.stderr


@pytest.mark.parametrize('lang',['zh','en'])
def test_report_brand_and_legacy_json_schema(lang):
    text=markdown({'schema_version':3,'tool_version':__version__,'checks':[]},lang)
    assert 'VPSMaster' in text and 'ProxyDoctor' not in text
    assert __version__=='1.0.0b1' and 'VPSMaster' in release_label(lang)


def test_distribution_keeps_legacy_module_and_both_cli_names():
    root=Path(__file__).resolve().parents[1]
    metadata=(root/'pyproject.toml').read_text()
    assert 'name = "proxydoctor"' in metadata
    assert 'vpsmaster = "proxydoctor.cli:main"' in metadata
    assert 'proxydoctor = "proxydoctor.cli:main"' in metadata
    assert (root/'vpsmaster.sh').read_bytes()==(root/'proxydoctor.sh').read_bytes()
