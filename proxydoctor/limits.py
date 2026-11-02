"""Scoped Linux main-thread deadlines; no background thread left doing work."""
from contextlib import contextmanager
import signal
import threading
import time


class ModuleTimeout(BaseException):
    pass


class DeadlineUnsupported(BaseException):
    pass


@contextmanager
def bounded(seconds):
    if seconds is None:
        yield
        return
    if not hasattr(signal, 'setitimer') or threading.current_thread() is not threading.main_thread():
        raise DeadlineUnsupported()
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    # Do not displace a caller's active alarm.
    if previous_timer[0]:
        raise DeadlineUnsupported()
    def expired(*_):
        raise ModuleTimeout()
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
