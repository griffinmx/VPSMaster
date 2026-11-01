import json
import re
import subprocess
import sys

import pytest

from proxydoctor.checks import Command, inspect
from proxydoctor.cli import redact
from proxydoctor.i18n import MESSAGES, translator
from test_checks import Ubuntu


def test_english_ubuntu_report_has_no_chinese_and_same_results():
    host = Ubuntu()
    zh = inspect(host, lang="zh")
    en = inspect(host, lang="en")
    assert not re.search(r"[\u4e00-\u9fff]", json.dumps(en, ensure_ascii=False))
    assert en["language"] == "en"
    assert [(c["id"], c["status"]) for c in zh["checks"]] == [(c["id"], c["status"]) for c in en["checks"]]


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_reports_and_help_in_selected_language(lang):
    base = [sys.executable, "-m", "proxydoctor"]
    result = subprocess.run(base + ["check", "--lang", lang, "--json", "--public-ip", "2001:db8::123"],
                            capture_output=True, encoding="utf-8")
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert data["language"] == lang
    assert "2001:db8::123" not in result.stdout
    assert data["checks"][0]["title"] == ("操作系统" if lang == "zh" else "Operating system")
    for arguments in (["--lang", lang, "check", "--help"], ["check", "--lang=" + lang, "--help"]):
        help_result = subprocess.run(base + arguments, capture_output=True, encoding="utf-8")
        assert help_result.returncode == 0
        assert ("代理端口" if lang == "zh" else "Intended proxy port") in help_result.stdout
    error = subprocess.run(base + ["check", "--lang", lang, "--port", "0"], capture_output=True, encoding="utf-8")
    assert error.returncode == 2
    assert ("端口必须" if lang == "zh" else "Port must") in error.stderr


def test_success_conflict_and_firewall_branches_translate():
    host = Ubuntu({("ss", "-H", "-lntu"): Command(0, "tcp LISTEN 0 5 [::]:8388 *:*\n"),
                   ("ufw", "status"): Command(0, "Status: active"),
                   ("nft", "list", "ruleset"): Command(0, ""),
                   ("iptables", "-S"): Command(0, "-P INPUT ACCEPT"),
                   ("sshd", "-T"): Command(0, "permitrootlogin yes\npasswordauthentication yes\n"),
                   ("systemctl", "is-active", "sing-box.service"): Command(0, "active")})
    en = redact(inspect(host, public_ip="8.8.8.8", lang="en"), "en")
    assert not re.search(r"[\u4e00-\u9fff]", json.dumps(en, ensure_ascii=False))
    assert "[IP REDACTED]" in json.dumps(en)


def test_catalog_preserves_placeholders_and_rejects_unknown_language():
    for zh, en in MESSAGES.items():
        assert re.findall(r"\{[^}]+\}", zh) == re.findall(r"\{[^}]+\}", en)
    with pytest.raises(ValueError):
        translator("fr")
