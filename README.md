# VPSMaster

**看清你的 VPS，让服务器管理更安全。**

VPS Diagnostics & Security Toolkit — 面向 VPS 新手和 Linux 用户的开源检测与安全管理工具。

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue) ![Linux](https://img.shields.io/badge/Platform-Linux-lightgrey) [![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE) ![Beta.1](https://img.shields.io/badge/Status-Beta.1-orange)

[English](README.en.md) · [使用文档](docs/guide/USAGE.md) · [反馈问题](https://github.com/griffinmx/VPSMaster/issues)

## 项目简介

VPSMaster 基于 Python，帮助你快速了解 Linux VPS 的硬件资源、网络质量、IP 信息及基础安全风险。当前 Beta.1 提供 CLI 检测与本地报告，普通检测默认只读，不修改 SSH、防火墙、路由或系统 DNS。

项目将从 VPS 检测工具逐步发展为 Linux 服务器安全诊断与加固助手，未来重点是 SSH 与防火墙安全加固、配置备份与回滚、持续安全监控及 Web UI 管理。

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

需要 **Linux、Python 3.10+ 和标准库 venv**。从 [GitHub Releases](https://github.com/griffinmx/VPSMaster/releases) 获取 ZIP 与配套 `SHA256SUMS.txt`，放到同一目录。仓库仍为 Private 时，仅获授权用户可访问；Draft 是发行草稿，并非所有用户均可下载的正式版本。

```bash
sha256sum -c SHA256SUMS.txt
python3 -m zipfile -e VPSMaster-v1.0.0-beta.1.zip .
cd VPSMaster-v1.0.0-beta.1
python3 -I -B install.py --run
```

安装器在用户目录创建隔离环境，输出可执行入口路径；首次运行离线体检，不要求 root，也不调用 pip、sudo 或系统包管理器。缺少依赖时明确退出，不擅自修改系统。[安装、升级与卸载](docs/guide/INSTALL.md)

## 一键综合检测

新用户推荐入口：**`vpsmaster all`**。复用现有检测模块，实时显示正在执行的模块、完成数量、结果与最终汇总，并自动保存脱敏报告。

安装器会打印启动器路径；默认安装可在当前终端设置别名后使用：

```bash
alias vpsmaster="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
vpsmaster all
vpsmaster all --lang zh
vpsmaster all --offline
vpsmaster all --full --allow-bandwidth
```

默认检测系统与资源、接口、DNS/TCP/TLS、UDP 与条件允许时的 ICMP/TCP、IP/ASN/BGP、网页可达性和基础安全。缺依赖、权限不足或超时记录原因后继续。默认总预算300秒、每模块60秒；完整模式总预算600秒，仍无 CPU/磁盘负载基准。

`--full` 增加 PTR/TCP25 与中国目标方向追踪；带宽需 `--allow-bandwidth`，测试载荷上限64 MiB。大陆测速候选另需实验性 `--china-speed`，不会默认启用。[全部选项与边界](docs/guide/USAGE.md)

## 常用命令

默认安装使用下面的入口；自定义目录请使用安装器打印的路径。

```bash
VM="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
"$VM" check --lang zh                       # 本机体检
"$VM" suite --offline --lang zh             # 离线综合检测
"$VM" quality --lang zh                     # DNS / TCP / TLS 网络检测
"$VM" trace --target 1.1.1.1 --method udp    # 逐跳追踪
"$VM" ipquality                            # IP 归属与风险信息
"$VM" suite --json-output report.json       # 联网综合检测并保存报告
"$VM" report --input report.json --output report.md
"$VM" --help
```

`proxydoctor` 兼容命令仍可用。完整参数与可选测速见[使用指南](docs/guide/USAGE.md)。联网服务会看到来源 IP；分享报告前仍需人工复核脱敏结果。

## Beta 已知限制

- 流媒体仅网页可达性，不代表解锁或播放；大陆三网测速仍为实验性，默认关闭。
- ICMP/TCP 可能需要系统 `traceroute` 和相应权限；BGP、IP 地理位置及风险信息受第三方数据限制。
- 已验证实验环境为 Ubuntu 22.04 Desktop、24.04 Server（x86_64）；海外 VPS、ARM、公网 IPv6、全新 Ubuntu 22.04 Server 镜像尚未全面验证。
- 当前没有一键安全加固、自动代理部署和 Web UI；Beta 不代表稳定生产版本或独立安全认证。

[完整技术限制](docs/release/KNOWN_LIMITATIONS.md) · [Beta 发行说明](docs/release/RELEASE_NOTES.md)

## 后续开发方向

| 阶段 | 方向与目标 | 状态 |
| --- | --- | --- |
| Phase 1 · VPS 综合检测 | 系统与资源、网络连通性、逐跳追踪、BGP/IP、基础安全及报告恢复 | 当前 Beta 基础能力 |
| Phase 2 · 检测能力完善 | CPU/磁盘基准、三网测速完善、IP 情报交叉验证、线路建议、安全基线与购买验收 | Planned / 规划中 |
| Phase 3 · 一键安全加固 | SSH 与密钥策略、UFW/nftables、Fail2ban、更新及权限加固；可选方案、风险解释和修改预览 | Planned / 未来重点 |
| Phase 4 · 备份、回滚与监控 | 配置备份与差异、保留 SSH 通道、执行后复验、有条件回滚、审计及持续安全监控 | Planned / 规划中 |
| Phase 5 · Web UI 与管理 | 本地面板、风险与任务汇总、备份恢复、多 VPS 和可选服务管理 | 长期规划 |

未来安全加固必须由用户明确确认，遵循 **检测 → 解释 → 预览 → 确认 → 备份 → 执行 → 验证 → 回滚**。重点保护 SSH 管理访问，不承诺所有故障都能自动恢复；Web 管理入口默认不向公网开放。

以上未来能力尚未实现，不属于当前 Beta，不承诺固定交付时间。[完整开发路线](docs/security/ROADMAP.md)

## 文档与贡献

[中文使用文档](docs/guide/USAGE.md) · [English README](README.en.md) · [安装指南](docs/guide/INSTALL.md) · [已知限制](docs/release/KNOWN_LIMITATIONS.md) · [安全加固路线](docs/security/ROADMAP.md)

[文档目录](docs/README.md) · [安全与隐私](docs/security/SECURITY.md) · [Issues](https://github.com/griffinmx/VPSMaster/issues) · [贡献指南](docs/development/CONTRIBUTING.md) · [MIT LICENSE](LICENSE) · [第三方来源及许可声明](THIRD_PARTY_NOTICES.md)
