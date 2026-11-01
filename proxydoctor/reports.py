"""Local, exclusive report files and durable per-module recovery snapshots."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def exclusive_text(path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    return os.fdopen(fd, 'w', encoding='utf-8')


class ReportStore:
    """JSONL is authoritative for recovery; a final JSON is created on completion.

    Only complete newline-terminated events are recovery records. No exception
    strings are stored. Callers supply their redactor, including for checkpoints.
    """
    def __init__(self, destination, redact):
        if destination is None:
            directory = Path('reports')
            directory.mkdir(mode=0o700, exist_ok=True)
            destination = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                                       + '-' + uuid.uuid4().hex + '.json')
        self.path = Path(destination)
        if os.path.lexists(self.path):
            raise FileExistsError('Report destination exists')
        self.journal_path = self.path.with_name(self.path.name + '.events.jsonl')
        self.redact = redact
        self.stream = exclusive_text(self.journal_path)
        self.failed = False
        self.bytes_written = 0

    def checkpoint(self, report):
        if self.failed:
            return False
        try:
            event = {'event_version': 1, 'saved_at': utc_now(),
                     'snapshot': self.redact(report)}
            body=json.dumps(event, ensure_ascii=False) + '\n'
            size=len(body.encode('utf-8'))
            if size>4*1024**2 or self.bytes_written+size>64*1024**2:
                self.failed=True
                return False
            self.stream.write(body)
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.bytes_written+=size
            return True
        except (OSError, ValueError, TypeError):
            self.failed = True
            return False

    def finish(self, report):
        saved = self.checkpoint(report)
        try:
            # Never replace a file created by another process during detection.
            with exclusive_text(self.path) as output:
                json.dump(self.redact(report), output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
        except (OSError, ValueError, TypeError):
            self.failed = True
            return False
        return saved

    def close(self):
        try:
            self.stream.close()
        except OSError:
            self.failed = True


def recover_latest(path, max_bytes=64*1024**2, max_line_bytes=4*1024**2):
    """Read the last complete checkpoint, ignoring an interrupted final write.

    Recovery files are local trusted inputs; this function does not contact any
    service or execute content. A malformed line is not a successful checkpoint.
    """
    latest = None
    consumed = 0
    with Path(path).open('rb') as stream:
        while True:
            line = stream.readline(max_line_bytes+1)
            if not line:
                break
            consumed += len(line)
            if consumed > max_bytes or len(line)>max_line_bytes:
                raise ValueError('Recovery journal exceeds read budget')
            if not line.endswith(b'\n'):
                break
            try:
                event = json.loads(line)
                if event.get('event_version') == 1 and isinstance(event.get('snapshot'), dict):
                    latest = event['snapshot']
            except (ValueError, AttributeError):
                continue
    return latest


class UnavailableStore:
    """Continue terminal checks when local storage cannot be opened."""
    def __init__(self, destination):
        self.path = Path(destination) if destination else Path('reports')
        self.journal_path = None
        self.failed = True

    def checkpoint(self, report):
        return False

    def finish(self, report):
        return False

    def close(self):
        pass
