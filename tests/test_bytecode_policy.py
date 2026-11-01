"""Real interpreter regressions for BETA22-001; no dependency on remote APIs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest


def copy_package(destination):
    package=destination/'proxydoctor';package.mkdir(parents=True)
    for source in (Path(__file__).resolve().parents[1]/'proxydoctor').glob('*.py'):
        shutil.copyfile(source,package/source.name)
    return package


@pytest.mark.parametrize('action,options',[
    ('json',{'url':'http://127.0.0.1:1/'}),
    ('page',{'url':'http://127.0.0.1:1/'}),
    ('transfer',{'direction':'invalid','size':0}),
    ('carrier_probe',{'identifier':'invalid'}),
    ('resolve_public',{'host':'127.0.0.1','family':4}),
])
def test_real_worker_never_creates_bytecode_in_fresh_package(tmp_path,action,options):
    package=copy_package(tmp_path/'fresh')
    program='''import json,sys
sys.path.insert(0,sys.argv[1])
from proxydoctor.worker import invoke,reset
reset()
result=invoke(sys.argv[2],json.loads(sys.argv[3]),timeout=8)
print(json.dumps({'completed':True,'response':result}))
'''
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'0'}
    # -I ignores environment-only bytecode settings. The worker must set -B in
    # its own interpreter argv rather than depend on parent runtime state.
    result=subprocess.run([sys.executable,'-I','-B','-c',program,str(package.parent),action,json.dumps(options)],
                          env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['completed'] is True
    assert not list(package.rglob('__pycache__'))
    assert not list(package.rglob('*.pyc'))


def test_fresh_fixture_is_writable_and_plain_python_can_generate_cache(tmp_path):
    package=copy_package(tmp_path/'control')
    result=subprocess.run([sys.executable,'-I','-c',
                           'import sys;sys.path.insert(0,sys.argv[1]);import proxydoctor',str(package.parent)],
                          capture_output=True,timeout=10)
    assert result.returncode==0
    assert list(package.rglob('*.pyc')), 'Control must be able to reproduce the original cache write'
