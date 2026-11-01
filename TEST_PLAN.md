## 1.0 公测待验收

当前包的 Ubuntu 安装、ICMP/TCP、三网有效下载、BGP 实网及海外三城回程均留待下一轮；本轮开发机 271 通过、1 跳过。旧 Alpha 验证仅为历史。具体步骤范围见 PUBLIC_BETA_CHANGE_REPORT.md。


## v0.1.0-alpha 候选（2026-11-01）

隔离离线安装、完整性拒绝、网络worker超时/取消、统一结果schema、独立模块增量保存、路由重复探测统计已实现；两版Ubuntu各248自动测试/23实际验收。全新OS镜像尚缺，建议内部试用、暂缓公开。详情见ALPHA_RELEASE_REPORT.md。无主分支合并。


## 报告与IP质量更新（2026-11-01）

- 新增离线 `report` 命令：JSON→中英文Markdown，保留指标、来源、未知和跳过原因；输出独占创建，HTML/Markdown注入内容转义。
- 新增 `recover` 命令：恢复日志最后完整快照→JSON/Markdown；未完成运行标为recovered_partial，明确不是新检测。输入有读取预算。
- 分享副本增加敏感键、Bearer凭证、URL用户信息/查询参数脱敏；仍需人工复核，不保证任意文本完全匿名。
- 新增IP概览面板，CJK对齐与长行换行；多来源类型/代理/VPN/Tor证据放在下面，不合成纯净度评分。
- 新增可选 `--mail-probes`：PTR/正向一致性、单目标出站TCP25，默认不启用，不发送邮件。DNSBL明确未查询；IPMap尚未接入。
- 实际阅读xykt/IPQuality源码与AGPL许可，只参考需求与组织，未复制实现，详见IPQUALITY_COVERAGE.md。
- 报告/恢复/PTR实网版本两版Ubuntu均237测试通过；最终面板加入后，两版完整离线回归均239测试通过（22：4.04秒；24：4.49秒）。报告导出、恢复JSON/Markdown、中英文离线真实CLI均退出0。IP数据不完整时退出1符合预期。
- 实网：22的单目标出站TCP25可连接，24未确认；两台PTR未取得有效结果，不能据此判断邮件信誉。无付费API、系统依赖安装或完整报告上传。

证据：工作区outputs/ReportIP22-*、ReportIP24-*（真实导出/探测），PanelFinal22-pytest.txt / PanelFinal24-pytest.txt（最终239测试）。此前223测试记录属于前版，不覆盖所有新增功能。


## 最新双机验收（2026-11-01）

同版代码已在Ubuntu22.04.5/Python3.10.12和Ubuntu24.04.3/Python3.12.3分别完成223项测试、17/17实际CLI验收。中文/英文离线、Ctrl+C保存、恢复和防覆盖通过；两台实网检测均完整执行但存在目标TCP/IPv6/媒体未确认项，不能说网络全部通过。22.04初次验收脚本内存预期错误，按VirtualBox独立配置修正后复测通过。完整范围及原始证据见工作区outputs/双虚拟机-当前版本验收报告.md。此前未测试段落属于编写时状态，最新以本节为准。测试通过不表示全部101项需求完成。


## Ubuntu 24.04 实测更新（2026-11-01）

当前分支在Ubuntu24.04.3/Python3.12.3完成223项测试、17/17实际CLI验收。
中英文离线、默认测速拦截、Ctrl+C保存和防覆盖通过；网络实测正常执行但结果incomplete。
DNS有结果，固定IPv4 TCP超时、IPv6不可达、TLS跳过；30跳路由未到达目标，媒体多数未知。
综合报告schema版本升为3。此前“尚未测试”的段落是编写时记录；最新验证以本节为准。
完整日志/范围见工作区outputs/Current24-验收报告.md。Ubuntu22新版、真实VPS及未实现项目仍待验收。

# 测试与验收计划

本轮按用户指示暂不运行测试，所有新修改标记“未验证”。历史 0.5.0 记录位于工作区 outputs，不能直接用于本分支验收。

