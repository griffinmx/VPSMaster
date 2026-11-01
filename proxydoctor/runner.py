"""Small synchronous module boundary; no global process or signal changes."""
from .reports import utc_now


class ModuleRunner:
    def __init__(self, report, checkpoint, notify):
        self.report = report
        self.checkpoint = checkpoint
        self.notify = notify
        report['modules'] = {}

    def run(self, name, operation=None, skip_reason=None):
        state = {'status': 'skipped' if skip_reason else 'running',
                 'started_at': utc_now(), 'error_code': None}
        self.report['modules'][name] = state
        if skip_reason:
            state['reason'] = skip_reason
            state['finished_at'] = utc_now()
            self.checkpoint()
            return
        self.checkpoint()
        try:
            operation()
            state['status'] = 'success'
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
