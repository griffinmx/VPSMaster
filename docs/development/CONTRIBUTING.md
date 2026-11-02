# Contributing to VPSMaster / 参与贡献

公开仓库建立后请使用顶部 Issues → New issue；Bug/功能模板在 .github/ISSUE_TEMPLATE/。
Roadmap 标记 Planned 的能力不能在贡献说明中写为已实现；更名仍保留 proxydoctor 包/命令兼容。

Python 3.10+; runtime uses the standard library only.

```console
python -m venv .venv
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
```

Windows: use `.venv/Scripts/python.exe` instead.

Diagnostics must remain read-only: no automatic sudo, package installation,
firewall/SSH/network changes, or fetching/executing remote scripts. Explicit
local third-party adapters must remain opt-in and disclose their behavior.
Use fixed HTTPS endpoints, bounded requests, identity validation and no automatic
quota retries. Never report missing data as a safe flag or HTTP 200 as playback.
Keep source disagreement and scores separate. Do not commit tokens, reports,
VM connection information or private keys.

New rules need evidence-based fixtures for positive, restricted and unknown
cases where applicable. Tests must not query live services. Validate Ubuntu
22.04 and 24.04 changes in disposable test environments before release; record
test parameters and distinguish code failures from external service results.

中文：保持检测只读；不自动提权、安装组件或修改 SSH/防火墙。联网请求必须有边界，
未知不能视为安全，页面可达不能视为播放解锁。新增规则注明来源、语义和限制，
用模拟数据测试；禁止把真实凭证、VM 信息及未脱敏报告提交到仓库。
