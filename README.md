# VPSMaster

**看清你的 VPS，让服务器管理更安全。**

VPS Diagnostics & Security Toolkit — 面向 VPS 新手和 Linux 用户的开源检测与安全管理工具。

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue) ![Linux](https://img.shields.io/badge/Platform-Linux-lightgrey) [![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE) ![Beta.1](https://img.shields.io/badge/Status-Beta.1-orange)

[English](README.en.md) · [使用文档](docs/guide/USAGE.md) · [反馈问题](https://github.com/griffinmx/VPSMaster/issues)

## 项目简介

VPSMaster 基于 Python，帮助用户快速了解 Linux VPS 的硬件资源、网络质量、IP 信息及基础安全风险。

当前 **v1.0.0-beta.1** 主要提供 CLI 综合检测与本地报告。普通检测默认只读，不修改 SSH、防火墙、路由或系统 DNS。

项目将逐步从 VPS 检测工具发展为 Linux 服务器综合管理助手，未来计划加入：

- 更完整的硬件与网络质量检测
- 配置备份、差异对比及恢复机制
- 常见代理协议的一键部署与管理
- SSH、防火墙和系统安全加固
- 本地 Web UI 与多 VPS 管理

**当前 Beta 仅提供已经实现的检测功能，其余功能属于后续规划。**

## 核心功能

| 模块 | 当前功能 |
| --- | --- |
| 服务器检测 | Linux、CPU、内存、Swap、磁盘、虚拟化与资源状态 |
| 网络诊断 | DNS、TCP/TLS、IPv4/IPv6、UDP/ICMP/TCP Traceroute |
| 线路与 IP | BGP、ASN、IP 归属、网络类型和风险来源 |
| 服务可达性 | 部分流媒体等公开网页可达性检查 |
| 基础安全体检 | SSH、端口、防火墙、文件权限等只读检查 |
| 本地报告 | 中英文 CLI、JSON、Markdown、脱敏与中断恢复 |

## 快速安装

需要 **Linux、Python 3.10+、标准库 venv 和 Git**，推荐使用 Ubuntu 22.04 / 24.04。

### 1. 下载 VPSMaster

打开 Linux 终端，执行：

```bash
git clone https://github.com/griffinmx/VPSMaster.git
cd VPSMaster
```

### 2. 安装 VPSMaster

```bash
python3 -I -B install.py --run
```

安装器会验证文件完整性，在用户目录创建独立运行环境，并自动执行一次**离线体检**。

首次安装不要求 root 权限，不调用 pip、sudo 或系统包管理器，也不会自动修改系统配置。

默认安装目录：

```text
~/.local/share/vpsmaster/1.0.0b1/
```

### 3. 开始中文联网检测

```bash
~/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster all --lang zh
```

程序将自动检测服务器资源、网络连通性、IP/ASN/BGP、路由、部分公开网页可达性及基础安全状态，并保存本地报告。

默认检测总时间预算为 **300 秒**。

**注意：** 安装命令中的 `--run` 执行首次离线体检；`vpsmaster all --lang zh` 才会执行综合联网检测。

网络异常、缺少依赖或权限不足可能导致部分检测结果显示未知或跳过，并不一定代表软件运行失败。

更多安装方式请查看 [安装、更新与卸载指南](docs/guide/INSTALL.md)。

## 一键综合检测

新用户推荐入口：**`vpsmaster all`**。

VPSMaster 复用现有检测模块，实时显示检测进度、执行结果和最终汇总，并自动保存本地报告。

为了方便后续使用，可以在当前终端设置别名：

```bash
alias vpsmaster="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
```

然后执行：

```bash
# 中文综合联网检测
vpsmaster all --lang zh

# 英文综合联网检测
vpsmaster all --lang en

# 中文离线检测
vpsmaster all --offline --lang zh

# 完整模式
vpsmaster all --full --lang zh
```

默认检测包含系统与资源、网络接口、DNS/TCP/TLS、UDP 与条件允许时的 ICMP/TCP 路由、IP/ASN/BGP、网页可达性和基础安全体检。

缺少依赖、权限不足或超时时，程序会保留相应原因，不会将未知结果直接标记为成功。

默认总时间预算为 300 秒，每模块 60 秒；完整模式默认总预算为 600 秒。

`--full` 增加 PTR/TCP25 和中国目标方向的有限路由检测。

带宽测试需要额外指定 `--allow-bandwidth`，测试载荷预算上限为 64 MiB。中国大陆测速候选另需实验性 `--china-speed` 参数。

默认不执行带宽测速、CPU 或磁盘性能基准测试。

[完整参数与检测说明](docs/guide/USAGE.md)

## 常用命令

默认安装使用以下入口，自定义安装目录请使用安装器实际输出的路径。

```bash
VM="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"

"$VM" all --lang zh                         # 综合联网检测
"$VM" all --offline --lang zh               # 离线综合检测
"$VM" check --lang zh                       # 本机基础体检
"$VM" quality --lang zh                     # DNS / TCP / TLS 检测
"$VM" trace --target 1.1.1.1 --method udp    # UDP 路由追踪
"$VM" ipquality                             # IP 归属与风险信息
"$VM" bgp --target 1.1.1.1                  # BGP 信息
"$VM" suite --json-output report.json       # 保存指定 JSON 报告
"$VM" report --input report.json --output report.md
"$VM" --help
```

`proxydoctor` 兼容命令仍然可用。

联网检测涉及第三方服务时，对方可能看到请求来源 IP。分享报告前请人工检查脱敏结果。

## 常见问题

**为什么 GitHub 下载成功，但 TCP/TLS 检测失败？**

Git 使用的代理配置不会自动应用到 VPSMaster。当前部分网络检测明确使用直连方式，DNS 成功也不代表 TCP/TLS 一定成功。

**为什么 Ubuntu Server 中文显示乱码？**

部分 Linux 纯文本控制台不支持中文字体。建议通过支持 UTF-8 和中文字体的 SSH 终端运行，或者使用 `--lang en`。

**为什么检测结果显示 `unknown`、`skipped` 或 `incomplete`？**

可能由网络限制、权限不足、缺少系统工具、请求超时或第三方数据源不可用引起。模块执行完成不代表所有目标均已成功检测。

**安全体检会修改服务器吗？**

不会。当前基础安全体检只读，不自动修改 SSH、防火墙、系统 DNS 或路由，也不会自动执行安全加固。

**检测报告可以公开分享吗？**

建议先人工检查。脱敏不能保证覆盖任意敏感信息，报告仍可能包含公网 IP、网络拓扑等内容。

## Beta 已知限制

- 流媒体仅检测公开网页可达性，不代表实际解锁或播放。
- 中国大陆三网测速仍为实验性功能，默认关闭，不保证完整节点覆盖。
- ICMP/TCP 路由可能需要系统 `traceroute` 和相应权限；BGP、IP 地理位置及风险数据受第三方来源限制。
- 当前主要验证环境为 Ubuntu 22.04 Desktop、24.04 Server（x86_64）；海外 VPS、ARM、公网 IPv6 及更多全新系统镜像尚未全面验证。
- 当前没有一键代理部署、自动安全加固、配置自动回滚或 Web UI。
- Beta 不代表生产环境稳定性或独立安全认证。

[完整技术限制](docs/release/KNOWN_LIMITATIONS.md) · [Beta 发行说明](docs/release/RELEASE_NOTES.md)

## 后续开发方向

VPSMaster 计划分为五个阶段，逐步从服务器检测发展为综合部署与安全管理工具。

| 阶段 | 方向与目标 | 状态 |
| --- | --- | --- |
| **Phase 1 · VPS 综合检测** | 系统与资源、网络连通性、逐跳追踪、BGP/IP、基础安全体检及本地报告恢复 | 当前 Beta 基础能力 |
| **Phase 2 · 检测能力完善与备份回滚** | CLI 彩色综合报表、CPU/磁盘性能基准、三网测速、IP 情报交叉验证、线路建议、安全基线，以及配置备份、差异对比和基础恢复机制 | 规划中 |
| **Phase 3 · 一键代理部署** | 常见代理协议的一键安装、服务配置、状态检测、更新与卸载；逐步支持域名、证书及订阅配置管理 | 规划中 |
| **Phase 4 · 一键安全加固** | SSH 与密钥策略、UFW/nftables、Fail2ban、系统更新、权限和端口加固；提供方案选择、风险解释、修改预览、执行验证及有条件回滚 | 未来重点 |
| **Phase 5 · Web UI 与服务器管理** | 本地 Web 面板、检测报告展示、安全风险管理、备份恢复、多 VPS 管理及可选服务管理 | 长期规划 |

### Phase 2 · 检测能力完善与备份回滚

在现有检测基础上，逐步完善硬件性能、网络质量和 IP 情报分析，并优化 CLI 最终报告的可读性。

同时建设配置备份与恢复基础能力，包括配置快照、差异比较及可验证的恢复流程，为后续服务部署和安全加固提供基础保障。

### Phase 3 · 一键代理部署

面向 VPS 新手，计划提供常见代理协议的简化部署和服务管理功能。

初期优先考虑无需域名的基础部署方式，随后逐步增加需要域名及证书的配置方案。

重点关注安装流程、服务状态、更新、卸载、配置安全及故障诊断。

### Phase 4 · 一键安全加固

未来计划提供可选择的 Linux 服务器安全加固方案，包括 SSH 登录保护、防火墙、Fail2ban、系统更新和权限管理等。

涉及 SSH、防火墙或其他可能影响服务器连接的操作时，必须由用户明确确认。

安全加固遵循：

**检测 → 解释 → 预览 → 确认 → 备份 → 执行 → 验证 → 回滚**

重点保护 SSH 管理连接和现有业务端口，尽可能降低因错误配置导致服务器失联的风险。

回滚功能需要满足相应前提，不承诺自动恢复全部断网、云安全组、重启或宿主机故障。

### Phase 5 · Web UI 与服务器管理

长期计划提供本地 Web 管理面板，集中展示服务器资源、网络质量、安全风险、部署服务和备份状态。

逐步探索多 VPS 管理与可选服务维护能力。

未来 Web 管理入口默认不向公网开放，认证、权限及凭据保护将作为基础安全要求。

**以上 Phase 2–5 功能均为后续规划，不属于当前 Beta.1 已实现能力，也不承诺固定发布时间。**

[完整开发路线](docs/security/ROADMAP.md)

## 文档与贡献

[中文使用文档](docs/guide/USAGE.md) · [English README](README.en.md) · [安装指南](docs/guide/INSTALL.md) · [已知限制](docs/release/KNOWN_LIMITATIONS.md) · [安全加固路线](docs/security/ROADMAP.md)

[文档目录](docs/README.md) · [安全与隐私](docs/security/SECURITY.md) · [Issues](https://github.com/griffinmx/VPSMaster/issues) · [贡献指南](docs/development/CONTRIBUTING.md) · [MIT LICENSE](LICENSE) · [第三方来源及许可声明](THIRD_PARTY_NOTICES.md)

欢迎提交 Bug、功能建议及经过脱敏的测试反馈。

请勿在公开 Issue 中上传密码、Token、SSH 私钥或未经检查的原始报告。

---

**VPSMaster — 看清你的 VPS，让服务器管理更安全。**
