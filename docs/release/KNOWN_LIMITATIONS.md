# VPSMaster Known Limitations — 1.0 public Beta

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
- Reports do not expire automatically. Third-party data retention/sharing terms
  remain applicable; see [data-service terms](../guide/DATA_SERVICES.md), including IP2Location cache limits.
- The manifest detects file changes, not publisher authenticity. Verify the ZIP
  digest through a trusted independent channel before installation.
- Media checks cover public-page reachability only, not unlock or paid playback.
- Mainland three-carrier speed testing is experimental and disabled by default.
- Public IPv6 and complete public ICMP/TCP routes are not comprehensively accepted.
- Beta is not production stability or an independent security certification.
- No Web UI, automatic proxy deployment or full management panel is provided.
- Bandwidth `attempted` counts scheduled sample slots, including automatically
  skipped slots; it is not an actual network-request counter. Inspect sample errors.

当前不具备一键安全加固或自动修复。未来遵循检测→解释→预览→确认→备份→执行→验证→回滚；回滚不能覆盖所有断网/重启/云安全组/宿主机故障。本轮只更新路线与私有发布准备。
