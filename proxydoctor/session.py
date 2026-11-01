"""Consistent persistence lifecycle for individual CLI modules."""
from .reports import ReportStore,UnavailableStore,utc_now
from .schema import normalize_report
from .reporting import sharing_copy
from . import __version__


class ScanSession:
    def __init__(self,key,path,lang):
        self.key=key
        self.lang=lang
        self.report={'schema_version':3,'tool_version':__version__,'generated_at':utc_now(),
                     'mode':'read-only','result':'running',key:{}}
        try:self.store=ReportStore(path,lambda value:sharing_copy(value,lang))
        except FileExistsError:raise
        except OSError:self.store=UnavailableStore(path)
        self.failed=False

    def checkpoint(self):
        normalize_report(self.report)
        if not self.store.checkpoint(self.report):self.failed=True

    def __enter__(self):
        self.checkpoint()
        return self

    def __exit__(self,kind,value,traceback):
        if kind is not None and issubclass(kind,KeyboardInterrupt):
            from .worker import cancel_all
            cancel_all()
            self.report['result']='cancelled'
        else:self.report['result']='incomplete' if kind else self.report['result'] if self.report['result']!='running' else 'local_execution_complete'
        self.report['finished_at']=utc_now()
        normalize_report(self.report)
        try:
            self.failed=not self.store.finish(self.report) or self.failed
        finally:self.store.close()
        if self.store.journal_path:
            print(('恢复日志: ' if self.lang=='zh' else 'Recovery journal: ')+str(self.store.journal_path),flush=True)
        if self.failed:print('REPORT_WRITE_FAILED'+(' / 报告写入未完成' if self.lang=='zh' else ''),flush=True)
        return False
