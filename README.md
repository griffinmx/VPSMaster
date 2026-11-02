# VPSMaster

**面向 Linux VPS 用户的一站式服务器检测、网络诊断与管理工具。**

[中文](README.md) · [English](README.en.md) · [已知限制](KNOWN_LIMITATIONS.md) · [贡献指南](CONTRIBUTING.md)

VPSMaster 是基于 Python 的开源 VPS 综合检测与管理工具，主要面向中文 Linux 社区及 VPS 初学者。
**当前 `1.0.0b1` 是以 CLI 为核心的 Beta 公测候选，非生产稳定版；管理能力仍在规划中。**
项目强调安全、易用和检测结果透明：普通检测默认不修改 SSH、防火墙、路由或系统 DNS，未知结果不会被写成安全或成功。

> An open-source VPS diagnostics and management toolkit. The current Beta focuses on transparent, read-only CLI diagnostics; management and Web UI are planned.

## Available / 当前可用

| 模块 | 当前 Beta 能力 | 判断边界 |
| --- | --- | --- |
| 服务器信息与资源 | Linux/内核/架构、CPU、内存、Swap、磁盘容量、可见配额、短时 steal/PSI | 不能证明硬件独享；没有 CPU/磁盘基准 |
| 网络基础 | DNS、分 IPv4/IPv6 的 TCP、证书验证 TLS、接口和路由信息 | 取决于权限、网络和目标服务，保留错误与未知 |
| Traceroute | 自主 UDP，可选系统 traceroute 的 ICMP/TCP；IP、RTT、响应/超时、可选 ASN/位置 | 默认30跳、最多64跳；跳点不响应不等于真实转发丢包 |
| BGP / ASN | RIPE RIS 前缀、起源 ASN、邻居及有限 AS_PATH 样本 | 采集器视角，不代表本机选路、商业上游或优质线路承诺 |
| IP 信息与风险 | 多来源归属、网络类型、代理/VPN/Tor/风险信息及冲突；可选 PTR/TCP25 | 不合成不透明“纯净度”；第三方可能失败、限额或缺字段 |
| 流媒体网页 | Netflix、Disney+、YouTube 等10项公开服务页面的基础可达性 | **不保证解锁、登录后地区权限或实际播放** |
| 基础安全体检 | SSH、监听端口、防火墙、固定敏感路径权限、更新缓存 | 只读提示，不是完整漏洞扫描或自动修复 |
| 本地报告 | 脱敏 JSON、Markdown、逐步恢复日志、失败隔离、中英文终端主题 | 分享前仍需人工复核；断电/SIGKILL不能保证未落盘数据 |
| 可选带宽与中国目标 | 多来源多轮有界下载/部分上传、固定中国候选与三城九方向追踪入口 | 需明确允许流量；大陆三网实验性，默认关闭；不是完整全国回程 |

“模块执行完成”不等于目标可用或检测结论完整。`success / failure / skipped / unsupported / unknown` 与原因、时间、方法和来源分别保留。

## 安装

需要 Linux、Python **3.10+** 及标准库 `venv`。运行时没有第三方 Python 包依赖；安装器不调用 pip、sudo 或系统包管理器。
先从可信渠道取得 ZIP 和校验文件，并阅读 `install.py`；校验和不能独立证明发布者身份。

```bash
sha256sum -c VPSMaster-v1.0.0-beta.1.zip.sha256
python3 -m zipfile -e VPSMaster-v1.0.0-beta.1.zip .
cd VPSMaster-v1.0.0-beta.1
python3 -I -B install.py --run
VM="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"
"$VM" --version
"$VM" check --lang zh --theme framed
```

安装到用户目录的隔离环境，`--run` 首次只运行离线体检。缺少 Python/venv 会明确退出，不擅自安装系统依赖。
已有安装目录不会覆盖。需要另一路径时用 `python3 -I -B install.py --prefix "$HOME/vpsmaster-beta-test"`，并使用打印出的启动器路径。

### 更名与兼容性

