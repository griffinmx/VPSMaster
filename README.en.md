# VPS Check · 1.0 public beta

[中文](README.md) | [English](README.en.md)

Read-only Python VPS diagnostics; internal package/command: proxydoctor. **Public beta, not the final release.** Version: `1.0.0b1`. Local candidate only; not publicly published or finally accepted.

## Install

Final hardening: route outcomes retain permission/dependency/network errors. ICMP/TCP
permissions depend on system traceroute; no automatic elevation. Optional `--geo`
adds estimated location, ASN/operator, provider and time, capped at 12 public lookups.
Interactive frames adapt to narrow terminals. Exact acceptance scope is recorded in
the separate report matching the ZIP SHA256; overseas VPS results are not implied.

Requires Linux, Python 3.10+ and standard-library venv. Target: Ubuntu 22.04 and newer. No Python runtime dependencies, sudo, pip or automatic system package installation. Check the ZIP against a trusted SHA256 digest and review install.py first; Python extraction works without unzip.

```bash
sha256sum -c ProxyDoctor-v1.0.0-beta.1.zip.sha256
python3 -m zipfile -e ProxyDoctor-v1.0.0-beta.1.zip .
cd ProxyDoctor-v1.0.0-beta.1
python3 install.py --run
PD="$HOME/.local/share/proxydoctor/1.0.0b1/bin/proxydoctor"
"$PD" check --theme framed --lang en
"$PD" suite --offline --lang en
```

An isolated user environment is created. Existing destinations are refused; failures clean only the new directory. Missing prerequisites fail clearly. The supplied launcher and Python workers explicitly use -B. This covers supplied launch paths, not arbitrary external imports or pip precompilation; add -B when invoking Python directly.

## Commands

```bash
"$PD" suite --lang en
"$PD" quality --color always --lang en
"$PD" ipquality --show-ip --lang en
"$PD" media --lang en
"$PD" cn-nodes --lang en
"$PD" bandwidth --china --allow-bandwidth --rounds 3 --sample-mib 4 --lang en
"$PD" bandwidth --source mobile-hk --allow-bandwidth --lang en
"$PD" trace --target 1.1.1.1 --method icmp --geo --lang en
"$PD" trace --target 1.1.1.1 --method tcp --tcp-port 443 --lang en
"$PD" return-route --method udp --lang en
"$PD" bgp --target 1.1.1.1 --lang en
"$PD" suite --route-method tcp --include-return-routes --include-bgp --lang en
```

- check/suite support default, iprisk and framed themes, with live results. Explicit language choices override the Linux-console fallback.
- System, visible resource quota, Swap, short steal/PSI, SSH/ports/firewall, file permissions and update-cache observations. No benchmarks or exclusive-resource certification.
- IPv4/IPv6 DNS/TCP/certificate-verified TLS and native UDP trace. ICMP/TCP require existing system traceroute; no elevation or automatic installation.
- IP provider evidence; failed providers remain visible. Optional PTR/outbound TCP25 sends no email.
- Ten media services: public webpage reachability only. No unlock or playback verdict in the CLI.
- Repeated bounded bandwidth requires --allow-bandwidth. Download means node to this host; upload means this host to node. China candidates currently provide download only; Cloudflare supports upload.
- cn-nodes uses small plaintext protocol samples, without credentials or report uploads. Success is not a capacity measurement. Hong Kong Mobile never counts as mainland Mobile coverage.
- Return routes: Beijing/Shanghai/Guangzhou × three carriers, this host to China targets. Not nationwide or reverse-direction coverage. Per-route soft probe budget: 30s; optional geo requests have separate limits.
- BGP: RIPE RIS prefix, origin ASNs, sampled neighbours and AS paths. Collector observations do not prove local selected packet paths, commercial upstreams or premium tiers.

Development-host small JPEG samples succeeded for Shanghai Telecom and Hong Kong Mobile. Mainland Unicom/Mobile do not yet have successful evidence this round. HTTPS throughput never downgrades to HTTP or disables certificate verification. New Linux/overseas network capabilities remain pending real acceptance.

## Reports and safety

Reports/journals are local (reports/ by default), with no overwrites. --show-ip affects only terminal display. Review redacted exports before sharing.

```bash
"$PD" suite --offline --json-output report.json --lang en
"$PD" report --input report.json --output report.md --lang en
"$PD" recover --journal report.json.events.jsonl --output recovered.json --lang en
```

Ctrl+C/SIGTERM cancels workers and attempts to save observations. Operations have timeouts; journals have size limits. Power/storage failure and SIGKILL cannot guarantee unfinished data survives. JSON keeps legacy fields and uniform result items; Markdown uses collision-safe JSON fences.

Exit codes: 0 completed, 1 findings/incomplete/storage failure, 2 usage/install error, 130 cancelled. Defaults do not modify SSH/firewall/routes/system DNS, benchmark, repair or upload complete reports. Online targets see the request source.

P0 automation: 277 passed, one Windows symlink-permission skip. Current VM acceptance is recorded separately in BETA_ACCEPTANCE_REPORT.md and its JSON beside the candidate ZIP, identified by SHA256. Historical Alpha and earlier Beta evidence is not current-build acceptance. Full carrier throughput, ICMP/TCP permission variants and overseas paths require explicit coverage evidence.

No nationwide carrier coverage, long monitoring, DNSBL, Web UI, proxy deployment, Karing subscriptions or automatic updates/uninstall. Install updates into a new directory; back up reports before removing a confirmed old installation.

See [current status](CURRENT_STATUS.md), [changes and pending acceptance](PUBLIC_BETA_CHANGE_REPORT.md), [security](SECURITY.md) and [third-party notices](THIRD_PARTY_NOTICES.md). MIT project, standard-library runtime, no bundled tracing/speed-test binaries.
