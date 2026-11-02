> 历史材料：版本、测试数量与旧路径仅说明当时状态，不是本次构建的验收证据。参见[当前发行说明](../release/RELEASE_NOTES.md)。

See [current status](README.md) for implemented and outstanding work. Family-specific DNS/TCP/TLS checks now back suite/quality; untested.

# Current development scope (2026-11-01)

This branch develops an independent Python VPS diagnostics CLI. See [backlog](README.md), [architecture](ARCHITECTURE-alpha.md), [source research](OPEN_SOURCE_RESEARCH.md), [test plan](TEST_PLAN-alpha.md), and [changelog](../release/CHANGELOG.md). The previous 0.5.0 documentation below is historical context.

Routine `proxydoctor suite` skips CPU and bandwidth benchmarks. Consent to traffic tests with `proxydoctor bandwidth --allow-bandwidth` or `proxydoctor suite --allow-bandwidth`. The displayed payload budget excludes protocol overhead and other checks. Use `suite --offline` to skip network checks. Third-party executable/script wrappers are temporarily disabled.

These changes have not been tested or released. Earlier test results do not validate this branch.

---

# ProxyDoctor

[中文](../README.md) | [English](../../README.en.md)

Native Python read-only VPS diagnostics for Ubuntu 22.04 and newer. Python 3.10+;
no third-party runtime dependencies. Ubuntu 22.04/24.04 are the current acceptance
targets; other versions need separate testing. No automatic sudo, installation,
SSH/firewall changes or fetching/executing remote scripts.

## Run

Extract the source package and run from its directory:

```bash
bash proxydoctor.sh
bash proxydoctor.sh suite --lang en
bash proxydoctor.sh suite --offline --lang en
python3 -m proxydoctor check --lang en --port 8388 --json --output check.json
```

Downloading/cloning does not execute code. The default `suite` contacts external
services and streams compact colored rows. `check` defaults to local reads.
Ordinary users can run it; missing privileges remain unknown. Report files stay
local, do not overwrite existing files and redact IPs. Review before sharing;
redaction is not an anonymity guarantee. `--show-ip` displays egress IP in the
terminal only. Routes display actual hop IPs in the terminal; exports mask them.

## Four modules

| Module | Terminal output | Limits |
| --- | --- | --- |
| Resources/preflight | OS, architecture, CPU/model/count, kernel, memory, disk, SHA-256 sample; route/DNS config, target port, SSH guard/config, local/cloud firewall status | Visible resources may differ from quotas; SHA-256 is not a general CPU benchmark; local reads cannot establish cloud ingress |
| Network/IP | Real DNS/TCP probes; ownership/ASN/location/type, provider flags/scores, coverage and disagreements | AAAA answers do not prove IPv6 connectivity; provider scores are separate observations, not safety certification |
| Route | Linux IPv4/IPv6 UDP error queue, 30 hops by default, up to 64; IP, latency, estimated location | NAT/filtering or silent routers can prevent completion; geolocation is approximate |
| Media | Ten independent service adapters, repeat confirmation, catalog/metadata evidence and explicit unknown reasons | No paid account/DRM playback verification; public offers/catalogs do not prove full unlock |

Suite JSON schema_version=2 includes local checks, DNS/TCP, per-source bandwidth,
IP observations/provenance/conflicts, route hops and media probe evidence.
Green indicates acquired data/local success, red known warnings/restrictions,
yellow unknown/skipped/insufficient evidence. `--color auto|always|never` and
`NO_COLOR` are supported. Use `check --json` for detailed local evidence.
`sshd -T` defaults may differ from running instances/Match rules. Future repair
features still require separate SSH safeguards.

## Bandwidth

```bash
bash proxydoctor.sh bandwidth --lang en
bash proxydoctor.sh bandwidth --lang en --source ovh-rbx --rounds 3 --sample-mib 4
bash proxydoctor.sh bandwidth --lang en --source hetzner-fsn --sample-mib 1
bash proxydoctor.sh suite --lang en --bandwidth-source cloudflare
```

| ID | Source/node label | Download | Upload | Default |
| --- | --- | --- | --- | --- |
| cloudflare | Cloudflare / Anycast | Yes | Yes | Yes |
| ovh-rbx | OVHcloud / FR Roubaix | Yes | No | Yes |
| hetzner-fsn | Hetzner / DE Falkenstein | Yes | No | No; slow on current test network |

