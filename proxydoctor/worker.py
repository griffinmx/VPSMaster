"""CLI-only hard boundaries for network operations, including blocking DNS."""
import json
import os
import subprocess
import sys
from pathlib import Path
import threading

_active=set()
_lock=threading.Lock()
_cancelled=threading.Event()


def cancel_all():
    _cancelled.set()
    with _lock:
        for process in tuple(_active):
            if process.poll() is None:
                try:process.kill()
                except OSError:pass


def reset():
    _cancelled.clear()


def enabled():
    return os.environ.get('PROXYDOCTOR_NETWORK_WORKERS','1')=='1'


def local_command(argv, timeout=4):
    """Bound a caller-validated local probe and register it for cancellation."""
    if _cancelled.is_set():
        return None, '', 'CANCELLED'
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding='utf-8', errors='replace',
                          env={**os.environ, 'LC_ALL':'C'}) as process:
        with _lock:
            _active.add(process)
            if _cancelled.is_set():process.kill()
        try:
            output, errors = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate()
            return None, '', 'COMMAND_TIMEOUT'
        except BaseException:
            process.kill();process.communicate()
            raise
        finally:
            with _lock:_active.discard(process)
        if len(output)>16384:
            return None, '', 'COMMAND_OUTPUT_LIMIT'
        message=errors.lower()
        error=None
        if process.returncode:
            if any(token in message for token in ('operation not permitted','permission denied','not enough privileges')):
                error='PERMISSION_DENIED'
            elif any(token in message for token in ('network is unreachable','network unreachable','no route to host')):
                error='NETWORK_UNREACHABLE'
            elif 'not supported' in message:
                error='PROTOCOL_UNSUPPORTED'
        return process.returncode, output, error


def invoke(action,options,timeout=20):
    if action not in ('json','page','transfer','carrier_probe','resolve_public'):
        raise ValueError('Unsupported network action')
    if _cancelled.is_set():
        return None
    try:
        bootstrap='import sys;sys.path.insert(0,sys.argv.pop(1));from proxydoctor.worker import main;sys.exit(main())'
        with subprocess.Popen([sys.executable,'-I','-B','-c',bootstrap,str(Path(__file__).resolve().parent.parent),action],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                              text=True,encoding='utf-8') as process:
            with _lock:
                _active.add(process)
                if _cancelled.is_set():process.kill()
            try:
                output,_=process.communicate(json.dumps(options),timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill();process.communicate()
                return None
            except KeyboardInterrupt:
                cancel_all();process.communicate()
                raise
            finally:
                with _lock:_active.discard(process)
            if process.returncode or len(output)>2*1024**2:
                return None
            return json.loads(output)
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return None


def main():
    os.environ['PROXYDOCTOR_NETWORK_WORKERS']='0'
    options=json.loads(sys.stdin.read(65537))
    action=sys.argv[1]
    if action=='json':
        from .net import request_json
        result=request_json(**options)
    elif action=='page':
        from dataclasses import asdict
        from .media import fetch_page
        result=asdict(fetch_page(**options))
    elif action=='transfer':
        from dataclasses import asdict
        from .bandwidth import transfer
        result=asdict(transfer(**options))
    elif action=='carrier_probe':
        from .carriers import probe_node
        result=probe_node(**options)
    elif action=='resolve_public':
        from .carriers import resolve_public
        result=resolve_public(**options)
    else:
        return 2
    print(json.dumps(result))
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except (Exception,KeyboardInterrupt):
        sys.exit(1)  # Never print provider exceptions/credentials.
