# VPS 检测工具 · 1.0 公测版

[中文](README.md) | [English](README.en.md)

面向 Ubuntu VPS 的 Python 命令行体检工具。内部项目名及命令仍为 ProxyDoctor / `proxydoctor`。
**这是 1.0 公测版，非最终版本。** 包版本 `1.0.0b1`；当前是本地候选包，尚未公开发布或完成最终验收。

## 安装

需要 Linux、Python 3.10+ 和标准库 venv，支持目标为 Ubuntu 22.04 及更新版本。
没有第三方 Python 运行依赖，不调用 sudo、pip 或系统包管理器。
先从可信来源核对摘要，再解压并阅读 install.py。没有 unzip 也可用 Python 解压：

```bash
sha256sum -c ProxyDoctor-v1.0.0-beta.1.zip.sha256
python3 -m zipfile -e ProxyDoctor-v1.0.0-beta.1.zip .
cd ProxyDoctor-v1.0.0-beta.1
python3 install.py --run
```

安装到用户目录的隔离环境，首次仅运行离线体检。已有目录不会覆盖；失败只清理本次新建目录。
缺少 Python/venv 时明确退出，不自动安装系统依赖。`--prefix` 可指定不存在的用户目录。
安装后的启动器及各 Python worker 显式使用 `-B`，忽略用户包路径并禁止这些启动路径生成字节码缓存。此承诺覆盖随包安装器启动命令和源码脚本；自行使用 Python 导入或 `python -m` 时应加 `-B`，pip 的安装期预编译及外部调用方不在此范围。

```bash
PD="$HOME/.local/share/proxydoctor/1.0.0b1/bin/proxydoctor"
"$PD" check --theme framed --lang zh
"$PD" suite --offline --theme framed
"$PD" suite --lang en
"$PD" quality --color always
"$PD" ipquality --show-ip
"$PD" media
"$PD" --help
```

`check`、`suite` 支持 default/iprisk/framed 三种主题。结果直接逐项显示在命令行。
中英文可选；纯 Linux 文本控制台默认英文，显式 `--lang zh` 或 `--lang=zh` 保留中文。

## 能力与范围

| 模块 | 本版能力 | 结果范围 |
| --- | --- | --- |
| 系统和资源 | 系统、CPU、内存、Swap、根分区、可见配额、短采样 steal/PSI | 无法证明资源独享；不执行 CPU/磁盘基准 |
| 网络 | 分 IPv4/IPv6 的 DNS、TCP、证书验证 TLS | 本机到指定目标的当前观测 |
| 路由 | 原生 UDP；可选系统 traceroute 的 ICMP/TCP | 默认 30 跳、最多 64 跳；响应缺失不等于转发丢包 |
| IP 信息 | 归属、ASN、运营商及分来源风险；可选 PTR/TCP25 | 缺失保持未知；接口失败显示，未配置的可选密钥来源可省略 |
| 流媒体 | Netflix、Disney+、YouTube Premium 等 10 项公开网页 | 仅可达性，不输出解锁或播放成功结论 |
| 安全 | SSH、端口、防火墙、权限和更新缓存只读检查 | 不修改配置，不是完整漏洞扫描 |
| 带宽 | 多来源多轮下载，Cloudflare 支持上传 | 必须明确允许；短样本不报线路容量 |
| BGP | RIPE RIS 前缀、起源 ASN、邻居、AS_PATH 样本 | 采集器视角，不等于本机选路或商业上游 |

## 三网、路由和 BGP

实测覆盖以随包提供、SHA256 一致的验收报告为准；没有海外 VPS 验收证据。

ICMP/TCP 权限取决于系统 traceroute。权限不足显示 `PERMISSION_DENIED`，不自动提权。
可选 `--geo` 提供跳点 ASN、运营商、来源与时间；地理位置是数据库推测，最多查询 12 个公网跳点，遇限额停止。窄交互终端面板会适配窗口宽度。

