> 历史记录 / Historical record：ProxyDoctor 是项目旧名。以下旧版本、SHA256、测试数量与路径保留原样，不代表 VPSMaster 新构建已通过；当前范围见 README.md、CURRENT_STATUS.md 和新包同 SHA256 验收报告。

最新逐类完成情况和未完成重点见 [当前进度](CURRENT_STATUS.md)。新增双栈 DNS/TCP/TLS 已接入 suite/quality，尚未验证。

# 当前开发范围（2026-11-01）

资源首页优先显示本进程 CPU 上限、可见内存限额及其依据。已识别的容器如果没有可读限额，不以宿主机总内存充当自己的额度。系统原始值保留在 JSON 详细依据中；CPU/内存是否独享统一标注“无法从本机确认”。容器识别仍有遗漏可能，KVM 中的系统可见内存也不等于已验证商家独享保障。此轮显示调整未测试。

本分支按新的 [开发任务书](DEVELOPMENT_BRIEF.zh.md) 推进独立 Python VPS 综合诊断 CLI。代理部署、Web UI 不在当前范围。下面原 0.5.0 说明保留作背景；最新实际状态以 [问题追踪](PROBLEM_BACKLOG.md)、[架构](ARCHITECTURE.md)、[源码研究](OPEN_SOURCE_RESEARCH.md)、[测试计划](TEST_PLAN.md) 和 [更新记录](CHANGELOG.md) 为准。

常规 `bash proxydoctor.sh` / `proxydoctor suite` 默认跳过 CPU 和带宽基准。需要测速时，使用 `proxydoctor bandwidth --allow-bandwidth` 或 `proxydoctor suite --allow-bandwidth`；执行前显示请求载荷预算，协议开销与其他模块流量另计。`proxydoctor suite --offline` 跳过联网。第三方脚本/可执行文件包装入口暂时禁用。

本分支修改尚未运行测试，不继承旧版测试通过结论，也尚未发布。

---

# ProxyDoctor

[中文](README.md) | [English](README.en.md)

面向 Ubuntu VPS 新手的原生 Python 只读诊断工具。支持 Ubuntu 22.04 及更新版本；
当前优先验收 22.04、24.04，其他版本逐步实测。Python 3.10+，没有第三方运行依赖。
本阶段不安装 sing-box，不修改 SSH/防火墙，不自动提权，不下载执行远程脚本。

## 快速运行

下载源码包并解压，进入项目目录：

```bash
bash proxydoctor.sh
bash proxydoctor.sh suite --lang en
bash proxydoctor.sh suite --offline
```

下载或克隆本身不执行程序。默认入口 `suite` 会联网、逐项回显；
`check` 默认只读取本机信息。普通用户可运行，权限不足显示未知；程序不调用 sudo。

```bash
python3 -m proxydoctor check
python3 -m proxydoctor check --port 8388 --json --output check.json
python3 -m proxydoctor suite --json-output suite.json --color always
```

报告文件不会覆盖已有文件，也不会自动创建目录。原生报告仅保存在本地，IP 默认脱敏；
脱敏不是匿名保证，分享前仍应检查。`--show-ip` 可在终端显示出口地址，文件仍脱敏。
路由模块按用户要求在终端显示实际节点 IP，导出文件中隐藏。

## 四模块

| 模块 | 直接回显 | 边界 |
| --- | --- | --- |
| VPS 资源与体检 | 系统、架构、CPU、逻辑核心、内核、内存、磁盘、SHA-256 样本；DNS 配置、端口、SSH 保护、SSH 设置和防火墙提示 | 系统可见资源不保证等于商家配额；SHA-256 不是完整 CPU 基准；本机读取不能确认云防火墙放行 |
| 节点网络/IP 质量 | 实际 DNS、TCP 请求，IP 归属/ASN/地区/类型、风险标记、来源状态、覆盖率和分歧 | DNS 返回 IPv6 不代表 IPv6 连通；第三方标记不是客观安全保证，不合并不同评分 |
| 路由 | 原生 Linux IPv4/IPv6 UDP 追踪，默认 30 跳，可至 64；每行 IP、延迟、估计位置 | 中间节点可能不回包，位置是数据库估计，不保证真实物理位置；NAT/过滤可能导致未到达 |
| 流媒体 | Netflix、Disney+、YouTube Premium、Spotify、Prime Video、Max、Apple TV+、Hulu、BBC iPlayer、Paramount+ | 明确地区提示/套餐证据重复确认；片库和元数据不等于账号/DRM 实际播放；规则失效和网络失败显示未知 |

JSON 综合报告 schema_version=2，同时包含本机检查、DNS/TCP、每个测速来源、IP 来源观察、路由逐跳及媒体探测依据。
绿色表示取得结果或局部通过，红色表示已知风险/限制/冲突，黄色表示未知、跳过或证据不足。
支持 `--color auto|always|never` 和 `NO_COLOR`。复杂配置的完整依据可用 `check --json` 查看。
`sshd -T` 读取默认配置，不保证与运行中实例或 Match 条件相同。安装与修复阶段仍须独立保护 SSH。

