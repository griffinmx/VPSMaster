# VPSMaster

**An open-source VPS diagnostics and management toolkit.**

[中文](README.md) · [English](README.en.md) · [Limitations](KNOWN_LIMITATIONS.md) · [Contributing](CONTRIBUTING.md)

VPSMaster is a Python toolkit for Linux VPS users, especially beginners and the Chinese Linux community.
The **1.0.0b1 Beta is CLI-focused**: transparent diagnostics are available; management and Web UI remain planned.
Routine checks do not change SSH, firewall, routes or system DNS. Missing evidence remains unknown.

## Available

| Area | Current Beta | Boundary |
| --- | --- | --- |
| System/resources | OS, kernel, CPU, memory, Swap, disk capacity, visible quotas, short steal/PSI samples | No dedicated-hardware proof or CPU/disk benchmark |
| Network | DNS, IPv4/IPv6 TCP and certificate-verified TLS, interfaces/routes | Subject to permissions, connectivity and target availability |
| Traceroute | Native UDP; optional system ICMP/TCP; IP, RTT, timeout, optional ASN/operator/location | 30 TTLs by default, max64; router silence is not forwarding loss |
| BGP/ASN | RIPE RIS prefixes, origins, neighbours and AS_PATH samples | Collector view, not local packet paths or commercial relationships |
| IP risk | Provider-specific ownership, network type, proxy/VPN/Tor/risk evidence, conflicts | Quotas, missing fields and disagreement remain visible |
| Media | Ten public service pages, including Netflix, Disney+ and YouTube | Reachability only, no unlock or account playback guarantee |
| Security | Read-only SSH, ports, firewall, selected permissions and update caches | No full vulnerability scan or automatic repair |
| Reports | Local redacted JSON/Markdown, recovery journals, English/Chinese themes | Review before sharing; incomplete data may remain partial |
| Opt-in tests | Bounded repeated bandwidth and fixed China targets | Mainland three-carrier coverage is experimental, disabled by default |

Execution success does not mean every provider or destination is available. Results retain status, method, time, source and limitations.

## Install and use

Requires Linux, Python3.10+ and stdlib venv. No third-party Python runtime dependencies, pip, sudo or automatic system package installation.
Obtain the ZIP/checksum through a trusted channel and review install.py. A checksum detects change, not publisher authenticity.

```bash
sha256sum -c VPSMaster-v1.0.0-beta.1.zip.sha256
python3 -m zipfile -e VPSMaster-v1.0.0-beta.1.zip .
cd VPSMaster-v1.0.0-beta.1
python3 -I -B install.py --run
VM="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
"$VM" --version
"$VM" check --theme framed --lang en
"$VM" suite --offline --lang en
"$VM" quality --lang en
"$VM" trace --target 1.1.1.1 --method tcp --tcp-port 443 --geo --lang en
"$VM" bgp --target 1.1.1.1 --lang en
"$VM" media --lang en
"$VM" suite --lang en --json-output report.json
"$VM" report --input report.json --output report.md --lang en
"$VM" recover --journal report.json.events.jsonl --output recovered.json --lang en
```

`--run` initially performs offline checks. Existing installation/report paths are refused; choose a new user-owned `--prefix` for a separate install.
ICMP/TCP require an existing system traceroute and appropriate permissions. Missing dependency/permission failures are explicit; there is no automatic elevation.
Online commands contact external services, which see the source IP. `check` is offline unless its explicit public-IP lookup is selected.

Bandwidth needs explicit consent, for example `bandwidth --allow-bandwidth --rounds 3 --sample-mib 4`.
`--china` selects experimental mainland candidates; availability is incomplete. Hong Kong Mobile never substitutes for mainland Mobile.
Download means node → this host, upload means this host → node. Short samples are not line capacity.
The current `attempted` summary counts scheduled sample slots, including skipped slots, not actual wire requests; inspect sample errors.

### Compatibility

