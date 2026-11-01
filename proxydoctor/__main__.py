from .cli import main
import signal

def cancelled(signum, frame):
    from .worker import cancel_all
    cancel_all()
    raise KeyboardInterrupt

if hasattr(signal,'SIGTERM'):
    signal.signal(signal.SIGTERM,cancelled)
signal.signal(signal.SIGINT,cancelled)

try:
    main()
except KeyboardInterrupt:
    import sys
    print('\n已中止 / Interrupted',file=sys.stderr)
    sys.exit(130)
