#!/usr/bin/env python3
"""Offline, dependency-free installer. Review this file before running it."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys

VERSION = '1.0.0b1'


def verify(source):
    manifest = json.loads((source/'MANIFEST.sha256.json').read_text(encoding='utf-8'))
    if manifest.get('version') != VERSION or not isinstance(manifest.get('files'), dict):
        raise ValueError('Invalid release manifest')
    files = manifest['files']
    required = {'install.py','pyproject.toml','LICENSE','THIRD_PARTY_NOTICES.md',
                'proxydoctor/__init__.py','proxydoctor/__main__.py','proxydoctor/cli.py'}
    if not required <= set(files):
        raise ValueError('Incomplete release manifest')
    actual = {p.relative_to(source).as_posix() for p in (source/'proxydoctor').rglob('*.py')}
    if actual != {name for name in files if name.startswith('proxydoctor/') and name.endswith('.py')}:
        raise ValueError('Unlisted or missing package source')
    for name, expected in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('Unsafe manifest path')
        path = source.joinpath(*relative.parts)
        if any(part.is_symlink() for part in (path,*path.parents) if part != source.parent):
            raise ValueError('Symlink in source path')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Release integrity check failed')
    return files


def install(source, prefix):
    if sys.version_info < (3,10) or sys.platform != 'linux':
        raise ValueError('Requires Linux and Python 3.10+')
    files = verify(source)
    prefix = prefix.expanduser().absolute()
    if prefix.is_symlink() or os.path.lexists(prefix):
        raise FileExistsError('Install destination already exists; choose a new version directory')
    prefix.parent.mkdir(parents=True,exist_ok=True)
    prefix.mkdir(mode=0o700)
    owned = prefix.resolve()
    try:
        # --without-pip avoids ensurepip/network/package-manager dependencies.
        subprocess.run([sys.executable,'-I','-B','-m','venv','--without-pip',str(prefix)],
                       check=True,timeout=45,capture_output=True)
        python = prefix/'bin/python'
        probe = subprocess.run([str(python),'-I','-B','-c',
                                'import json,sys,sysconfig;print(json.dumps([sys.prefix,sys.base_prefix,sysconfig.get_path("purelib")]))'],
                               check=True,capture_output=True,text=True,timeout=10)
        active,base,library = json.loads(probe.stdout)
        if active == base or Path(active).resolve() != owned:
            raise ValueError('Virtual environment isolation check failed')
        library = Path(library)
        library.resolve().relative_to(owned)
        for name in files:
            if name.startswith('proxydoctor/') and name.endswith('.py'):
                destination = library/name
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source/name,destination)
        notices = prefix/'share/proxydoctor'
        notices.mkdir(parents=True)
        for name in ('LICENSE','THIRD_PARTY_NOTICES.md','MANIFEST.sha256.json'):
            shutil.copyfile(source/name,notices/name)
        launcher = prefix/'bin/vpsmaster'
        # execv avoids shebang/path whitespace issues without shell interpolation.
        launcher.write_text('#!/bin/sh\nexec '+__import__('shlex').quote(str(python))+' -I -B -m proxydoctor "$@"\n',encoding='utf-8')
        launcher.chmod(0o700)
        legacy_launcher = prefix/'bin/proxydoctor'
        legacy_launcher.write_bytes(launcher.read_bytes())
        legacy_launcher.chmod(0o700)
        subprocess.run([str(launcher),'--version'],check=True,timeout=10,capture_output=True)
        (prefix/'proxydoctor-install.json').write_text(json.dumps({'brand':'VPSMaster','package':'proxydoctor','version':VERSION,'isolated':True}),encoding='utf-8')
        return launcher
    except BaseException:
        # Only remove the new directory reserved by this invocation.
        if not prefix.is_symlink() and prefix.resolve() == owned:
            shutil.rmtree(prefix)
        raise


def main():
    parser=argparse.ArgumentParser(description='Offline isolated VPSMaster installer / VPSMaster 离线隔离安装')
    parser.add_argument('--prefix',type=Path,default=Path.home()/'.local/share/vpsmaster'/VERSION)
    parser.add_argument('--run',action='store_true',help='Install and run a read-only offline check')
    args=parser.parse_args()
    try:
        launcher=install(Path(__file__).resolve().parent,args.prefix)
    except KeyboardInterrupt:
        print('Installation cancelled; new environment cleaned / 安装已取消',file=sys.stderr)
        return 130
    except (OSError,ValueError,subprocess.SubprocessError):
        print('Installation failed. Check Python/venv availability, release checksum and destination. No system packages were installed. / 安装失败，请检查环境、校验和与目录。',file=sys.stderr)
        return 2
    print('Installed / 已安装：'+str(launcher),flush=True)
    print('VPSMaster 1.0 public beta; not the final release / VPSMaster 1.0 公测版，非最终版本',flush=True)
    if args.run:
        return subprocess.call([str(launcher),'suite','--offline'])
    return 0


if __name__=='__main__':
    sys.exit(main())
