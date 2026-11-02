# References and acknowledgements / 借鉴来源与致谢

VPSMaster更名后保留历史版权与引用；API/数据条款及保留边界见 [docs/DATA_SERVICES.md](docs/guide/DATA_SERVICES.md)。本项目MIT不授予第三方数据的任意再分发权。

VPSMaster's default Python checks are independently implemented. The projects
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
# Additional design reference — 2026-11-01

xykt/IPQuality: https://github.com/xykt/IPQuality . Its root LICENSE contains
GNU AGPL v3. We reviewed ip.sh and its mail/DNSBL entry points for functional
coverage and report organization. No implementation, DNSBL list or scraped
provider data from that project is bundled. Our PTR/SMTP probes and overview
renderer are independently written. Provider APIs and any future datasets or
maps require their own terms and licensing review.

## 1.0 公测新增参考与数据服务（2026-11-01）

- NextTrace / NTrace-core：https://github.com/nxtrace/NTrace-core ，GPL-3.0；仅参考公开三城运营商测试目标域名的事实和用途，没有复制其 Go 实现、打包二进制或调用其定位鉴权服务。目标参考：https://github.com/nxtrace/NTrace-core/blob/main/fast_trace/basic.go 。
- CleanIP sh.cd：https://github.com/CleanIP/sh.cd ，MIT，Copyright (c) 2026 CleanIP；参考少量公开测速端点信息和节点失败需诚实展示的设计，没有复制其 shell 执行/上传流程。目录标签不能证明当前运营商、物理位置或服务授权；代码开源不等于测速服务永远开放。
- VPSDance/vkit：https://github.com/VPSDance/vkit/blob/main/speedtest.sh ，仅作为寻找公开候选端点的研究线索；未复制脚本、打包或执行。未确认许可的代码不作为本项目实现依赖。
- RIPEstat Data API：https://stat.ripe.net/docs/data-api/ripestat-data-api ，查询 network-info、asn-neighbours、bgp-state。使用 HTTPS，逐次查询、有限响应/超时，不下载整个 BGP 表。结果记录 RIPE RIS 采集器视角，按服务条款和限额使用。
- 系统 traceroute 是用户系统已有的可选工具。本包不分发、不自动安装，不使用 shell、不自动提权。UDP 模式保持自主标准库实现。
- 固定测速端点只发送测试载荷，没有订阅、账号或 API 密钥。HTTPS 下载不禁用证书校验、不自动降级 HTTP；小流量明文协议探测单独标明范围。

CleanIP 参考数据的许可证声明：

MIT License

Copyright (c) 2026 CleanIP

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Documentation presentation reference

[xykt/HardwareQuality](https://github.com/xykt/HardwareQuality) informed the concise README structure and terminal-first presentation. No source, artwork or README text copied; this is a design reference, not a bundled dependency.
