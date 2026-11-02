# References and licensing

The independently implemented stdlib runtime has no third-party Python dependency.
No new third-party code, database or binary was copied during final hardening.
Full references and retained MIT notices: [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

Reviewed 2026-11-01:

- https://github.com/spiritLHLS/ecs — module/workflow reference, MIT; no copied code.
- https://github.com/oneclickvirt/ecs — workflow reference; no copied code.
- https://github.com/nxtrace/NTrace-core/blob/main/fast_trace/basic.go — public trace
  target names. GPL-3.0: https://github.com/nxtrace/NTrace-core/blob/main/LICENSE .
  No implementation/database bundled. Names alone do not authorize arbitrary traffic.
- https://github.com/CleanIP/sh.cd — catalogue reference; upstream MIT notices retained.
  Availability, carrier identity and service terms require independent validation.
- https://stat.ripe.net/docs/data-api/ripestat-data-api — read-only BGP observations.
- https://ipwhois.io/documentation — optional route geography/ASN/operator estimates.

NodeQuality, IPQuality, NetQuality, RegionRestrictionCheck and BestTrace inform product
coverage; implementations/binaries are not bundled. Acknowledgement does not grant
permission to copy. Future reuse needs a new license review. API and public test
service terms/limits apply independently of source-code licenses.