## 多来源测速

```bash
bash proxydoctor.sh bandwidth
bash proxydoctor.sh bandwidth --source ovh-rbx --rounds 3 --sample-mib 4
bash proxydoctor.sh bandwidth --source hetzner-fsn --sample-mib 1
bash proxydoctor.sh suite --bandwidth-source cloudflare
```

| 来源参数 | 节点标签 | 下载 | 上传 | 默认 |
| --- | --- | --- | --- | --- |
| cloudflare | Cloudflare / Anycast | 是 | 是 | 是 |
| ovh-rbx | OVHcloud / 法国 Roubaix | 是 | 不支持 | 是 |
| hetzner-fsn | Hetzner / 德国 Falkenstein | 是 | 不支持 | 否，当前网络较慢 |

每方向 128 KiB 预热不计统计；正式 3–8 轮、每轮 1–20 MiB。默认请求测速载荷
最多 36.375 MiB，不含协议开销及其他模块请求。各来源独立给出中位数、范围、成功数；
不做跨来源平均。样本短于 1 秒、轮次不足或波动大显示黄色。吞吐包含建连，不能核验商家标称带宽。
对大文件只接受精确 HTTP 206 分段响应；若服务器忽略 Range，不读取整文件正文，不回退完整下载。
测速超过时限或未完成不记为成功；不支持上传不记为上传失败。带宽子报告 schema_version=2。

## IP 数据与密钥

```bash
bash proxydoctor.sh ipquality --show-ip --json-output ip.json
bash proxydoctor.sh ipquality --no-enrichment
bash proxydoctor.sh suite --no-ip-enrichment
```

默认查询 ipapi.is、proxycheck.io 和 IP2Location。若 ipapi.is 连接失败，尝试 ipify 获取出口 IP。
后续查询固定为该地址，拒绝把其他地址的响应混入结果。所有这些服务会看到请求来源，
另外两家会收到查询的出口地址。可用 `--no-ip-enrichment` 关闭额外来源，`--offline` 关闭综合入口联网。

17 项核心字段包括运营商/ASN、地区/时区、网络类型、网段滥用比例，以及数据中心、代理、VPN、
Tor、近期滥用、移动、卫星、Anycast、保留地址标记。按来源记录观察和字段来源；布尔标记冲突显示
“来源不一致”，不会自动选成安全。IP2Location 免费模式的有限代理标记单独保留，不替代通用 VPN 判断。
proxycheck.io 风险/置信度与 AbuseIPDB 评分分别保存，不求平均，不把网段比例当作单 IP 恶意概率。

免密钥 API 也有配额：proxycheck.io 当前限 100 次/天，IP2Location 当前限 1000 次/天；以服务官方规则为准。
遇到限流不自动重试。ipapi.is 匿名响应只提供基础数据；扩展字段和 AbuseIPDB 举报数据可通过密钥补充。
不要把密钥发到聊天、提交到仓库或放进命令参数；在 VPS 本地无回显输入：

```bash
read -rsp 'ipapi.is API Key: ' PROXYDOCTOR_IPAPI_KEY
export PROXYDOCTOR_IPAPI_KEY
printf '\n'
read -rsp 'AbuseIPDB API Key: ' PROXYDOCTOR_ABUSEIPDB_KEY
export PROXYDOCTOR_ABUSEIPDB_KEY
printf '\n'
bash proxydoctor.sh ipquality
```

ipapi.is 密钥放 HTTPS POST 正文，AbuseIPDB 放请求头，不写入 URL 或报告。
缺少字段和密钥明确显示未知；完整覆盖率只针对定义的核心字段，不代表所有数据库或安全认证。
零举报不代表干净 IP。只确认本次接口请求的出口和地址族，不保证每个服务连接都使用同一出口。

## 路由与媒体复测

```bash
bash proxydoctor.sh suite --route-target 1.1.1.1 --max-hops 64
bash proxydoctor.sh suite --route-target 2606:4700:4700::1111 --no-geo
bash proxydoctor.sh media --color always --json-output media.json
```

路由位置来自 ipwho.is，按运行缓存；私网/保留节点不查询。`--no-geo` 关闭位置查询。
媒体重复确认地区提示/带价格的具体套餐；Netflix 检查结构化片库元数据，BBC 额外查询测试频道的公开媒体元数据。
不获取付费节目、不下载流媒体、不绕过登录/DRM，不保留媒体签名地址。BBC 的测试频道结果不代表整个平台。
HTTP 200、403、页面可达、套餐或片库可见均不作为“完全解锁”证据。

## 退出码