Excluded 128 KiB warmup per supported direction; 3–8 measured rounds of 1–20 MiB.
Default requested benchmark payload is at most 36.375 MiB, excluding protocol
and other module traffic. Medians/ranges/success counts stay separate per source.
Short samples (<1s), missing rounds and high variation stay yellow. Wall-time
HTTPS throughput includes connection setup and cannot verify advertised capacity.
Static files require exact HTTP 206 ranges; ignored Range responses are closed
without reading the full body, never falling back to a full-file download.
Unsupported upload is skipped, not counted as failure. Bandwidth JSON schema=2.

## IP sources and keys

```bash
bash proxydoctor.sh ipquality --lang en --show-ip --json-output ip.json
bash proxydoctor.sh ipquality --lang en --no-enrichment
bash proxydoctor.sh suite --lang en --no-ip-enrichment
```

Defaults: ipapi.is, proxycheck.io and IP2Location. On an ipapi.is transport failure,
ipify can provide an egress address. Subsequent sources query that exact address;
mismatched responses are rejected. These services see the source address and the
additional sources receive the selected egress IP. Disable extra sources with
`--no-ip-enrichment` or all suite networking with `--offline`.

Seventeen core fields cover ownership/ASN, location/timezone, type/network abuse
share and datacenter/proxy/VPN/Tor/recent-abuse/mobile/satellite/anycast/bogon flags.
Per-source observations and field provenance are retained. Conflicting booleans
become unknown with disagreement evidence. IP2Location's limited free-plan proxy
flag is kept separate, not converted into a broad VPN guarantee. proxycheck.io
risk/confidence and AbuseIPDB scores are not averaged. Network abuse share is not
a single-IP maliciousness probability.

Keyless limits currently include 100 queries/day for proxycheck.io and 1000/day
for IP2Location, subject to provider rules. No automatic quota retries. Anonymous
ipapi.is has limited fields; optional keys provide extended fields/AbuseIPDB reports.
Enter locally without echoing; never send keys to chat or commit them:

```bash
read -rsp 'ipapi.is API Key: ' PROXYDOCTOR_IPAPI_KEY
export PROXYDOCTOR_IPAPI_KEY
printf '\n'
read -rsp 'AbuseIPDB API Key: ' PROXYDOCTOR_ABUSEIPDB_KEY
export PROXYDOCTOR_ABUSEIPDB_KEY
printf '\n'
bash proxydoctor.sh ipquality --lang en
```

ipapi.is keys travel in HTTPS POST JSON; AbuseIPDB keys use headers, not URLs or
reports. Missing fields remain unknown. Complete coverage means defined fields,
not every database or a security certification. Zero reports do not guarantee
safety. Observed API egress/family may differ from media connections.

## Route and media

```bash
bash proxydoctor.sh suite --lang en --max-hops 64 --route-target 1.1.1.1
bash proxydoctor.sh suite --lang en --route-target 2606:4700:4700::1111 --no-geo
bash proxydoctor.sh media --lang en --json-output media.json
```

ipwho.is geolocation is cached per run; private/reserved hops are never queried.
Media covers Netflix, Disney+, YouTube Premium, Spotify, Prime Video, Max, Apple
TV+, Hulu, BBC iPlayer and Paramount+. Clear regional messages and visible priced
offers require repeat agreement. Netflix uses structured catalog metadata; BBC
also checks public test-channel metadata. No media segments/paid content are
fetched and signed media URLs are not retained. BBC's channel result is scoped
to that channel. HTTP 200/403 or catalog/offer visibility never proves playback.

## Exit codes

`check`: 0=no known warning/failure (unknowns may remain), 1=findings, 2=usage/export
error. Online suite/bandwidth/ipquality/media: 1 also covers incomplete/unknown/
variable measurements or unverified playback. Offline 0 means local execution
completed, not online success. Media intentionally leaves playback untested and
returns 1. Ctrl+C returns 130 without changing system settings.

## Install and contribute

