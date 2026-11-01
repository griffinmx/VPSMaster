import subprocess

import pytest

from proxydoctor.checks import Command, Host, OUTPUT_LIMIT, SYSTEM_PATH, inspect
from proxydoctor.cli import redact
from test_checks import Ubuntu, by_id


@pytest.mark.parametrize("address", ["2001:db8::1", "::ffff:192.0.2.1", "fe80::1%eth0", "192.0.2.1"])
@pytest.mark.parametrize("lang", ["zh", "en"])
def test_address_redaction_with_punctuation(address, lang):
    result = redact(f"Address ({address}).", lang)
    assert address not in result
    assert "IP" in result
    assert result.endswith(").")


def test_truncated_output_cannot_be_used_as_complete_evidence(monkeypatch):
    def resolve(name, *, path):
        assert path == SYSTEM_PATH
        return "/usr/bin/ss"
    monkeypatch.setattr("proxydoctor.checks.shutil.which", resolve)
    monkeypatch.setattr("proxydoctor.checks.subprocess.run", lambda *a, **kw:
                        subprocess.CompletedProcess(a, 0, "x" * (OUTPUT_LIMIT + 1)))
    result = Host("en").run("ss", "-H", "-lntu")
    assert result.code is None
    assert not result.output
    assert "limit" in result.reason


def test_failed_service_is_not_reported_as_fresh_install():
    host = Ubuntu({("systemctl", "is-active", "sing-box.service"): Command(3, "failed\n"),
                   ("systemctl", "is-enabled", "sing-box.service"): Command(1, "disabled\n")})
    data = inspect(host, lang="en")
    assert by_id(data, "service")["status"] == "warn"
    assert "failed state" in by_id(data, "service")["detail"]
    assert by_id(data, "service_startup")["status"] == "warn"


@pytest.mark.parametrize("state,code,status", [("enabled", 0, "pass"), ("disabled", 1, "warn"),
    ("masked", 1, "warn"), ("enabled-runtime", 0, "warn"), ("static", 0, "unknown"), ("", None, "unknown")])
def test_boot_state_has_its_own_result(state, code, status):
    host = Ubuntu({("systemctl", "is-enabled", "sing-box.service"): Command(code, state)})
    assert by_id(inspect(host), "service_startup")["status"] == status


def test_empty_ssh_output_does_not_claim_settings_were_checked():
    data = inspect(Ubuntu({("sshd", "-T"): Command(0, "")}), lang="en")
    assert "missing required fields" in by_id(data, "ssh")["detail"]


def test_sshd_failure_advice_covers_socket_activated_runtime_directory():
    for lang in ('zh', 'en'):
        data = inspect(Ubuntu({('sshd', '-T'): Command(255, reason='读取命令失败，可能是权限、配置或服务状态问题')}), lang=lang)
        ssh = by_id(data, 'ssh')
        assert ssh['status'] == 'unknown'
        assert ('运行目录' if lang == 'zh' else 'runtime directory') in ssh['advice']


def test_all_ssh_listen_ports_are_preserved():
    host = Ubuntu({("sshd", "-T"): Command(0, "port 22\nport 2222\npasswordauthentication no\npermitrootlogin no\n")})
    evidence = by_id(inspect(host), "ssh")["evidence"]
    assert "port 22\nport 2222" in evidence


def test_missing_os_file_is_unknown():
    host = Ubuntu()
    host.read = lambda _: None
    assert by_id(inspect(host), "system")["status"] == "unknown"


def test_malformed_port_is_not_free():
    host = Ubuntu({("ss", "-H", "-lntu"): Command(0, "tcp LISTEN 0 5 *:99999 *:*\n")})
    assert by_id(inspect(host), "ports")["status"] == "unknown"
