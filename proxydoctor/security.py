"""Metadata-only file checks and local Ubuntu update evidence.

No privilege escalation, package refresh, network calls, private-file reads or
automatic repairs. Findings are review prompts, never exploit confirmations.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import stat
import time

from .reports import utc_now


POLICIES = (
    ('/etc/passwd',False), ('/etc/group',False),
    ('/etc/shadow',True), ('/etc/gshadow',True),
    ('/etc/sudoers',False), ('/etc/ssh/sshd_config',False),
    ('/etc',False), ('/etc/ssh',False), ('/etc/sudoers.d',False),
)


def inspect_path(path, sensitive=False, *, lstat=os.lstat):
    row = {'source':path,'method':'lstat_metadata_only','status':'unknown',
           'observed_at':utc_now(),'reasons':[]}
    try:
        info = lstat(path)
    except FileNotFoundError:
        row.update(status='skipped',error_code='PATH_MISSING')
        return row
    except OSError:
        row['error_code'] = 'METADATA_UNAVAILABLE'
        return row
    mode = stat.S_IMODE(info.st_mode)
    row.update(mode=oct(mode),uid=info.st_uid,gid=info.st_gid)
    if stat.S_ISLNK(info.st_mode):
        row['error_code'] = 'SYMLINK_REQUIRES_REVIEW'
        return row
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        row['error_code'] = 'UNEXPECTED_FILE_TYPE'
        return row
    if mode & stat.S_IWOTH:
        row['reasons'].append('WORLD_WRITABLE')
    if mode & stat.S_IWGRP:
        row['reasons'].append('GROUP_WRITABLE_REVIEW')
    if info.st_uid != 0:
        row['reasons'].append('OWNER_NOT_ROOT_REVIEW')
    if sensitive and mode & stat.S_IROTH:
        row['reasons'].append('SENSITIVE_WORLD_READABLE')
    row['status'] = 'review' if row['reasons'] else 'observed'
    row['limitations'] = ['POSIX mode/owner only; ACLs, capabilities, mount options and runtime use not evaluated.',
                           'Group access or non-root ownership can be intentional; review in deployment context.']
    return row


def read_small(path):
    try:
        with Path(path).open(encoding='utf-8') as stream:
            value = stream.read(8193)
        return value if len(value) <= 8192 else None
    except (OSError,UnicodeError):
        return None


def update_evidence(*, lstat=os.lstat, read=read_small, now=time.time):
    """A timestamp is freshness evidence, never a vulnerability inventory."""
    row = {'method':'local_update_cache_only','observed_at':utc_now(),'status':'unknown',
           'pending_updates':None,'security_updates':None,'sources':[],
           'limitations':['No repository refresh or package solver was run.',
                          'Missing or stale cache cannot establish whether the system is fully patched.']}
    for path in ('/var/lib/apt/periodic/update-success-stamp',
                 '/var/lib/update-notifier/updates-available'):
        evidence = {'source':path,'status':'unknown'}
        try:
            info = lstat(path)
            if not stat.S_ISREG(info.st_mode):
                evidence['error_code'] = 'NOT_REGULAR_FILE'
            else:
                timestamp = info.st_mtime
                age = now()-timestamp
                if age < 0:
                    evidence['error_code'] = 'FUTURE_TIMESTAMP'
                else:
                    evidence.update(status='observed',age_hours=round(age/3600,2),
                                    modified_at=datetime.fromtimestamp(timestamp,timezone.utc).isoformat())
                    if path.endswith('updates-available'):
                        # This notifier summary is optional and may be localized.
                        # Never retain its complete text in logs or reports.
                        text = read(path)
                        match = re.search(r'^\s*(\d+) updates? can be applied immediately\.',text or '',re.M)
                        if match:
                            row['pending_updates'] = int(match[1])
                            row['status'] = 'cached_observation'
                        match = re.search(r'^(\d+) of these updates? (?:is|are) (?:a )?(?:standard )?security updates?\.',text or '',re.M)
                        if match:
                            row['security_updates'] = int(match[1])
        except FileNotFoundError:
            evidence['error_code'] = 'CACHE_MISSING'
        except (OSError,ValueError,OverflowError):
            evidence['error_code'] = 'CACHE_UNAVAILABLE'
        row['sources'].append(evidence)
    return row


def collect(report=None, on_result=None, *, system=None, lstat=os.lstat, read=read_small, now=time.time):
    report = {} if report is None else report
    report.update(schema_version=1,observed_at=utc_now(),status='unsupported',files=[],updates=None,
                  limitations=['Read-only hints, not a complete security audit.',
                               'Cloud security groups and external reachability cannot be confirmed locally.'])
    if (system or platform.system()) != 'Linux':
        return report
    for path,sensitive in POLICIES:
        report['files'].append(inspect_path(path,sensitive,lstat=lstat))
        if on_result is not None:
            on_result()
    report['updates'] = update_evidence(lstat=lstat,read=read,now=now)
    report['status'] = 'partial'
    report['review_count'] = sum(item['status']=='review' for item in report['files'])
    if on_result is not None:
        on_result()
    return report


def render(report, out):
    tr = out.text
    out.row(tr('权限检查范围','Permission scope'),tr('只读权限元数据','Read-only metadata'),'unknown')
    reasons = {
        'WORLD_WRITABLE':('所有用户可写','Writable by everyone'),
        'GROUP_WRITABLE_REVIEW':('同组可写，需审阅','Group-writable; review'),
        'OWNER_NOT_ROOT_REVIEW':('所有者非 root，需审阅','Non-root owner; review'),
        'SENSITIVE_WORLD_READABLE':('敏感文件所有用户可读','Sensitive file readable by everyone'),
    }
    for row in report['files']:
        if row['status'] == 'review':
            value = '; '.join(tr(*reasons[reason]) for reason in row['reasons'])
        elif row['status'] == 'observed':
            value = tr('模式位未见上述宽松项','No listed mode-bit finding')
        else:
            value = tr('未知/跳过','Unknown/skipped')+' ('+row.get('error_code','UNKNOWN')+')'
        out.row(row['source'],row.get('mode','---')+' · '+value,
                'bad' if row['status']=='review' else 'ok' if row['status']=='observed' else 'unknown')
    update = report.get('updates')
    if update:
        pending = update['pending_updates']
        out.row(tr('缓存待更新数','Cached pending updates'),tr('未知','Unknown') if pending is None else str(pending),'unknown')
        for source in update['sources']:
            if 'age_hours' in source:
                out.row(tr('更新缓存年龄','Update cache age'),f"{source['age_hours']:g} h · "+source['source'],'unknown')
    out.row(tr('安全结论','Security conclusion'),tr('本机只读观测；补丁状态未确认','Local read-only observations; patch status unconfirmed'),'unknown')


def run_console(lang='zh', color='auto', report=None, on_result=None):
    from .console import Console
    report = collect(report,on_result)
    render(report,Console(lang,color))
    return 1 if report.get('review_count') or report['status'] == 'unsupported' else 0