| 批次 | 必须验证的行为 | 方法和环境 | 当前证据 |
|---|---|---|---|
| P0 默认安全 | suite 默认不调用 hashlib 基准/measure_bandwidth；离线零外网；bandwidth 无许可拒绝；许可后预算显示；所有第三方包装入口拒绝 | Mock 调用计数、CLI 子进程、中文/英文；普通用户 | 新源码，未运行 |
| P0 安全持久化 | 每模块异常继续下一模块；Ctrl+C 保留事件；权限不足/磁盘满/中断/符号链接/已有文件均不覆盖 | 临时目录与故障注入；已有 suite 回归适配 | 尚未实现 |
| P1 资源 | cgroup v1/v2 嵌套配额/无限/缺文件；Swap/PSI/steal 采样；购买规格与实测分离 | 固定 fixture + Ubuntu 22.04 Server/24.04 Desktop | 待开发和验证 |
| P1 网络 | 分 IPv4/IPv6，DNS 超时/拒绝/无记录，TCP/TLS/UDP 限时，NAT/多网卡，不将失败归因唯一 | Mock + 回环服务 + VM | 部分旧测试待复核 |
| P2 路由 | 1..64 跳、v4/v6、目标不回应、中间超时不算端到端丢包、ASN 冲突、方向标记 | 固定报文 fixture + VM + 获授权公网节点 | UDP 旧用例存在，新验收待补 |
| P2 IP/媒体 | 403/429/200登录/地区禁止/有效元数据/证据冲突；时间和来源；无密钥/错误密钥；不下载受保护内容 | 离线 fixture，必要时有限实网 | 旧用例存在；新规则不宣称验证 |
| P3 基准监测 | 磁盘限额与清理、无裸盘写、进程超时、24/48h 中断恢复和时区、流量预算 | 先 Mock 后专用 VM，真实 VPS 须另授权 | 尚未实现 |
| P3 发布集成 | 干净 venv 安装/更新/卸载/离线、Schema 兼容、Python API 不依赖 CLI 文本、许可清单 | Ubuntu 双版本和 CI；ARM/真实 VPS 独立记录 | 待验证 |

每次执行记录 commit、日期、Python/OS/架构、命令、退出码、通过/失败/跳过数、脱敏日志和限制。未知不能算通过；缺海外 VPS 或 API 条件记为待实机验证。无生产测试、无付费 API、无完整报告上传、无系统依赖安装。旧测试如果断言自动测速，应改为显式传 allow_bandwidth=True，再新增默认不测速的独立断言。


## Reliability batch — 2026-11-01 (implemented, untested)

`suite` now creates a local redacted JSON report and sibling `.events.jsonl` recovery journal. Without `--json-output`, files are placed under `./reports/` with unique names. Detection does not modify system configuration, but does write these local output files. Linux file creation requests mode 0600; Windows uses inherited ACLs.

Each module start/completion and completed DNS/TCP result, route hop, and media service writes a flushed/fsynced snapshot. Module exceptions use `MODULE_ERROR` without storing raw exception text; other modules continue. `success` in `modules` means the module executed, not that a service is unlocked or a server is safe. Overall partial measurement remains incomplete. Ctrl+C records cancellation and returns 130. Previously completed journal records remain useful after a crash; use the Python `proxydoctor.reports.recover_latest(path)` API to read the latest complete snapshot.

Existing final/journal files and dangling final symlinks are rejected. Storage errors during checks produce a terminal warning, keep prior records, and return a nonzero result. The final JSON is exclusively created; a failed final write can leave a partial final file, so recover from the journal. No absolute durability guarantee applies to disk/controller failure. Storage paths must be in user-controlled directories; parent-directory symlink attacks are outside this first implementation.

Limits: module-level isolation does not isolate every individual local system check. Bandwidth and IP collection currently checkpoint on module completion; interruption can lose the current module's unfinished results. Media cancellation may wait for in-flight bounded network calls when the thread pool exits. SIGKILL/power loss cannot trigger cleanup; the journal contains only the last complete checkpoint. Standalone commands retain their existing save behavior. These changes and the new fault-injection tests have not been run yet.


## 资源检测第三组（2026-11-01：已编写，未测试）