Former project name: **ProxyDoctor**. New visible brand/command: **VPSMaster / vpsmaster**.
The installer also creates the legacy `proxydoctor` launcher. Python package/distribution identity `proxydoctor`, imports, JSON schemas and `PROXYDOCTOR_*` variables remain compatible.
New installs default to `~/.local/share/vpsmaster/1.0.0b1`; old directories/reports are not migrated or overwritten.
Both source scripts `vpsmaster.sh` and `proxydoctor.sh` remain usable. Supplied launchers/workers use `-B`; arbitrary external imports are outside that promise.

### Illustrative CLI output

Placeholders below show structure, **not benchmark results for this build**:

```text
1.0.0b1 · VPSMaster · 1.0 public beta (not the final release)
 1  127.0.0.1    <RTT> ms    Private/reserved  AS? --- [reached]
Trace result       reached
Recovery journal: <local path>
```

## Validation and limitations

Lab baselines are Ubuntu22.04.5 Desktop/Python3.10.12 and Ubuntu24.04.3 Server/Python3.12.3, x86_64.
Each VPSMaster candidate requires fresh installation from its final ZIP; only a matching-SHA acceptance report establishes that build's pass.
The old ProxyDoctor ZIP is preserved and cannot be renamed as proof for the new build.
ICMP/TCP loopback success and limited public observations do not establish complete public routing.

- Media is public-page reachability, not unlock, paid entitlement or actual playback.
- Mainland three-carrier speed testing is experimental and off by default.
- BGP/geolocation depend on third-party accuracy, terms and quotas; geography is estimated.
- Overseas VPS, ARM, public IPv6 and a fresh Ubuntu22 Server image are not comprehensively validated.
- PTY bytes/width checks do not prove GUI font rendering. Beta is not production stability or independent security certification.
- No Web UI, automated proxy deployment, full management panel, long monitoring or CPU/disk benchmarks are currently provided.

See [full limitations](KNOWN_LIMITATIONS.md), [status](CURRENT_STATUS.md) and [Beta notes](RELEASE_NOTES.md).

## Security and privacy

No default configuration changes, automatic repairs or full-report uploads. Installation creates a user venv; diagnostics/reports create local files.
`--show-ip` affects the terminal; exported files mask known IP/credential patterns, not arbitrary identifying text. Review before sharing.
Ctrl+C/SIGTERM attempts cancellation and persistence; recovery uses the last complete journal event. SIGKILL, power/storage failure can prevent final JSON.
Exit codes: 0 completed, 1 findings/incomplete/storage failure, 2 usage/install error, 130 cancelled.
Never publish raw logs, subscriptions, passwords, tokens or keys. See [SECURITY.md](SECURITY.md).

## Roadmap — Planned

These are future goals, **not claims of current implementation**. Stage1 deepens existing basic diagnostics. No delivery dates are promised.

1. **Network and hardware:** improve mainland three-carrier tests; deepen ICMP/TCP/UDP diagnosis; BGP/ASN/path analysis; CPU/disk benchmarks; more IP intelligence/reputation sources.
2. **Long-term diagnosis:** stability monitoring; peak-hour analysis; historical report comparison; anomaly detection/advice; VPS purchase acceptance reports.
3. **Security and maintenance:** deeper audits; repair suggestions/previews; configuration backup/rollback; maintenance assistance.
4. **Automation and Web UI:** optional service deployment; modular management; local Web UI; state visualization; optional service configuration/management.

## Contributing, Issues and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Once a repository is published, use its **Issues → New issue** tab with the bundled [bug](.github/ISSUE_TEMPLATE/bug_report.md) or [feature](.github/ISSUE_TEMPLATE/feature_request.md) template.
No public repository URL is configured yet; no fictional owner/repo link is supplied. Use private channels for sensitive vulnerability reports.

MIT project; former-brand contributor notices remain in [LICENSE](LICENSE).
No third-party traceroute clients, databases or remote test scripts are bundled/executed. References/attribution are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [OPEN_SOURCE_REFERENCES.md](OPEN_SOURCE_REFERENCES.md).
Our license does not grant rights to third-party APIs/data/test services; their terms, quotas and permissions apply separately.
Reports do not expire automatically; review [data-service retention/sharing terms](docs/DATA_SERVICES.md), including applicable IP2Location cache limits.