- 项目旧名 **ProxyDoctor**；当前用户可见品牌统一为 **VPSMaster**。
- 新命令为 `vpsmaster`，同一安装目录保留 `proxydoctor` 兼容入口；两者调用同一实现。
- Python 包名、发行元数据中的旧包标识 `proxydoctor`、导入路径、已有 JSON schema 和 `PROXYDOCTOR_*` 环境变量保留。没有宣称支持新的 `VPSMASTER_*` 变量。
- 新默认目录为 `~/.local/share/vpsmaster/1.0.0b1`；旧安装、报告和 `~/.local/share/proxydoctor/` 不自动改名或迁移。
- 源码入口 `bash vpsmaster.sh ...` 与 `bash proxydoctor.sh ...` 均可用。提供的启动器与 Python workers 使用 `-B`，不通过删除缓存掩盖问题；外部自行导入不在此承诺范围。

## 使用

```bash
# 本机体检，不发起外部探测（--detect-public-ip 是另行选择的联网选项）
"$VM" check --lang zh --color always
"$VM" suite --offline --lang en

# 联网模式：目标服务会看到请求来源 IP
"$VM" quality --lang zh
"$VM" suite --lang zh --json-output report.json
"$VM" trace --target 1.1.1.1 --method udp --max-hops 30
"$VM" trace --target 1.1.1.1 --method tcp --tcp-port 443 --geo
"$VM" bgp --target 1.1.1.1
"$VM" ipquality
"$VM" media

# 本地导出和恢复；不覆盖已有文件
"$VM" report --input report.json --output report.md
"$VM" recover --journal report.json.events.jsonl --output recovered.json
"$VM" --help
```

ICMP/TCP 需要系统已有 traceroute，权限不足显示 `PERMISSION_DENIED`，缺依赖明确跳过/退出，不自动提权安装。
`--geo` 最多查询12个公网跳点，私有/保留地址不外发；位置是数据库推测，不是物理路径证明。

默认不运行带宽测试。确需测试时单独允许，并先核对命令预告的负载预算：

```bash
"$VM" bandwidth --allow-bandwidth --rounds 3 --sample-mib 4
# 实验性：中国大陆三网候选，并不保证三网都有可用节点
"$VM" bandwidth --china --allow-bandwidth --rounds 3 --sample-mib 1
"$VM" cn-nodes
"$VM" return-route --method udp --max-hops 30
```

下载方向为“节点 → 本机”，上传为“本机 → 节点”；中国候选当前下载为主。香港移动单独标注，不能替代大陆移动。
短文件成功不是线路容量；`attempted` 目前统计计划样本槽，包含失败后自动跳过的槽位，不是实际网络请求次数，需查看每个样本错误。

### CLI 示例输出

以下是**格式示意**，`<RTT>` 等为占位符，不是本发行包的测速成绩：

```text
1.0.0b1 · VPSMaster · 1.0 公测版（非最终版本）
 1  127.0.0.1    <RTT> ms    内网/保留地址  AS? --- [reached]
追踪结果           reached
恢复日志: <本地文件路径>
```

终端逐项回显，支持 `default / iprisk / framed` 和中英文；`framed` 适配窄终端。
Linux纯文字控制台默认英文，显式 `--lang zh` 保留中文，但需要终端字体支持。

## 已验证环境与验收范围

已有实机基线是 **Ubuntu 22.04.5 Desktop / Python3.10.12 / x86_64** 与 **Ubuntu 24.04.3 Server / Python3.12.3 / x86_64**。
本次 VPSMaster 构建使用新 ZIP、全新 HOME/安装目录重新验收；**仅旁附与 ZIP SHA256 一致的验收报告可证明本构建通过**。
旧 ProxyDoctor 验收包保留，不能换名充当 VPSMaster 的通过证据。

当前测试不等于全新22 Server镜像、海外VPS、ARM或公网IPv6已全面验证。
ICMP/TCP 的回环成功和有限公网观察，不代表所有线路或完整公网路径可用。
版本与实际范围见 [当前状态](CURRENT_STATUS.md)、[发行说明](RELEASE_NOTES.md) 和包外验收报告。