- 新增 `proxydoctor/resources.py`，提供独立 `collect()` Python API 和数值渲染。接入综合检测的独立 resources 模块及 `check` 的 JSON/终端输出。
- 读取 `/proc/self/cgroup` 和 mountinfo，映射 cgroup v1/v2 挂载与成员路径，取最多 64 级可见父级中的最严格 CPU/内存配额；结合 sched_getaffinity 和逻辑 CPU 数计算可见 CPU 上限。
- 输出内存可见上限、Swap 总量/使用量、cgroup 当前内存使用及 CPU/内存/IO PSI。保留数字和单位，不解析中文描述；缺失或格式不合法保持未知。
- 对 `/proc/stat` 进行默认 0.2 秒被动采样，计算 steal 的计数差值比例。排除重复包含在 user/nice 中的 guest 字段；计数回退、缺失或无增量保持未知。
- 新增 `tests/test_resources.py` 的七个 fixture 场景：v2 父级限制、v1、子树挂载、缺失/非法数据、steal 差值、被动采样和非 Linux 降级。均未执行。

限制：namespace 隐藏的父级无法确认；混合层级/特殊挂载仍待实机验证。cgroup 当前内存用量与最严格父级上限可能属于不同层级，不可相减充当可用内存。meminfo、PSI、steal 可能反映宿主视图；不代表容器专属指标或长期超售证据。配额为可见上限，不证明独享、保证容量或购买规格。短采样不是 CPU 性能基准，颜色表示数据是否可读，暂不判断压力高低。

尚未实现：虚拟化类型细化、CPU 频率与购买规格对比、可授权 CPU/磁盘基准。没有运行测试或 VM 实测，不更新为“已实现且通过测试”。

实现语义参考 Linux 内核官方文档：

- [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)（层级限制、cpu.max、memory.max）
- [PSI](https://docs.kernel.org/accounting/psi.html)（avg10/60/300 百分比和 total 微秒）
- [/proc](https://docs.kernel.org/filesystems/proc.html)（CPU 计数与内存字段）

下次验收需先运行新增测试和现有回归，再分别在 Ubuntu 22.04 Server、24.04 Desktop 验证宿主/cgroup/权限视图；真实 VPS 未具备，不以 VM 代替。


## 双栈网络第四组（2026-11-01，已编写但未测试）

新增 `connectivity.py`，接入 `suite` 和 `quality`；旧 quality.py API 保留但不再是这两个 CLI 入口的主检测。每协议族默认2次独立系统解析（每次2秒子进程时限），4个固定数字IP端点执行 TCP→证书验证TLS（每目标4秒网络预算）。DNS时间包含进程启动、系统缓存与解析，不能作为纯DNS服务器延迟；成功率仅为本次小样本。

分离DNS/TCP/TLS结果，TCP成功且TLS失败时保留两者；错误不含原始异常、URL凭证。固定端点不代表全互联网或中国运营商，TLS不验证HTTP业务可用性。仅观察出站；未测UDP/PMTU/入站/云安全组。没有真实网络执行；网络时限不等于进程所有本地调度/证书加载时间的绝对总上限。

增加 `tests/test_connectivity.py` 六个场景：DNS无地址/超时、协议族错误、证书失败保留TCP成功、分族样本统计、探针错误隔离、Ctrl+C透传。尚未执行。


## 基础安全第五组（2026-11-01：实现未测试）

新增 `proxydoctor/security.py`：独立 Python collect/render API，接入 suite 独立安全模块和 check 的结构化/双语终端输出。检查固定9个文件/目录的 lstat 权限、所有者和类型，不读取 shadow/gshadow 内容、不提权、不刷新包缓存、不执行任何修复。检测世界可写、同组可写、非root所有者、敏感文件世界可读，均为人工审阅提示而非漏洞确认；shadow 的同组只读本身不报风险。符号链接不跟随判断，结果未知。

更新状态只读取 apt 成功时间戳和可选 update-notifier 缓存的明确英文计数。记录缓存年龄；无缓存/无权限/本地化或不识别格式不解释为零更新。未调用 apt update/upgrade，不联网、不查询付费API。即使缓存为0也不能证明无漏洞或已完整修补。仅固定入口/父目录，不递归审计 sudoers.d/sshd_config.d；ACL、capabilities、运行态、ESM/订阅资格和完整包版本安全比对未实现。

新增 `tests/test_security.py` 九个离线场景（含权限、符号链接、错误不泄密、缓存缺失/年龄/本地化、禁止读取私密内容和非Linux降级），本轮没有执行测试。此前与本轮全部新增实现仍待回归和双Ubuntu实测。
