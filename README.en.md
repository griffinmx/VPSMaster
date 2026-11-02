# VPSMaster

**Know your VPS. Manage your server more safely.**

VPS Diagnostics & Security Toolkit — an open-source Linux VPS diagnostics and security management toolkit.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue) ![Linux](https://img.shields.io/badge/Platform-Linux-lightgrey) [![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE) ![Beta.1](https://img.shields.io/badge/Status-Beta.1-orange)

[中文首页](README.md) · [Usage](docs/guide/USAGE.md) · [Issues](https://github.com/griffinmx/VPSMaster/issues)

## About

Built with Python for VPS beginners and Linux users, VPSMaster helps explain server resources, connectivity, IP information and basic security risks. Beta.1 provides CLI diagnostics and local reports. Default diagnostics are read-only and do not modify SSH, firewall, routes or system DNS.

The project aims to grow into a Linux security diagnostics and hardening assistant, with SSH/firewall hardening, configuration backup and rollback, continuous security monitoring and a local Web UI as future priorities.

## Features

| Module | Available now |
| --- | --- |
| Server | Linux, CPU, memory, swap, disk capacity, virtualization and resource observations |
| Network | DNS, TCP/TLS, IPv4/IPv6 and UDP/ICMP/TCP traceroute |
| Routing & IP | BGP, ASN, ownership, network types and provider-specific risk observations |
| Services | Basic public-page reachability for selected media services |
| Security | Read-only SSH, port, firewall and file-permission checks |
| Reports | Chinese/English CLI, local JSON/Markdown, redaction and interruption recovery |

## Install

Requires **Linux, Python 3.10+ and standard-library venv**. Download the ZIP and matching `SHA256SUMS.txt` from [Releases](https://github.com/griffinmx/VPSMaster/releases) into the same directory. During private testing, access is restricted; a release draft is not a generally available published download.

```bash
sha256sum -c SHA256SUMS.txt
python3 -m zipfile -e VPSMaster-v1.0.0-beta.1.zip .
cd VPSMaster-v1.0.0-beta.1
python3 -I -B install.py --run
```

The installer creates an isolated user environment and prints the launcher path. The first scan is offline. Root is not required; the installer invokes neither pip, sudo nor a system package manager. Missing dependencies produce an error without changing the system. [Installation guide](docs/guide/INSTALL.md)

## Common commands

Use the printed launcher path for custom installations; the default is:

```bash
VM="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
"$VM" check --lang en
"$VM" suite --offline --lang en
"$VM" quality --lang en
"$VM" trace --target 1.1.1.1 --method udp
"$VM" ipquality
"$VM" suite --json-output report.json
"$VM" report --input report.json --output report.md
"$VM" --help
```

The legacy `proxydoctor` command remains compatible. See [usage](docs/guide/USAGE.md) for full options and opt-in bandwidth tests. Remote services see your source IP; review redacted reports before sharing.

## Beta limitations

- Media checks test page reachability, not unlocking or playback. Mainland three-carrier bandwidth tests are experimental and off by default.
- ICMP/TCP may require system `traceroute` and permissions. BGP, geography and risk observations depend on third-party data.
- Lab coverage: Ubuntu 22.04 Desktop and 24.04 Server, x86_64. Overseas VPS, ARM, public IPv6 and a fresh Ubuntu 22.04 Server image are not comprehensively validated.
- No one-click hardening, automatic proxy deployment or Web UI. Beta does not imply production stability or independent security certification.

[Detailed limitations](docs/release/KNOWN_LIMITATIONS.md) · [Release notes](docs/release/RELEASE_NOTES.md)

## Roadmap

| Phase | Direction | Status |
| --- | --- | --- |
| 1 · VPS diagnostics | Resources, connectivity, routes, BGP/IP, basic security and recoverable reports | Current Beta foundation |
| 2 · Improve diagnostics | CPU/disk benchmarks, mainland carrier tests, IP cross-checking, routing advice, security baselines and purchase acceptance | Planned |
| 3 · Security hardening | SSH/key policies, UFW/nftables, Fail2ban, updates and permissions, with selectable plans and previews | Planned; future priority |
| 4 · Backup, rollback & monitoring | Configuration backups/diffs, SSH access protection, verification, conditional rollback, auditing and monitoring | Planned |
| 5 · Visual management | Local Web UI, risks/tasks, recovery, multiple VPS and optional service management | Long-term plan |

Future hardening requires explicit confirmation: **detect → explain → preview → confirm → back up → execute → verify → roll back**. Protecting SSH access is essential; rollback cannot cover every outage. A future management UI must not expose its entry point publicly by default.

Future capabilities are not implemented or included in this Beta, and have no fixed delivery dates. [Detailed roadmap](docs/security/ROADMAP.md)

## Documentation & contributing

[Usage](docs/guide/USAGE.md) · [中文首页](README.md) · [Installation](docs/guide/INSTALL.md) · [Limitations](docs/release/KNOWN_LIMITATIONS.md) · [Roadmap](docs/security/ROADMAP.md)

[Documentation](docs/README.md) · [Security/privacy](docs/security/SECURITY.md) · [Issues](https://github.com/griffinmx/VPSMaster/issues) · [Contributing](docs/development/CONTRIBUTING.md) · [MIT License](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