## 安全与隐私

普通检测不修改 SSH、防火墙、路由或系统 DNS，不自动修复或上传完整报告。
安装器只创建指定的用户隔离环境；检测和导出会创建本地报告。联网 API、媒体页和测速服务仍会看到请求来源 IP。
提供的入口有超时与取消处理；Ctrl+C/SIGTERM 尝试保存已有结果，恢复以最后完整日志事件为准。
退出码：`0` 完成，`1` 有发现/不完整/存储失败，`2` 参数或安装错误，`130` 中断。

`--show-ip` 只影响终端显示；导出默认脱敏 IP、已知密钥字段和URL凭据，但不是任意文本匿名器。
不要公开原始日志、订阅地址、密码、Token或私钥。安全问题见 [SECURITY.md](SECURITY.md)，未知不能当作安全保证。

## Roadmap / 开发路线 — Planned / 规划中

以下是未来目标，**不代表当前 Beta 已实现**。阶段一包含现有基础诊断的继续完善；未承诺交付日期。

### 阶段一：网络与硬件检测完善 — Planned

- 中国大陆三运营商测速完善
- ICMP/TCP/UDP 线路诊断深化
- BGP、ASN 和线路分析深化
- CPU 和磁盘性能基准
- IP 情报与信誉来源扩展

### 阶段二：长期监控与诊断 — Planned

- 长时间网络稳定性监测
- 晚高峰性能分析
- 历史报告对比
- 异常检测和诊断建议
- VPS 购买验收报告

### 阶段三：安全与维护 — Planned

- 深度安全体检
- 安全修复建议和预览
- 配置备份及回滚
- 服务器维护辅助功能

### 阶段四：自动化管理及 Web UI — Planned

- 可选服务器服务部署
- 模块化管理能力
- 本地 Web UI
- 服务器状态可视化
- 可选服务配置和管理功能

## Known Limitations / 已知限制

- 流媒体主要是公开网页可达性，不保证解锁、订阅权限、地区可用性或实际播放。
- 中国大陆三网测速仍为实验性能力，默认关闭；没有完整可靠三网覆盖承诺。
- BGP/IP 地理信息依赖第三方来源、准确性、服务条款和限额；位置不证明物理路由。
- 海外 VPS、ARM、公网 IPv6、全新 Ubuntu22 Server 镜像未全面验证；新GUI字体渲染须单独目视验收。
- Beta 不代表生产稳定性、独立安全认证或资源独享证明。
- **当前没有 Web UI、自动代理部署或完整管理面板。** 也没有长时间监控、CPU/磁盘基准或完整全国三网回程。

详见 [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)。更新请安装到新的、确认不存在的目录；卸载前备份报告，只移除自己确认的安装目录。

## 贡献、Issues 与许可

欢迎文档、翻译、可复现Bug和有来源的检测规则贡献，见 [CONTRIBUTING.md](CONTRIBUTING.md)。
仓库公开后使用顶部 **Issues → New issue**；[Bug 模板](.github/ISSUE_TEMPLATE/bug_report.md) 和 [功能建议模板](.github/ISSUE_TEMPLATE/feature_request.md) 已随源码提供。
当前未配置公开仓库地址，不编造仓库URL；敏感安全问题不要发到公开Issues。

项目采用 [MIT](LICENSE)，保留旧品牌贡献者版权。标准库运行，不打包第三方测速客户端/地理数据库，不下载执行外部检测脚本。
感谢相关开源项目与数据服务，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 [OPEN_SOURCE_REFERENCES.md](OPEN_SOURCE_REFERENCES.md)。
本项目MIT许可不覆盖第三方API、数据库或测速服务，使用时仍需遵守其条款、配额与权限；没有长期或高负载使用授权保证。
数据保留/分享边界（含IP2Location适用缓存期限）见 [第三方接口条款](docs/DATA_SERVICES.md)；当前工具不自动删除历史报告。
