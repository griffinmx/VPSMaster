"""Small synchronous module boundary; no global process or signal changes."""
from .reports import utc_now
import time
from .limits import bounded, ModuleTimeout, DeadlineUnsupported


class ModuleRunner:
    def __init__(self, report, checkpoint, notify, observe=None, deadline=None, module_timeout=None):
        self.report = report
        self.checkpoint = checkpoint
        self.notify = notify
        self.observe = observe
        self.deadline = deadline
        self.module_timeout = module_timeout
        report['modules'] = {}

    def run(self, name, operation=None, skip_reason=None):
        if not skip_reason and self.deadline is not None and time.monotonic() >= self.deadline:
            skip_reason = 'TOTAL_TIME_BUDGET'
        state = {'status': 'skipped' if skip_reason else 'running',
                 'started_at': utc_now(), 'error_code': None}
        self.report['modules'][name] = state
        if self.observe:self.observe(name, state, False)
        if skip_reason:
            state['reason'] = skip_reason
            state['finished_at'] = utc_now()
            self.checkpoint()
            if self.observe:self.observe(name, state, True)
            return
        self.checkpoint()
        try:
            seconds = self.module_timeout
            if self.deadline is not None:
                seconds = min(seconds, max(0.001, self.deadline-time.monotonic()))
            with bounded(seconds):
                result = operation()
            state['status'] = 'success'
            if isinstance(result,dict) and result.get('status') in ('unknown','skipped','unsupported'):
                state.update(result)
        except ModuleTimeout:
            from .worker import cancel_all, reset
            cancel_all();reset()
            state.update(status='unknown', error_code='MODULE_TIMEOUT')
        except DeadlineUnsupported:
            state.update(status='unsupported', error_code='DEADLINE_UNSUPPORTED')
        except KeyboardInterrupt:
            state.update(status='cancelled', error_code='CANCELLED')
            raise
        except Exception:
            # Deliberate isolation boundary. Never echo exception text that may
            # include URLs, tokens, provider responses or sensitive local paths.
            state.update(status='failure', error_code='MODULE_ERROR')
            self.notify(name)
        finally:
            state['finished_at'] = utc_now()
            self.checkpoint()
            if self.observe:self.observe(name, state, True)