Source runs directly. Install the supplied wheel into a local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install /path/to/proxydoctor-0.5.0-py3-none-any.whl
.venv/bin/proxydoctor suite --offline --lang en
```

If Ubuntu lacks venv support, install its matching OS component separately;
ProxyDoctor never installs it automatically. Development: install pytest and run
`python -m pytest -q`. An Actions workflow is supplied; remote CI is not claimed
before repository publication. See [CONTRIBUTING.md](../development/CONTRIBUTING.md) and [SECURITY.md](../security/SECURITY.md).

## Stage 1 and scope

This iteration targets code plus Ubuntu 22.04/24.04 VM acceptance as selected by
the user; consult the delivered acceptance records for actual results. Overseas
VPS tests, real-key extended data, paid-account playback and other Ubuntu releases
remain separately unverified. Later stages cover sing-box installation, Karing
protocol validation, repair previews/backups/rollback, Web UI and secure subscription
transport. No public plaintext subscription server or automatic SSH/firewall changes.

## License and acknowledgements

Original code is MIT. Thanks to ECS, NodeQuality, NetQuality/IPQuality, NextTrace
and RegionRestrictionCheck for feature/presentation references. No upstream script
source/databases are bundled by the default implementation. See [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
Explicit local-script adapters are opt-in; external behavior/output may not be
read-only or redacted.

Official data references: [Cloudflare](https://github.com/cloudflare/speedtest),
[OVHcloud](https://proof.ovh.net/), [Hetzner](https://docs.hetzner.com/storage/object-storage/troubleshooting/bandwidth-latency-issues/),
[ipapi.is](https://ipapi.is/developers.html), [proxycheck.io](https://proxycheck.io/api/),
[IP2Location](https://www.ip2location.io/ip2location-documentation), [AbuseIPDB](https://docs.abuseipdb.com/),
[ipwho.is](https://ipwhois.io/documentation), [ipify](https://www.ipify.org/).
[Netflix VPN guidance](https://help.netflix.com/en/node/114701) explains catalog restrictions.


## Reliability batch — 2026-11-01 (implemented, untested)

`suite` now creates a local redacted JSON report and sibling `.events.jsonl` recovery journal. Without `--json-output`, files are placed under `./reports/` with unique names. Detection does not modify system configuration, but does write these local output files. Linux file creation requests mode 0600; Windows uses inherited ACLs.

Each module start/completion and completed DNS/TCP result, route hop, and media service writes a flushed/fsynced snapshot. Module exceptions use `MODULE_ERROR` without storing raw exception text; other modules continue. `success` in `modules` means the module executed, not that a service is unlocked or a server is safe. Overall partial measurement remains incomplete. Ctrl+C records cancellation and returns 130. Previously completed journal records remain useful after a crash; use the Python `proxydoctor.reports.recover_latest(path)` API to read the latest complete snapshot.

Existing final/journal files and dangling final symlinks are rejected. Storage errors during checks produce a terminal warning, keep prior records, and return a nonzero result. The final JSON is exclusively created; a failed final write can leave a partial final file, so recover from the journal. No absolute durability guarantee applies to disk/controller failure. Storage paths must be in user-controlled directories; parent-directory symlink attacks are outside this first implementation.

Limits: module-level isolation does not isolate every individual local system check. Bandwidth and IP collection currently checkpoint on module completion; interruption can lose the current module's unfinished results. Media cancellation may wait for in-flight bounded network calls when the thread pool exits. SIGKILL/power loss cannot trigger cleanup; the journal contains only the last complete checkpoint. Standalone commands retain their existing save behavior. These changes and the new fault-injection tests have not been run yet.

## Resource observations (unverified)

`suite` and `check` now include visible CPU quotas, process affinity, visible memory bounds, swap, PSI and short-sample CPU steal. Numeric results are preserved separately from terminal language. The default 0.2-second passive observation does not benchmark the CPU or change cgroup settings. Missing data remains unknown. Visible limits do not establish dedicated capacity; namespace/host scope and long-term contention require separate verification. New tests have not been run.

Basic security now inspects fixed-path ownership/mode metadata and optional local update-cache age/counts. Password-file contents are not read. Review findings manually; cached counts do not establish patch status. Untested.

## Local report export and IP overview

Use `proxydoctor report --input report.json --output report.md` to export a local snapshot; `proxydoctor recover --journal report.json.events.jsonl --output recovered.json` recovers the last complete record. Add `--format markdown --lang en` for English Markdown recovery. Files are never overwritten. Inspect exports before sharing.

`proxydoctor ipquality --mail-probes` opts into bounded PTR/forward consistency and one outbound TCP/25 target without sending mail. The overview panel precedes provider evidence. DNSBL and IP maps are not yet integrated; see IPQUALITY_COVERAGE.md. Final code passed 239 tests on each Ubuntu VM.
