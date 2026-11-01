import json
import subprocess
import sys

import pytest

from proxydoctor.checks import Command, Host, inspect, port_rows
from proxydoctor.cli import redact


class Ubuntu:
    def __init__(self, commands=None):
        self.commands = commands or {}
        self.calls = []

    def system(self):
        return "Linux", "x86_64"

    def disk_free(self):
        return 5 * 1024**3

    def read(self, path):
        return {"/etc/os-release": 'ID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04 LTS"',
                "/proc/meminfo": "MemAvailable: 1048576 kB\n"}.get(path)

    def run(self, *args):
        self.calls.append(args)
        return self.commands.get(args, Command(None, reason="命令不可用"))


def by_id(data, key):
    return next(item for item in data["checks"] if item["id"] == key)


def test_unavailable_tools_never_become_success():
    data = inspect(Ubuntu())
    for key in ("ports", "ssh", "firewall", "service", "public_ip", "cloud_firewall"):
        assert by_id(data, key)["status"] == "unknown"
    assert by_id(data, "system")["status"] == "pass"


@pytest.mark.parametrize("distribution,version,status", [
    ("ubuntu", "20.04", "warn"), ("ubuntu", "21.10", "warn"),
    ("ubuntu", "22.04", "pass"), ("ubuntu", "22.10", "pass"),
    ("ubuntu", "24.04", "pass"), ("ubuntu", "26.04", "pass"),
    ("ubuntu", "26.10", "pass"), ("ubuntu", "", "unknown"),
    ("ubuntu", "noble", "unknown"), ("ubuntu", "22.4", "unknown"),
    ("ubuntu", "22.99", "unknown"), ("ubuntu", "24.04-dev", "unknown"),
    ("debian", "24.04", "warn"), ("linuxmint", "22.04", "warn"),
])
@pytest.mark.parametrize("lang", ["zh", "en"])
def test_minimum_ubuntu_version_and_distribution(distribution, version, status, lang):
    host = Ubuntu()
    original_read = host.read
    host.read = lambda path: (f'ID={distribution}\nVERSION_ID="{version}"\nID_LIKE=ubuntu'
                              if path == "/etc/os-release" else original_read(path))
    result = by_id(inspect(host, lang=lang), "system")
    assert result["status"] == status
    if status == "pass":
        assert "22.04" in result["detail"]
        assert "实机" in result["detail"] if lang == "zh" else "real system" in result["detail"]


@pytest.mark.parametrize("endpoint", ["0.0.0.0:8388", "[::]:8388", "127.0.0.1:8388", "*:8388"])
def test_any_existing_listener_is_a_conflict(endpoint):
    host = Ubuntu({("ss", "-H", "-lntu"): Command(0, f"tcp LISTEN 0 4096 {endpoint} *:*\n")})
    assert by_id(inspect(host), "ports")["status"] == "warn"


def test_failed_partial_ss_output_cannot_claim_free_port():
    host = Ubuntu({("ss", "-H", "-lntu"): Command(1, "", "权限不足")})
    assert by_id(inspect(host), "ports")["status"] == "unknown"
    host.commands[("ss", "-H", "-lntu")] = Command(0, "unexpected output")
    assert by_id(inspect(host), "ports")["status"] == "unknown"


def test_empty_successful_ss_only_confirms_no_listener():
    host = Ubuntu({("ss", "-H", "-lntu"): Command(0, "")})
    data = inspect(host)
    assert by_id(data, "ports")["status"] == "pass"
    assert by_id(data, "cloud_firewall")["status"] == "unknown"


def test_ssh_only_retains_selected_settings_and_flags_passwords():
    host = Ubuntu({("sshd", "-T"): Command(0, "port 2222\npasswordauthentication yes\npermitrootlogin prohibit-password\nhostkey /private/secret-path\n")})
    ssh = by_id(inspect(host), "ssh")
    assert ssh["status"] == "warn"
    assert "2222" in ssh["evidence"]
    assert "secret-path" not in json.dumps(ssh)


def test_root_can_be_allowed_by_match_so_default_config_is_not_security_pass():
    host = Ubuntu({("sshd", "-T"): Command(0, "passwordauthentication no\npermitrootlogin no\n")})
    assert by_id(inspect(host), "ssh")["status"] == "unknown"


def test_active_service_does_not_pass_network_tests():
    host = Ubuntu({("systemctl", "is-active", "sing-box.service"): Command(0, "active\n")})
    data = inspect(host, public_ip="8.8.8.8")
    assert by_id(data, "service")["status"] == "pass"
    assert by_id(data, "public_ip")["status"] == "unknown"


def test_redaction_hides_ipv4_and_ipv6_and_preserves_versions():
    data = {"version": "0.1.0", "items": ["eth0: 203.0.113.5", "eth0: 2001:db8::123", "[::]:8388"]}
    result = redact(data)
    assert "203.0.113.5" not in str(result)
    assert "2001:db8::123" not in str(result)
    assert result["version"] == "0.1.0"
    assert result["items"][2] == "[[IP已隐藏]]:8388"


def test_execution_allowlist_blocks_mutations():
    with pytest.raises(ValueError):
        Host().run("ufw", "enable")


def test_timeout_and_permission_denied_are_unknown(monkeypatch):
    monkeypatch.setattr("proxydoctor.checks.shutil.which", lambda _, **kwargs: "/usr/bin/ss")
    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 8
        assert "shell" not in kwargs
        raise subprocess.TimeoutExpired("ss", 8)
    monkeypatch.setattr("proxydoctor.checks.subprocess.run", timeout)
    assert Host().run("ss", "-H", "-lntu").code is None


def test_windows_does_not_execute_linux_checks():
    host = Ubuntu()
    host.system = lambda: ("Windows", "AMD64")
    data = inspect(host)
    assert not host.calls
    assert by_id(data, "ports")["status"] == "skip"


def test_cli_rejects_bad_input_and_does_not_overwrite_report(tmp_path):
    base = [sys.executable, "-m", "proxydoctor", "check"]
    assert subprocess.run(base + ["--port", "0"], capture_output=True).returncode == 2
    assert subprocess.run(base + ["--public-ip", "not-an-ip"], capture_output=True).returncode == 2
    target = tmp_path / "report.json"
    target.write_text("keep me", encoding="utf-8")
    assert subprocess.run(base + ["--output", str(target)], capture_output=True).returncode == 2
    assert target.read_text(encoding="utf-8") == "keep me"


def test_fixture_export_is_machine_readable():
    host = Ubuntu({("ip", "-j", "address", "show"): Command(0, json.dumps([
        {"ifname": "eth0", "addr_info": [{"scope": "global", "local": "2001:db8::1"}]}]))})
    data = json.loads(json.dumps(redact(inspect(host))))
    assert data["mode"] == "read-only"
    assert "2001:db8::1" not in str(data)
    assert by_id(data, "interfaces")["status"] == "pass"
