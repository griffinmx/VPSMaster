
## v0.1.0-alpha 候选（2026-11-01）

隔离离线安装、完整性拒绝、网络worker超时/取消、统一结果schema、独立模块增量保存、路由重复探测统计已实现；两版Ubuntu各248自动测试/23实际验收。全新OS镜像尚缺，建议内部试用、暂缓公开。详情见ALPHA_RELEASE_REPORT.md。无主分支合并。

# Current branch safety changes — 2026-11-01

Routine suites skip CPU and bandwidth benchmarks. Bandwidth requires explicit per-call consent via `--allow-bandwidth` / `allow_bandwidth=True`; payload limits are not a total network billing cap. External executable/script wrappers are disabled pending resource, license and upload review. Online native checks still disclose the request source to their target services; offline mode skips them.

The updated workflow is not yet tested. Fault isolation and incremental report saving are implemented but untested. Current scope excludes proxy deployment and Web UI. No full-report uploads, paid API use, system dependency installation, production VPS tests, main-branch merges or public releases are authorized by this development brief.

---

# Security / 安全反馈

Do not post vulnerabilities containing passwords, subscription URLs, API keys,
SSH keys or full diagnostic reports to public issues. If this repository is
published with GitHub private vulnerability reporting enabled, use that channel.
Otherwise request a private contact without publishing exploit details or secrets.
This source snapshot does not yet have a public repository or security mailbox.

Rotate any exposed credential at its provider. Report files hide IP addresses by
default, but redaction does not guarantee removal of all identifying information.
Review files before sharing. Native diagnostics do not upload reports or modify
SSH/firewall settings. The default suite contacts external test/data/media
services, which see the request source. `check` and `suite --offline` do not.
Keys are accepted through local environment variables; the product never asks
for them on a public web form. Future deployment/repair features require a
separate review and SSH rollback safeguards.

中文：不要公开提交密码、密钥、订阅地址或完整诊断报告。仓库发布并开启私密漏洞报告后
优先使用该渠道；未配置前先询问私密联系方式，不公开敏感细节。报告脱敏不是匿名保证，
分享前需检查。当前原生检测不修改 SSH/防火墙，不上传报告；联网模式的服务会看到请求来源。


## 基础安全第五组（2026-11-01：实现未测试）

新增 `proxydoctor/security.py`：独立 Python collect/render API，接入 suite 独立安全模块和 check 的结构化/双语终端输出。检查固定9个文件/目录的 lstat 权限、所有者和类型，不读取 shadow/gshadow 内容、不提权、不刷新包缓存、不执行任何修复。检测世界可写、同组可写、非root所有者、敏感文件世界可读，均为人工审阅提示而非漏洞确认；shadow 的同组只读本身不报风险。符号链接不跟随判断，结果未知。

更新状态只读取 apt 成功时间戳和可选 update-notifier 缓存的明确英文计数。记录缓存年龄；无缓存/无权限/本地化或不识别格式不解释为零更新。未调用 apt update/upgrade，不联网、不查询付费API。即使缓存为0也不能证明无漏洞或已完整修补。仅固定入口/父目录，不递归审计 sudoers.d/sshd_config.d；ACL、capabilities、运行态、ESM/订阅资格和完整包版本安全比对未实现。

新增 `tests/test_security.py` 九个离线场景（含权限、符号链接、错误不泄密、缓存缺失/年龄/本地化、禁止读取私密内容和非Linux降级），本轮没有执行测试。此前与本轮全部新增实现仍待回归和双Ubuntu实测。
