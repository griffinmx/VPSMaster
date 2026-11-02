# VPSMaster

**Know your VPS. Manage your server more safely.**

VPS Diagnostics & Security Toolkit — an open-source Linux VPS diagnostics and security management toolkit.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue) ![Linux](https://img.shields.io/badge/Platform-Linux-lightgrey) [![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE) ![Beta.1](https://img.shields.io/badge/Status-Beta.1-orange)

[中文首页](README.md) · [Usage](docs/guide/USAGE.md) · [Issues](https://github.com/griffinmx/VPSMaster/issues)

## About

VPSMaster helps Linux users and VPS beginners understand server resources, connectivity, IP information and basic security risks. **v1.0.0-beta.1** provides CLI diagnostics and local reports. Default checks are read-only and do not change SSH, firewall, routes or system DNS.

The project will grow toward server management: improved diagnostics, configuration backup and recovery, optional proxy deployment, security hardening and a local Web UI. These management capabilities are future plans, not current Beta features.

## Features

| Module | Available now |
| --- | --- |
| Server | Linux, CPU, memory, swap, disk capacity, virtualization and resource observations |
| Network | DNS, TCP/TLS, IPv4/IPv6 and UDP/ICMP/TCP traceroute |
| Routing & IP | BGP, ASN, ownership, network types and provider-specific risk information |
| Services | Public-page reachability for selected media services |
| Security | Read-only SSH, port, firewall and file-permission checks |
| Reports | Chinese/English CLI, JSON/Markdown, redaction and interruption recovery |

## Install from public GitHub

Requires **Linux, Python 3.10+, standard-library venv and Git**. Ubuntu 22.04 / 24.04 is recommended.

```bash
git clone https://github.com/griffinmx/VPSMaster.git
cd VPSMaster
python3 -I -B install.py --run
```

The installer verifies the manifest, creates an isolated user environment and runs an **offline** check. It requires no root and invokes neither pip, sudo nor a package manager. Default location: `~/.local/share/vpsmaster/1.0.0b1/`.

Start the online scan separately:

```bash
~/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster all --lang en
```

The online scan saves local reports and has a default 300-second budget. Missing permissions, tools or reachable targets can yield unknown/skipped/incomplete results without a program crash. [Install/update/uninstall](docs/guide/INSTALL.md)

## One-command diagnostics

Optionally define an alias in your current shell:

```bash
alias vpsmaster="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
vpsmaster all --lang zh
vpsmaster all --lang en
vpsmaster all --offline --lang en
vpsmaster all --full --lang en
```

`all` reuses existing modules and shows live progress and a final summary. It covers resources/interfaces, DNS/TCP/TLS, UDP and available ICMP/TCP, IP/ASN/BGP, pages and basic security. Unknown is not success. Default limits: 300 seconds total, 60 per module; full mode allows 600 total.

`--full` adds PTR/TCP25 and bounded China-destination traces. Bandwidth needs separate `--allow-bandwidth` consent, with a 64 MiB test-payload cap. Mainland speed candidates additionally need experimental `--china-speed`. No bandwidth, CPU or disk benchmark runs by default. [Full usage](docs/guide/USAGE.md)

## Common commands

Use the printed launcher path for custom installations.

```bash
VM="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
"$VM" all --lang en
"$VM" all --offline --lang en
"$VM" check --lang en
"$VM" quality --lang en
"$VM" trace --target 1.1.1.1 --method udp
"$VM" ipquality
"$VM" bgp --target 1.1.1.1
"$VM" suite --json-output report.json
"$VM" report --input report.json --output report.md
"$VM" --help
```

The legacy `proxydoctor` command remains supported. External services see your source IP; inspect reports before sharing.

## FAQ and limits

- A Git proxy is not automatically used by VPSMaster; some probes connect directly. DNS success does not imply TCP/TLS success.
- A Linux text console may lack Chinese fonts. Use a suitable UTF-8 SSH terminal or `--lang en`.
- Media checks mean public-page reachability, not unlocking or playback. Mainland carrier tests remain experimental/off by default.
- ICMP/TCP may need system `traceroute` and permissions. BGP, location and risk data depend on third parties.
- Main lab coverage is Ubuntu22 Desktop/Ubuntu24 Server, x86_64. Overseas VPS, ARM, public IPv6 and more fresh images are not comprehensively validated.
- No automatic proxy deployment, hardening, configuration rollback or Web UI exists in this Beta. It is not production stability or independent security certification.
- Redaction is not an arbitrary-text anonymizer; review IP/topology and other sensitive information before sharing.

[Detailed limits](docs/release/KNOWN_LIMITATIONS.md) · [Release notes](docs/release/RELEASE_NOTES.md)

## Five-phase roadmap

| Phase | Direction | Status |
| --- | --- | --- |
| 1 · Comprehensive VPS diagnostics | Resources, connectivity, routes, BGP/IP, basic security and local recoverable reports | Current Beta foundation |
| 2 · Better diagnostics and backup/rollback | Clearer CLI reports, CPU/disk benchmarks, carrier tests, IP cross-checking, routing advice, security baselines, snapshots/diffs and basic recovery | Planned |
| 3 · One-click proxy deployment | Common protocols, installation/configuration, health, updates/uninstall, then domains/certificates/subscriptions | Planned |
| 4 · One-click security hardening | SSH/key policies, UFW/nftables, Fail2ban, updates/permissions/ports; plans, previews, verification and conditional rollback | Future priority |
| 5 · Web UI and server management | Local dashboard, reports/risks, backups/recovery, multiple VPS and optional services | Long-term plan |

Phase 2 builds verifiable backup/recovery foundations alongside diagnostic improvements. Phase 3 prioritizes basic deployments without a domain before domain/certificate-based configurations, with secure configuration and service lifecycle handling.

Phase 4 requires explicit confirmation for changes affecting SSH, firewall or access: **detect → explain → preview → confirm → back up → execute → verify → roll back**. Protect management connections and business ports; rollback cannot cover every outage, cloud firewall, reboot or host failure.

A future local Web UI must not expose its management entry point publicly by default; authentication, authorization and credential protection are essential. **Phases 2–5 are plans, not implemented Beta.1 capabilities, and have no fixed release dates.** [Detailed roadmap](docs/security/ROADMAP.md)

## Documentation and contributing

[Usage](docs/guide/USAGE.md) · [中文首页](README.md) · [Installation](docs/guide/INSTALL.md) · [Limits](docs/release/KNOWN_LIMITATIONS.md) · [Roadmap](docs/security/ROADMAP.md)

[Docs](docs/README.md) · [Security/privacy](docs/security/SECURITY.md) · [Issues](https://github.com/griffinmx/VPSMaster/issues) · [Contributing](docs/development/CONTRIBUTING.md) · [MIT License](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Please share reproducible, redacted feedback. Never upload passwords, tokens, SSH private keys or unchecked raw reports to public Issues.
