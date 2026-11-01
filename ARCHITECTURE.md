
## v0.1.0-alpha 候选（2026-11-01）

隔离离线安装、完整性拒绝、网络worker超时/取消、统一结果schema、独立模块增量保存、路由重复探测统计已实现；两版Ubuntu各248自动测试/23实际验收。全新OS镜像尚缺，建议内部试用、暂缓公开。详情见ALPHA_RELEASE_REPORT.md。无主分支合并。

# 架构与接口演进

2026-11-01。当前范围是独立 Python CLI，未来 FlexMaster 通过 Python API 复用。以下区分现状与方案，方案尚未视为实现。

## 现状

- `checks.py`：Host 只读适配器、Result、inspect；返回 schema_version=1 字典。
- `suite.py`：四模块编排、终端渲染和 schema_version=2 报告，当前相互耦合。
- `routes.py`：Linux UDP 错误队列路由，emit 回调和 records 可供调用；非通用跨平台实现。
- `quality.py`、`media.py`、`ipquality.py`、`bandwidth.py`：可调用函数，但部分收集函数同时输出终端。
- `net.py`：有限响应、请求超时；`console.py`：颜色和控制字符过滤；`cli.py`：参数、脱敏和保存。
- 无运行依赖，Python >=3.10；setuptools>=77 是构建依赖，尚无上限锁定。

## 渐进方案（待实现）

保留文件和现有接口，先增加独立 core/models、core/runner、reports 组件，再逐模块适配。不要一次移动所有代码。

统一 EvidenceResult：schema_version、check_id、status、observed_at、method、source、metrics（数值+单位）、error_code、confidence、limitations。状态为 success/failure/skipped/unsupported/unknown。failure 表示检查失败，不等于确认存在漏洞。媒体业务状态保留独立字段，不把 catalog_visible 映射为播放成功。旧 pass/warn 不可机械映射为网络成功/失败。

Runner 接受显式配置和 provider 注入；每模块独立捕获预期错误，未知异常仅记录固定错误码，不保存异常原文中的凭证。KeyboardInterrupt 传给协调器，落盘已有结果再退出 130。同步阶段先使用明确请求预算；不可通过线程超时假装终止底层网络操作。

Reports 接收结构化对象，不解析 CLI 文本。增量 JSONL 保存完成事件，最终报告独占创建、默认脱敏；禁止覆盖已有文件或通过符号链接写入。持久化失败应保留可用终端结果并返回明确错误。历史比较只比较相同方法、单位、节点及采样参数；用户购买规格单独存为 user_claim，不能当实测。

## 安全配置

常规 suite 不跑 CPU 或磁盘基准；测速需 allow_bandwidth=True / CLI --allow-bandwidth。该标志仅授权当前调用，不是永久授权。当前预算沿用 bandwidth.payload_budget，属于 HTTP 载荷预算，不能宣称为链路计费硬上限。CPU/磁盘基准后续单独命令、确认和上限。常规联网仍会向目标及 API 暴露请求来源；--offline 跳过联网。

第三方可执行文件入口当前暂停；恢复前必须审查版本、许可、网络上传和资源消耗，不自动下载或提权。未来 FlexMaster 默认同样应用安全策略。暂不承诺稳定 API/Schema 兼容性；新格式须先有版本及迁移文档。


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
