# 使用与常见问题 / Usage & FAQ

下例先设置 `VM="$HOME/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster"`；自定义安装请使用安装器打印的路径。逐项参数以 `"$VM" <command> --help` 为准。

| 命令 | 用途 |
| --- | --- |
| `check --lang zh` | 本机体检；仅显式 `--detect-public-ip` 才查询公网出口 |
| `suite --offline --lang en` | 不发起外部探测的综合检测 |
| `quality` | DNS、TCP/TLS、网络质量观察 |
| `trace --target 1.1.1.1 --method udp --max-hops 30` | 默认30跳，最多64跳的逐跳探测 |
| `trace --target 1.1.1.1 --method tcp --tcp-port 443 --geo` | 可选系统 traceroute；位置是推测，最多查询12个公网跳点 |
| `bgp --target 1.1.1.1` | RIPE RIS 的前缀、ASN 与有限路径样本 |
| `ipquality` / `media` | IP 多来源信息 / 公开网页可达性 |
| `cn-nodes` | 实验性中国候选节点的基础探测 |
| `return-route --method udp --max-hops 30` | VPS 到固定中国目标方向，不等于中国到 VPS 去程 |

## 输出和报告

```bash
"$VM" check --lang zh --theme framed --color always
"$VM" suite --json-output report.json
"$VM" report --input report.json --output report.md
"$VM" recover --journal report.json.events.jsonl --output recovered.json
```

主题支持 `default / iprisk / framed`，中英文可选；窄终端推荐 framed。Linux 纯文字控制台默认英文，中文需要字体支持。保存时不覆盖已有文件，默认脱敏；`--show-ip` 只影响终端。中断尝试保存已完成结果，恢复以完整日志事件为准；断电/SIGKILL 不保证尚未落盘的数据。

退出码：`0` 完成；`1` 有发现、结果不完整或存储失败；`2` 参数/安装错误；`130` 中断。模块执行结束不代表全部检测成功。未知、缺依赖或权限不足不会写成安全或解锁。

`suite` 默认省略值仅为“未知／跳过”的空条目及离线未执行模块的标题；使用 `--show-unavailable` 显示这些条目。实际失败和重要限制仍显示，JSON 和恢复日志始终保留完整状态。

## 可选测速（会消耗流量）

```bash
"$VM" bandwidth --allow-bandwidth --rounds 3 --sample-mib 4
"$VM" bandwidth --china --allow-bandwidth --rounds 3 --sample-mib 1
```

默认不开启。下载为节点→本机，上传为本机→节点；中国候选主要提供下载。大陆三网仍实验性，不保证覆盖与可用性；香港移动不替代大陆移动。小样本不证明端口上限，节点拥堵会影响结果。`attempted` 统计计划样本槽（含失败后跳过），不是实际请求次数。

## 常见问题

- **为什么没有安装到 PATH？** 安装器不改 shell 配置；使用打印的完整启动器路径。
- **为什么不能再次安装？** 保护已有文件；使用新的 `--prefix`。
- **为什么 ICMP/TCP 跳过？** 需要系统已有 `traceroute` 和相应权限；不会自动提权/安装。
- **中间跳点超时是否丢包？** 不一定。设备可能只过滤探测响应；不能据单跳延迟判断真实转发拥堵。
- **为什么媒体是 unknown？** DNS、TLS、HTTP、反爬、账号和地区因素不能总是自动区分；网页成功不等于播放成功。
- **报告能直接公开吗？** 仍需人工检查。第三方 API 会看到来源 IP，数据保存和分享受[服务条款](DATA_SERVICES.md)约束。
- **这些 CPU/内存是独享吗？** 只反映来宾可见资源及可见配额，不能证明宿主硬件独享。

[安装指南](INSTALL.md) · [已知限制](../release/KNOWN_LIMITATIONS.md)
