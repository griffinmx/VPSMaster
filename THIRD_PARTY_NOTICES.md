# References and acknowledgements / 借鉴来源与致谢

ProxyDoctor's default Python checks are independently implemented. The projects
below informed the feature selection and terminal presentation. Their code is
not bundled in this source release. Attribution does not replace license compliance:
any future source reuse must retain the upstream notices and follow its license.

当前默认检测由本项目独立实现。以下项目用于功能调研、输出设计参考；未将其脚本源码
复制进本发布包。致谢不能替代许可证合规；后续实际复用源码时必须保留版权声明、记录修改，
并按相应许可证处理。

| Source / 来源 | Reference scope / 参考范围 | License note / 许可说明 |
| --- | --- | --- |
| [spiritLHLS/ecs](https://github.com/spiritLHLS/ecs) and [oneclickvirt/ecs](https://github.com/oneclickvirt/ecs) | 综合 VPS 检测的模块组织与直接终端回显 / benchmark workflow | See upstream LICENSE; no source bundled |
| [LloydAsp/NodeQuality](https://github.com/LloydAsp/NodeQuality) | 多种节点检测统一展示 / unified node tests | AGPL-3.0; optional local-script adapter only |
| [xykt/NetQuality](https://github.com/xykt/NetQuality) | 紧凑网络结果、分区布局 / compact network presentation | AGPL-3.0; no source bundled |
| [xykt/IPQuality](https://github.com/xykt/IPQuality) | IP 归属与风险字段分类 / IP field categories | AGPL-3.0; no source bundled |
| [nxtrace/NTrace-core](https://github.com/nxtrace/NTrace-core) | IP、延迟和位置的路由显示形式 / route output format | See upstream LICENSE; no code or database bundled |
| [lmc999/RegionRestrictionCheck](https://github.com/lmc999/RegionRestrictionCheck) | 流媒体服务清单、区域限制场景调研 / media test coverage research | AGPL-3.0; optional local-script adapter only |
| [IPIP BestTrace](https://www.ipip.net/product/client.html) | 路由追踪产品功能参考 / route tracing reference | Third-party software; binary/database not redistributed |

## Runtime data / 运行时数据来源

- [Cloudflare Speedtest](https://github.com/cloudflare/speedtest): HTTPS upload/download endpoints. Our repeated, bounded measurement implementation is independent.
- [Hetzner official test files](https://docs.hetzner.com/storage/object-storage/troubleshooting/bandwidth-latency-issues/): Falkenstein HTTPS download samples using validated Range requests; no full test file redistributed.
- [OVHcloud Network Speedtest](https://proof.ovh.net/): Roubaix HTTPS download samples using validated Range requests; download-only in our adapter.
- [ipapi.is](https://ipapi.is/developers.html): IP ownership/ASN metadata; optional fields depend on provider access and limits.
- [proxycheck.io](https://proxycheck.io/api/): keyless v3 network/proxy/VPN/Tor/hosting observations and provider-specific risk/confidence; fixed June 24, 2026 schema, tag=0. Results are not a safety guarantee.
- [IP2Location.io](https://www.ip2location.io/ip2location-documentation): keyless IP metadata and limited proxy observation; API/data terms remain with the provider, no database bundled.
- [AbuseIPDB](https://docs.abuseipdb.com/): optional key-authenticated read-only IP reputation check, 90-day window. Keys stay in HTTPS headers; no reports are submitted.
- [ipwho.is](https://ipwhois.io/documentation): route IP geolocation estimates, cached within a run. Private/reserved IPs are not queried.
- [ipify](https://www.ipify.org/): explicit optional egress IP lookup for the check command.
- Netflix, Disney+, YouTube, Spotify, Amazon Prime Video, Max, Apple TV+, Hulu, BBC iPlayer and Paramount+: service pages and BBC public test-channel metadata queried by native media rules. Results are not account-level playback tests.

No affiliation or endorsement by these projects or providers is claimed.
API availability, accuracy and terms are controlled by each provider. IP location
is an estimate, not verified physical hardware location.

Last reviewed / 最后核对：2026-10-31.
