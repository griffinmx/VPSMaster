> 历史记录 / Historical record：ProxyDoctor 是项目旧名。以下旧版本、SHA256、测试数量与路径保留原样，不代表 VPSMaster 新构建已通过；当前范围见 README.md、CURRENT_STATUS.md 和新包同 SHA256 验收报告。

## 1.0.0b1 — 2026-11-01 公测候选，非最终版本

终端、语言和参数修复；流媒体改为可达性；新增可选 ICMP/TCP、三城三运营商追踪、BGP 和候选节点探测。完整大陆三网未验证。详见 PUBLIC_BETA_CHANGE_REPORT.md。


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

# Changelog

## Resource display correction — 2026-11-01 (untested)

Resource output now prioritizes process CPU bounds and visible cgroup memory
limits. Raw OS CPU/RAM observations remain detailed JSON evidence rather than
being presented as dedicated VPS capacity. Recognized containers without a
visible memory limit show unknown allocation instead of host MemTotal. Allocation
basis and unknown CPU/memory dedication are explicit. Container markers are
best-effort evidence, not complete virtualization detection. No local metric
certifies provider-side exclusive CPU or reserved memory. Added a container
fixture case; no tests executed.

## Unreleased — 2026-11-01

- 范围更新为独立 Python VPS CLI，不开发代理部署和 Web UI。
- 按任务书逐条登记 101 项需求，记录源码、验证方法及限制。
- 新增架构演进、五个参考项目入口源码/许可证研究和测试计划。
- 综合流程移除自动 SHA-256 基准，默认跳过带宽测试；CLI --allow-bandwidth / Python allow_bandwidth=True 显式许可才启用测速。
- 暂停 NodeQuality/BestTrace/RegionRestrictionCheck 包装入口，避免常规流程执行未经资源/上传审查的第三方程序。
- 保留现有 0.5.0 代码历史，在 engineering/safe-cli-core 分支修改。

验证状态：用户要求本轮可先不测试；未运行自动测试、虚拟机或实网测量。模块故障隔离、增量保存、统一结构化接口和其他 backlog 项尚未完成。版本号保持 0.5.0，未发布。


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
