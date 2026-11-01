"""Read-only security fixtures; execution deferred at the user's request."""
import json
import stat
from types import SimpleNamespace

from proxydoctor.security import collect, inspect_path, update_evidence


def metadata(mode,uid=0,modified=3600):
    return SimpleNamespace(st_mode=mode,st_uid=uid,st_gid=42,st_mtime=modified)


def test_shadow_group_read_is_not_a_finding():
    row = inspect_path('/etc/shadow',True,lstat=lambda _:metadata(stat.S_IFREG|0o640))
    assert row['status'] == 'observed'


def test_world_readable_shadow_and_writable_configuration_require_review():
    row = inspect_path('/etc/shadow',True,lstat=lambda _:metadata(stat.S_IFREG|0o644))
    assert row['reasons'] == ['SENSITIVE_WORLD_READABLE']
    row = inspect_path('/etc/sudoers',lstat=lambda _:metadata(stat.S_IFREG|0o666,uid=1000))
    assert 'WORLD_WRITABLE' in row['reasons']
    assert 'GROUP_WRITABLE_REVIEW' in row['reasons']
    assert 'OWNER_NOT_ROOT_REVIEW' in row['reasons']


def test_symlinks_are_not_followed_or_called_safe():
    row = inspect_path('/etc/shadow',True,lstat=lambda _:metadata(stat.S_IFLNK|0o777))
    assert row['status'] == 'unknown'
    assert row['error_code'] == 'SYMLINK_REQUIRES_REVIEW'


def test_permission_error_does_not_expose_exception_text():
    def denied(_):
        raise PermissionError('secret-path-token')
    row = inspect_path('/etc/shadow',True,lstat=denied)
    assert row['error_code'] == 'METADATA_UNAVAILABLE'
    assert 'secret-path-token' not in json.dumps(row)


def test_missing_cache_does_not_mean_zero_updates():
    def missing(_):
        raise FileNotFoundError
    row = update_evidence(lstat=missing)
    assert row['status'] == 'unknown'
    assert row['pending_updates'] is None


def test_cache_is_timestamped_observation_not_patch_verdict():
    row = update_evidence(lstat=lambda _:metadata(stat.S_IFREG|0o644),now=lambda:7200,
                          read=lambda _:'12 updates can be applied immediately.\n3 of these updates are standard security updates.')
    assert row['pending_updates'] == 12
    assert row['security_updates'] == 3
    assert row['sources'][0]['age_hours'] == 1
    assert row['status'] == 'cached_observation'


def test_localized_summary_stays_unknown_and_raw_text_is_not_retained():
    row = update_evidence(lstat=lambda _:metadata(stat.S_IFREG|0o644),now=lambda:7200,
                          read=lambda _:'中文缓存 secret-key')
    assert row['pending_updates'] is None
    assert 'secret-key' not in json.dumps(row)


def test_collect_does_not_read_password_file_contents():
    reads = []
    def read(path):
        reads.append(path)
        assert path == '/var/lib/update-notifier/updates-available'
        return None
    row = collect(system='Linux',lstat=lambda _:metadata(stat.S_IFREG|0o640),read=read,now=lambda:7200)
    assert len(row['files']) == 9
    assert reads == ['/var/lib/update-notifier/updates-available']


def test_non_linux_does_not_inspect_host_files():
    def unexpected(_):
        raise AssertionError('Linux paths should not be read')
    assert collect(system='Windows',lstat=unexpected,read=unexpected)['status'] == 'unsupported'
