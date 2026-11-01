# Known limitations — 1.0 public Beta

- Targets: Ubuntu22.04+ / Python3.10+. Available labs: existing Ubuntu22 Desktop with
  fresh HOME, Ubuntu24 Server. No new Ubuntu22 Server, overseas VPS or ARM acceptance implied.
- Kernel text consoles default to English. Explicit Chinese needs suitable fonts.
- Missing commands, permissions, quotas, certificates or filtering can yield unknown/partial.
- One response per TTL is router-response evidence, not forwarding loss. IP geography
  is an estimate. ASN/operator can be unavailable; trace enrichment caps at 12 public lookups.
- No proof of dedicated hardware, complete reputation, mail deliverability, playback,
  full China routes, commercial BGP relationships or line capacity.
- China bandwidth candidates are optional, not a validated complete mainland set.
  Hong Kong never substitutes for mainland Mobile. No remote scripts execute.
- Default checks do not change SSH, firewall, DNS or routes. Installation creates a
  user venv; reports create local files; opt-in bandwidth sends bounded test payloads.
- Sharing redacts known patterns, not arbitrary text. Review exports; raw journals,
  inventories, credentials, snapshots and backups must remain private.
- The manifest detects file changes, not publisher authenticity. Verify the ZIP
  digest through a trusted independent channel before installation.
- Continuation files support manual restart of work, not automatic Codex scheduling.