```bash
# 固定候选的小流量探测，不运行带宽测试
"$PD" cn-nodes
# 大陆三运营商候选多轮下载；仍可能不可用，失败如实显示
"$PD" bandwidth --china --allow-bandwidth --rounds 3 --sample-mib 4
"$PD" bandwidth --source cn-telecom-sh --allow-bandwidth
# 香港移动单独标注，不能替代大陆移动
"$PD" bandwidth --source mobile-hk --allow-bandwidth
# ICMP/TCP 需要系统已经安装 traceroute，缺少则明确退出，不提权安装
"$PD" trace --target 1.1.1.1 --method tcp --tcp-port 443 --geo
"$PD" trace --target 1.1.1.1 --method icmp --max-hops 64
# 北京/上海/广州 × 三网，逐条执行，每条约 30 秒探测软预算
"$PD" return-route --method udp
"$PD" return-route --method tcp --family 6
"$PD" bgp --target 1.1.1.1
# 综合入口额外模块需明确开启
"$PD" suite --route-method tcp --include-return-routes --include-bgp
```

三城探测方向为“本机 → 中国目标”，在海外 VPS 上通常称回程；不包含中国侧到 VPS 的去程或全国各省全部线路。
ASN 标签不能证明 CN2 GIA 等套餐等级。测速下载是节点到本机，上传是本机到节点，和逐跳探测方向分别解释。

节点标签来自公开目录，不等于实测身份认证。当前开发机已验证上海电信及香港移动的小图片可访问；大陆联通、移动尚无本轮成功证据。
香港不计入大陆三网覆盖。HTTPS 测速不自动降级明文或关闭证书验证。三网候选本轮仅下载，未实现三网上传。
`cn-nodes` 使用少量明文测试协议数据，不发送凭据或报告；小样本成功不等于带宽容量。

## 报告、安全和中断

报告默认保存在当前目录的 reports/。支持 `--json-output` 的命令可指定路径；已有文件不会覆盖。
保存文件默认脱敏 IP；`--show-ip` 只影响终端。分享前仍须人工复核。

```bash
"$PD" suite --offline --json-output report.json
"$PD" report --input report.json --output report.md
"$PD" recover --journal report.json.events.jsonl --output recovered.json
"$PD" recover --journal report.json.events.jsonl --output recovered.md --format markdown
```

Ctrl+C/SIGTERM 尝试取消活动子进程并保存已有记录。API、DNS、命令、测速有限时；恢复日志有大小上限。
JSON 保留原模块和统一 result_items 的状态、方法、时间、来源及范围。Markdown 使用防提前闭合的 JSON 代码围栏。
断电、SIGKILL、磁盘故障时以最后完整恢复事件为准。

退出码：0 正常完成，1 有提示/不完整/保存失败，2 参数或安装错误，130 中断。
默认只读，不修改 SSH、防火墙、路由、系统 DNS，不自动上传完整报告或修复系统；联网目标会看到请求来源 IP。

## 公测状态与开源

P0 修复自动化：277 通过、1 项 Windows 符号链接权限跳过。当前构建的实机验收结果以随候选 ZIP 单独交付的 BETA_ACCEPTANCE_REPORT.md 和结构化结果中的 SHA256 为准；不将旧候选报告当作本包已通过。ICMP/TCP 实际权限、完整大陆三网和海外回程需按该报告的覆盖范围判断。
旧 Alpha 结果不是本包验收证据。见 [当前状态](CURRENT_STATUS.md)、[变更和待测项](PUBLIC_BETA_CHANGE_REPORT.md)。
尚无全国完整三网、长期监测、CPU/磁盘基准、DNSBL、Web UI、代理部署、Karing 订阅或自动更新卸载。
更新安装到新版本目录；卸载前退出进程、备份报告，仅移除自己确认过的安装目录。

MIT 项目，标准库运行。感谢 [NextTrace](https://github.com/nxtrace/NTrace-core)、[CleanIP sh.cd](https://github.com/CleanIP/sh.cd)、[RIPEstat](https://stat.ripe.net/) 和既有参考项目；详见 [来源和许可](THIRD_PARTY_NOTICES.md)。不打包下载执行第三方检测脚本或测速客户端。
