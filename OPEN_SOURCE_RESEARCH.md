# 开源源码研究（首轮）

阅读日期：2026-11-01。通过 GitHub 连接器实际获取根目录、下列源码及 LICENSE；未运行参考脚本、未复制实现。链接为阅读时默认分支，可变化，实施任何复用前还需固定 commit 和复核依赖许可证。本轮是入口级研究，不宣称完成整个仓库审计。

| 项目 | 实际阅读文件/入口 | 源码观察与采用方案 | 根许可证及处理 | 风险、费用和后续工作 |
|---|---|---|---|---|
| [YABS](https://github.com/masonr/yet-another-bench-script) | [yabs.sh](https://github.com/masonr/yet-another-bench-script/blob/master/yabs.sh)，本地 fio/iperf3 探测、FIO_BIN_TAG/IPERF_BIN_TAG、catch_abort、JSON 参数路径；LICENSE | 现有实现已有本地工具优先、基准跳过、JSON 和中断处理；我们计划独立编写本地工具适配器，消费其 JSON，不复制 shell。分别统计方法/节点便于比较 | 根 LICENSE 为 WTFPL v2；未来 fio/iperf3 的二进制、库及分发许可须单独核查，根许可不覆盖一切 | 脚本含下载和可选结果发送；本项目不采用自动下载/上传。测速节点条款和流量费用未逐项确认，不能默认集成 |
| [Backtrace](https://github.com/oneclickvirt/backtrace) | [cmd/main.go](https://github.com/oneclickvirt/backtrace/blob/main/cmd/main.go)：newBacktraceFlagSet、validateStructuredOptions、RunRouteReport 调用及 ResolveOriginASNWithConfig | 已有结构化路由、尝试次数、超时和可选 WHOIS/geofeed；计划自主建立 ASN 特征证据，保留现有 UDP 核心。中国目标只标为 VPS→中国方向 | Apache-2.0；如未来复用须保留许可、版权和适用 NOTICE，并注明修改；本轮无复制 | 入口包含外部访问；bk/bgptools 深层算法与数据库许可尚待审查。ASN 不代表具体城市或必经专线；外部服务限额/费用待核 |
| [ECS](https://github.com/oneclickvirt/ecs) | [goecs.go](https://github.com/oneclickvirt/ecs/blob/master/goecs.go)：runStructuredCLI、legacyDeadlineWindows、sanitizeECSLog、main | 已有显式结构化 CLI 和编排/日志处理入口，不能声称这些是本项目独有。借鉴分阶段调度理念，自主实现 Python 故障隔离和预算 | GPL v3 文本；不复制其实现；如果未来引入须先评估衍生/分发义务并征求用户确认 | 多模块和外部组件需逐个审核，内部实现尚未逐项研究。数据服务条款及费用待核实；不能以根仓库许可替代依赖审查 |
| [NodeQuality](https://github.com/LloydAsp/NodeQuality) | [NodeQuality.sh](https://github.com/LloydAsp/NodeQuality/blob/main/NodeQuality.sh)：load_bench_os、chroot_run、clear_mount、sig_cleanup、upload_result、main | 有临时系统、分模块选择、信号清理和报告组织；main 调用 upload_result。只借鉴模块组织和清理思路，采用本地报告、非 root 检测；现有包装入口暂停 | AGPL v3 文本；不复制代码。不因采用外部进程就认定豁免许可责任 | chroot/mount/swap 与远程脚本执行不符合当前默认边界；上传报告需另行明确授权。不能仅依据“临时系统”认定对宿主无影响 |
| [OneClickVirt](https://github.com/oneclickvirt/oneclickvirt) | 根目录、[agent-regressions.yml](https://github.com/oneclickvirt/oneclickvirt/blob/main/.github/workflows/agent-regressions.yml)：Go race 检查、OS matrix、Cargo locked 与 musl 目标 | 工程已有多环境回归和依赖锁定；借鉴 CI 组织方法，独立编写 Python Mock/Ubuntu 矩阵。该项目是控制面/Agent/Web 工程，不是检测核心的直接替代 | GPL v3 文本；不复制工作流或产品代码。后续引入任何组件单独审核 | 看到 CI 配置不证明运行通过；此工作流不证明所有 Ubuntu、ARM 或本项目兼容。无需接入其部署功能，外部服务费用不适用当前研究 |

## 竞争判断

已观察到：YABS 的结构化输出、Backtrace 的结构化路由入口、ECS 的编排和日志入口、NodeQuality 的中断清理、OneClickVirt 的多环境 CI。因此不能以这些名称本身宣称优于竞品。上述源码审查也不足以证明竞品缺少某能力。

本项目可验证的候选优势：默认跳过基准、明确许可测速、保守地区证据、本地报告和历史比较。前两项本轮已修改但未测试；后两项部分存在或待开发，暂不作优越性宣传。API 条款、数据集许可、费用和深层实现仍须逐项研究后才能集成。