- `check`：0=无已知注意/失败项，仍可能含未知；1=有注意/失败项；2=参数/保存错误。
- `suite/bandwidth/ipquality/media`：0=该命令定义的范围完整，离线 0 仅表示本地执行完成；1=有未完成/未知/波动或未验证播放；2=参数/保存错误。
- 流媒体命令仍保留“账号播放未测”，因此返回 1；这不表示程序崩溃。
- Ctrl+C 返回 130，不改系统设置。

## 安装与开发

源码可直接运行。也可把提供的 wheel 安装到自己的虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install /path/to/proxydoctor-0.5.0-py3-none-any.whl
.venv/bin/proxydoctor suite --offline
```

Ubuntu 若未安装 venv 支持，需另行安装系统对应组件；程序不会自动安装。
开发测试：`python -m pip install pytest` 后 `python -m pytest -q`。
GitHub Actions 配置已提供，未发布仓库前不宣称远程 CI 已运行。
贡献规范见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全反馈见 [SECURITY.md](SECURITY.md)。

## 阶段一验收与后续

本轮按用户选择完成代码和 22.04/24.04 虚拟机验收；实际记录以交付验收报告为准。
海外 VPS、真实付费账号播放、带真实密钥的扩展数据，以及 Ubuntu 其他版本仍待分别验收；不会把它们标为已通过。
之后阶段才实现 sing-box 安装、Karing 协议连通、修复预览/备份/回滚、Web UI 和安全订阅传输。
不对外开放明文 HTTP 订阅，不根据只读体检自动修改 SSH/防火墙。

## 开源与来源

原创代码使用 MIT 许可证。感谢 ECS、NodeQuality、NetQuality/IPQuality、NextTrace、RegionRestrictionCheck 的功能和展示设计参考；
默认实现没有打包或复制上游脚本/数据库。来源和许可范围见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
本地第三方适配器仅在显式指定时运行，第三方行为/输出不保证只读或脱敏。

数据接口：[Cloudflare](https://github.com/cloudflare/speedtest)、[OVHcloud](https://proof.ovh.net/)、
[Hetzner](https://docs.hetzner.com/storage/object-storage/troubleshooting/bandwidth-latency-issues/)、
[ipapi.is](https://ipapi.is/developers.html)、[proxycheck.io](https://proxycheck.io/api/)、
[IP2Location](https://www.ip2location.io/ip2location-documentation)、[AbuseIPDB](https://docs.abuseipdb.com/)、
[ipwho.is](https://ipwhois.io/documentation)、[ipify](https://www.ipify.org/)。
[Netflix 官方 VPN 说明](https://help.netflix.com/en/node/114701) 也说明了目录限制，不保证页面可达就能播放。

## 增量保存与故障隔离（实现未测试）

综合检测默认在当前目录的 `reports/` 保存脱敏 JSON 和 `.events.jsonl` 恢复日志，也可用 `--json-output` 指定文件。常规体检不修改系统配置，但会写入这些本地报告。已存在的报告和日志不会覆盖。

各模块独立记录异常后继续；DNS/TCP、路由跳、媒体结果完成后及时保存。Ctrl+C 会尝试保存并返回 130。磁盘写入失败会提示并继续终端检测；恢复时以日志中最后完整的记录为准。模块 success 只表示执行完成，不代表服务解锁或服务器安全。

本轮新增故障注入测试但未执行。测速/IP 查询尚不能保存模块内部所有未完成样本；媒体取消可能等待正在进行的请求结束；强制终止只能恢复最后一次完整记录。详见 TEST_PLAN.md。

## 资源检测新功能（未验证）

`suite` 和 `check` 增加 CPU 可见配额、进程 CPU 范围、内存可见上限、Swap、PSI 压力和短采样 CPU steal。结果直接显示在终端，并保留结构化数值。默认被动观察约 0.2 秒，不跑基准、不写 cgroup 设置。

缺失数据标为未知；可见配额不等于独享资源，短采样不代表长期状况。完整限制和后续验收见 TEST_PLAN.md。

基础安全新增重要路径权限/所有者与更新缓存年龄/计数，只读且不读取密码文件内容。风险提示需人工审阅，缓存不证明完整修补；未测试。


## IP概览、Markdown和恢复命令

```bash
# 终端集中显示IP信息；额外邮件探测为可选，不发送邮件
bash proxydoctor.sh ipquality --mail-probes --show-ip
# 从已有JSON导出，不重新检测
bash proxydoctor.sh report --input reports/example.json --output report.md
# 恢复最后完整记录，输出文件须不存在
bash proxydoctor.sh recover --journal reports/example.json.events.jsonl --output recovered.json
bash proxydoctor.sh recover --journal reports/example.json.events.jsonl --output recovered.md --format markdown --lang en
```

`--show-ip`只改变终端IP显示，文件仍脱敏。顶部是概览，详细数据源在下面。DNSBL与IPMap尚未接入，覆盖和限制见 [IP质量功能表](IPQUALITY_COVERAGE.md)。不要将来源评分或PTR/端口结果视为绝对安全/邮件可投递证明。
