> 历史记录 / Historical record：ProxyDoctor 是项目旧名。以下旧版本、SHA256、测试数量与路径保留原样，不代表 VPSMaster 新构建已通过；当前范围见 README.md、CURRENT_STATUS.md 和新包同 SHA256 验收报告。

> 最终加固：路由错误分类、跳点 ASN/运营商来源、窄终端适配已有回归。环境覆盖与结论以同 SHA256 的 FINAL_TEST_REPORT.md 为准。完整大陆三网、海外 VPS、ARM、新装 22 Server 尚未完成。
> 历史 Alpha/问题状态记录：当前 1.0 公测候选请以 CURRENT_STATUS.md 和 PUBLIC_BETA_CHANGE_REPORT.md 为准；新增代码不等于已完成实测。

> 最新Alpha优先项状态见 [ALPHA_TASK_STATUS.md](ALPHA_TASK_STATUS.md)。以下包含本轮前历史统计，不能作为最新发布验收结论。


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

# 全部需求追踪表


更新：2026-11-01。范围：独立 Python CLI；不开发代理部署或 Web UI。

本轮按用户要求不执行测试。历史 outputs/ 验收报告属于 0.5.0，不能证明本分支修改通过。状态中“部分实现”只表示源码证据；未将存在函数名等同于验收。

优先级：P0 默认安全与保存/隔离 → P1 结构化本机、双栈网络和证据 → P2 路由/信誉/媒体与报告 → P3 基准、长期监测、安装与集成。

P0 本轮：综合流程移除自动 CPU 基准；带宽要求显式许可；暂停可上传数据的第三方脚本入口。实现未测试。保存/隔离已编写，待验证；最新汇总见 CURRENT_STATUS.md。


## 第一类：VPS 本机与硬件检测


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 01-01 | 准确识别 Linux 发行版、内核、CPU 架构及虚拟化类型。 | 部分实现 | P1 | proxydoctor/checks.py; suite.py（源码审查；非通过证据） | 只读 /proc、cgroup v1/v2、PSI；CPU/fio 基准独立授权；标准库；可选 fio | tests/test_server_info.py; test_checks.py，逐项补缺并运行；本轮未执行 | 配额不等于物理资源；VM 不代表商家配置 |
| 01-02 | 识别 CPU 型号、核心数、频率及实际资源配额。 | 部分实现 | P1 | proxydoctor/checks.py; suite.py（源码审查；非通过证据） | 只读 /proc、cgroup v1/v2、PSI；CPU/fio 基准独立授权；标准库；可选 fio | tests/test_server_info.py; test_checks.py，逐项补缺并运行；本轮未执行 | 配额不等于物理资源；VM 不代表商家配置 |
| 01-03 | 检测内存、Swap、磁盘容量与资源限制。 | 部分实现 | P1 | proxydoctor/checks.py; suite.py（源码审查；非通过证据） | 只读 /proc、cgroup v1/v2、PSI；CPU/fio 基准独立授权；标准库；可选 fio | tests/test_server_info.py; test_checks.py，逐项补缺并运行；本轮未执行 | 配额不等于物理资源；VM 不代表商家配置 |
| 01-04 | 检测 CPU steal、内存压力、资源争用。 | 部分实现 | P1 | proxydoctor/checks.py; suite.py（源码审查；非通过证据） | 只读 /proc、cgroup v1/v2、PSI；CPU/fio 基准独立授权；标准库；可选 fio | tests/test_server_info.py; test_checks.py，逐项补缺并运行；本轮未执行 | 配额不等于物理资源；VM 不代表商家配置 |
| 01-05 | 实现可重复、可比较的 CPU 性能基准。 | 尚未实现 | P1 | proxydoctor/checks.py; suite.py（源码审查；非通过证据） | 只读 /proc、cgroup v1/v2、PSI；CPU/fio 基准独立授权；标准库；可选 fio | tests/test_server_info.py; test_checks.py，逐项补缺并运行；本轮未执行 | 配额不等于物理资源；VM 不代表商家配置 |
| 01-06 | 检测磁盘吞吐、IOPS、读写延迟，严格限制磁盘写入和占用。 | 尚未实现 | P1 | proxydoctor/checks.py; suite.py（源码审查；非通过证据） | 只读 /proc、cgroup v1/v2、PSI；CPU/fio 基准独立授权；标准库；可选 fio | tests/test_server_info.py; test_checks.py，逐项补缺并运行；本轮未执行 | 配额不等于物理资源；VM 不代表商家配置 |
| 01-07 | 支持用户输入购买规格，并对比实际可见配置；无法核实时明确说明。 | 尚未实现 | P1 | proxydoctor/checks.py; suite.py（源码审查；非通过证据） | 只读 /proc、cgroup v1/v2、PSI；CPU/fio 基准独立授权；标准库；可选 fio | tests/test_server_info.py; test_checks.py，逐项补缺并运行；本轮未执行 | 配额不等于物理资源；VM 不代表商家配置 |


## 第二类：基础网络与 DNS


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 02-01 | 检测公网 IPv4、IPv6、默认路由和网络接口。 | 部分实现 | P1 | checks.py; quality.py; net.py（源码审查；非通过证据） | 分协议族 DNS/TCP/TLS/UDP 探针；PMTU 需注明权限与路径限制；socket/ssl；可选系统工具 | tests/test_quality.py; test_review.py，逐项补缺并运行；本轮未执行 | NAT 出口不代表入站；DNS 解析预算待核查 |
| 02-02 | 分别验证 IPv4/IPv6 外网连通性。 | 尚未实现 | P1 | checks.py; quality.py; net.py（源码审查；非通过证据） | 分协议族 DNS/TCP/TLS/UDP 探针；PMTU 需注明权限与路径限制；socket/ssl；可选系统工具 | tests/test_quality.py; test_review.py，逐项补缺并运行；本轮未执行 | NAT 出口不代表入站；DNS 解析预算待核查 |
| 02-03 | 测量 DNS 解析时间、成功率和错误类型。 | 尚未实现 | P1 | checks.py; quality.py; net.py（源码审查；非通过证据） | 分协议族 DNS/TCP/TLS/UDP 探针；PMTU 需注明权限与路径限制；socket/ssl；可选系统工具 | tests/test_quality.py; test_review.py，逐项补缺并运行；本轮未执行 | NAT 出口不代表入站；DNS 解析预算待核查 |
| 02-04 | 区分 DNS、网络路径及目标服务故障。 | 尚未实现 | P1 | checks.py; quality.py; net.py（源码审查；非通过证据） | 分协议族 DNS/TCP/TLS/UDP 探针；PMTU 需注明权限与路径限制；socket/ssl；可选系统工具 | tests/test_quality.py; test_review.py，逐项补缺并运行；本轮未执行 | NAT 出口不代表入站；DNS 解析预算待核查 |
| 02-05 | 测试 TCP 连接、TLS 握手与 UDP 连通性。 | 部分实现 | P1 | checks.py; quality.py; net.py（源码审查；非通过证据） | 分协议族 DNS/TCP/TLS/UDP 探针；PMTU 需注明权限与路径限制；socket/ssl；可选系统工具 | tests/test_quality.py; test_review.py，逐项补缺并运行；本轮未执行 | NAT 出口不代表入站；DNS 解析预算待核查 |
| 02-06 | 检查 MTU/PMTU、双栈异常与 IPv6 连接问题。 | 尚未实现 | P1 | checks.py; quality.py; net.py（源码审查；非通过证据） | 分协议族 DNS/TCP/TLS/UDP 探针；PMTU 需注明权限与路径限制；socket/ssl；可选系统工具 | tests/test_quality.py; test_review.py，逐项补缺并运行；本轮未执行 | NAT 出口不代表入站；DNS 解析预算待核查 |
| 02-07 | 正确处理 NAT、容器、多网卡环境，避免误判公网出口。 | 部分实现 | P1 | checks.py; quality.py; net.py（源码审查；非通过证据） | 分协议族 DNS/TCP/TLS/UDP 探针；PMTU 需注明权限与路径限制；socket/ssl；可选系统工具 | tests/test_quality.py; test_review.py，逐项补缺并运行；本轮未执行 | NAT 出口不代表入站；DNS 解析预算待核查 |


## 第三类：Traceroute、BGP 与线路分析


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 03-01 | 保留现有 Traceroute 核心代码并完善。 | 部分实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-02 | 支持可行的 ICMP、UDP、TCP 探测方式。 | 部分实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-03 | 显示逐跳 IP、RTT、超时及具有明确统计依据的丢包数据。 | 部分实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-04 | 查询逐跳 ASN、运营商、推测地区。 | 尚未实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-05 | 避免将不响应的路由器错误判断为线路故障。 | 尚未实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-06 | 避免将单个中间节点的高延迟直接认定为拥堵。 | 尚未实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-07 | 检测中国电信、联通、移动相关线路特征。 | 尚未实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-08 | 支持 BGP、上游网络与 ASN 信息分析。 | 尚未实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-09 | 明确区分 VPS → 中国与中国 → VPS 的测试方向。 | 尚未实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-10 | 地理位置只显示推测结果，不声称是真实物理线路。 | 部分实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |
| 03-11 | 无中国侧测试节点时，不伪造中国到 VPS 的去程检测。 | 尚未实现 | P2 | routes.py; geo.py（源码审查；非通过证据） | 保留 UDP；扩展多轮与 TCP/ICMP，ASN 来源独立记录；标准库；可选 mtr；ASN API | tests/test_routes.py; test_console_geo.py，逐项补缺并运行；本轮未执行 | 中间跳不响应不等于丢包；无中国探针不生成去程 |


## 第四类：IP 地理位置、纯净度与信誉


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 04-01 | 查询国家、地区、城市、ASN、运营商。 | 尚未实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-02 | 识别住宅、机房、移动网络等 IP 分类。 | 尚未实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-03 | 查询代理、VPN、Tor 及相关风险标签。 | 部分实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-04 | 支持多个数据源交叉验证与冲突提示。 | 部分实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-05 | 查询公开黑名单、DNSBL、邮件信誉。 | 尚未实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-06 | 检测 PTR 等 DNS 邮件相关信息。 | 尚未实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-07 | 不使用缺乏依据的绝对“纯净度分数”。 | 尚未实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-08 | 处理 API 限速、失效、付费要求和服务条款。 | 尚未实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |
| 04-09 | 每条结果记录来源、查询时间、可信度及限制。 | 尚未实现 | P2 | ipquality.py; geo.py（源码审查；非通过证据） | 保留分源风险；补 PTR 与允许使用的 DNSBL；现有三来源；可选密钥 API | tests/test_measurements.py; test_phase1_delivery.py，逐项补缺并运行；本轮未执行 | 来源条款/限额需逐项审核；风险分不可合并 |


## 第五类：流媒体与在线服务可用性


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 05-01 | 检测 Netflix、Disney+、YouTube 等服务。 | 部分实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-02 | 检测 ChatGPT 等在线服务的网络与地区可用性。 | 尚未实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-03 | 区分网络可达、地区识别、受限、需要登录、无法确认及实际播放成功。 | 尚未实现 | P0 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-04 | 检测 DNS、TLS、HTTP 错误及服务端限制。 | 尚未实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-05 | 禁止将 HTTP 200 直接判定为成功解锁。 | 部分实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-06 | 处理网站检测规则变化、反爬限制和误报。 | 尚未实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-07 | 明确声明账号权限、订阅资格和实际播放能力可能无法自动验证。 | 部分实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-08 | 支持用户自定义合法检测目标。 | 尚未实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |
| 05-09 | 不尝试绕过账号验证、反爬或访问限制。 | 尚未实现 | P2 | media.py（源码审查；非通过证据） | 保守证据状态机；自定义目标仅合法 HTTPS 且限响应；urllib/ssl | tests/test_media.py，逐项补缺并运行；本轮未执行 | HTTP 200 不等于播放；反爬/订阅保持未知 |


## 第六类：多地区测速与长期稳定性


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 06-01 | 研究可信的全球及中国不同运营商测试节点。 | 尚未实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-02 | 测量延迟、抖动、丢包、下载和上传速率。 | 尚未实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-03 | 严格区分测试方向、节点地理位置与节点运营商。 | 部分实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-04 | 限制带宽、并发、执行时间及流量消耗。 | 尚未实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-05 | 识别测试节点瓶颈，避免假性低速。 | 尚未实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-06 | 支持可中断的 24/48 小时低负载监测。 | 尚未实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-07 | 分析晚高峰性能劣化、间歇性断线、突发丢包。 | 尚未实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-08 | 关联 CPU steal、内存压力及网络质量的时间变化。 | 部分实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |
| 06-09 | 中断监测时安全退出并保留已有数据。 | 尚未实现 | P3 | bandwidth.py; quality.py（源码审查；非通过证据） | 显式流量许可；增加受控节点、可取消 JSONL 监测；HTTPS；可选 iperf3 | tests/test_bandwidth_sources.py，逐项补缺并运行；本轮未执行 | 载荷预算不含协议开销；节点瓶颈不代表线路 |


## 第七类：基础安全体检


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 07-01 | 只读检查 SSH 配置和潜在高风险认证方式。 | 部分实现 | P1 | checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |
| 07-02 | 检查监听端口及可能暴露的服务。 | 部分实现 | P1 | checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |
| 07-03 | 识别系统防火墙状态，说明云安全组无法从本机完整确认。 | 部分实现 | P0 | checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |
| 07-04 | 检查系统更新状态及基础安全设置。 | 部分实现 | P1 | security.py; checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_security.py; checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |
| 07-05 | 检测重要文件权限风险。 | 部分实现 | P1 | security.py; checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_security.py; checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |
| 07-06 | 避免把正常业务配置直接定义为漏洞。 | 尚未实现 | P1 | checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |
| 07-07 | 提供有依据的修复建议，但不自动执行。 | 部分实现 | P0 | checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |
| 07-08 | 避免泄露密码、Token、私钥及其他敏感信息。 | 尚未实现 | P1 | checks.py（源码审查；非通过证据） | 保留 SSH/监听/防火墙只读；补更新缓存和权限检查；标准库；系统只读命令 | tests/test_checks.py; test_review.py，逐项补缺并运行；本轮未执行 | Match 条件和云安全组无法完整推断 |


## 第八类：报告、诊断与历史记录


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 08-01 | 设计统一的结构化检测结果 Schema。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-02 | 区分成功、失败、跳过、不支持和无法判断。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-03 | 保存检测时间、方法、来源、错误与置信度说明。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-04 | 将技术指标转换成普通用户能理解的中文解释。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-05 | 提供基于规则和真实测量结果的诊断建议。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-06 | 支持本地 JSON、Markdown 报告，必要时提供 HTML。 | 部分实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-07 | 对分享用报告进行脱敏。 | 部分实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-08 | 上传失败、断网或意外退出时不丢失已有报告。 | 尚未实现 | P0 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-09 | 支持历史记录及不同时间、不同服务器的对比。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-10 | 生成 VPS 购买验收报告，区分实际测量与用户提供的购买规格。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |
| 08-11 | 不生成未经校准的绝对性能评分。 | 尚未实现 | P2 | checks.Result; suite.run_suite; cli.redact（源码审查；非通过证据） | 兼容旧 Schema；增证据模型、增量记录、Markdown、历史差异；标准库 JSON/SQLite | tests/test_stage1.py; test_suite.py，逐项补缺并运行；本轮未执行 | 目前结束才保存；脱敏不是匿名保证 |


## 第九类：安装、兼容性与用户体验


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 09-01 | 实现面向小白的一键安装与运行。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-02 | 检查 Python 版本、依赖及权限。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-03 | 使用虚拟环境隔离依赖，不污染系统 Python。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-04 | 优先兼容 Ubuntu 22.04 Server、24.04 Desktop。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-05 | 评估其他发行版、容器、ARM/x86 架构兼容性。 | 外部条件不足，待实机验证 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-06 | 提供中文和英文输出，处理终端编码问题。 | 部分实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-07 | 尽可能支持非 root 检测。 | 部分实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-08 | 缺少依赖时友好提示、降级或跳过。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-09 | 提供帮助、参数说明、更新、卸载和离线说明。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-10 | 安装脚本可审查，采用可信来源及版本固定/完整性验证。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |
| 09-11 | 不要求用户盲目执行来源不明的 curl | bash。 | 尚未实现 | P3 | proxydoctor.sh; pyproject.toml; README.md（源码审查；非通过证据） | 虚拟环境安装、版本校验、受控更新卸载；Python >=3.10；setuptools | tests/test_phase1_delivery.py; test_i18n.py，逐项补缺并运行；本轮未执行 | 现有脚本只启动，不隔离安装；ARM 未实测 |


## 第十类：可靠性、隐私与自动化测试


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 10-01 | 验证默认检测确实不修改系统配置。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-02 | 区分普通检测与高负载、有写入的基准测试。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-03 | 对运行时间、CPU、磁盘、流量设置安全上限。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-04 | 处理超时、网络失败、权限错误和依赖缺失。 | 部分实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-05 | 保证模块故障隔离。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-06 | 处理 Ctrl+C、安全取消与临时文件清理。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-07 | 防止命令注入、路径问题、终端控制字符污染和敏感日志泄露。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-08 | 使用 Mock、单元测试、集成测试和异常场景测试。 | 部分实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-09 | 在两种 Ubuntu 虚拟机及真实 VPS 上验证。 | 外部条件不足，待实机验证 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-10 | 建立安全的社区错误反馈方式。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |
| 10-11 | 检查第三方许可证、依赖安全和 API 使用条款。 | 尚未实现 | P0 | net.py; console.py; checks.Host; __main__.py（源码审查；非通过证据） | 模块隔离、全局预算、取消保存、终端与日志脱敏；Mock/pytest（开发依赖） | tests/，逐项补缺并运行；本轮未执行 | 修改后未测试；真实 VPS 尚缺 |


## 第十一类：开源维护与未来 FlexMaster 集成


| 编号 | 需求 | 状态 | 优先级 | 代码/证据 | 实现/依赖 | 验证方案 | 限制 |
|---|---|---|---|---|---|---|---|
| 11-01 | 每个检测模块既能由 CLI 使用，也能通过 Python API 调用。 | 尚未实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |
| 11-02 | 检测核心与终端 UI 解耦。 | 尚未实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |
| 11-03 | 为未来 FlexMaster 设计稳定、可复用的接口。 | 尚未实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |
| 11-04 | 完善 README、安装说明、贡献指南及测试文档。 | 尚未实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |
| 11-05 | 提供标准 GitHub Issue 模板和脱敏日志机制。 | 部分实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |
| 11-06 | 明确支持系统、已知问题和未验证环境。 | 尚未实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |
| 11-07 | 建立外部贡献代码审查与自动化测试规范。 | 尚未实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |
| 11-08 | 为开源发布准备合适的 LICENSE、依赖声明及第三方版权通知。 | 部分实现 | P1 | 现有模块函数; CONTRIBUTING.md; LICENSE（源码审查；非通过证据） | 稳定 Python API、文档与 Issue 模板、许可登记；标准库；无新运行依赖 | tests/，逐项补缺并运行；本轮未执行 | 核心仍与 UI 混合；不承诺已兼容 FlexMaster |

共登记 101 项。每行验收前须补测量记录与精确证据；不得批量升级完成状态。

## P0 第二组实现记录（2026-11-01，未测试）

- `runner.py`：六模块独立执行边界、固定错误码、取消透传、执行状态与时间。
- `reports.py`：独占创建、脱敏增量 JSONL、flush/fsync、最终 JSON、恢复读取 API、存储失败降级。
- `suite.py`：接入默认本地保存、Ctrl+C 保存/130、失败模块继续；`quality.py`/`routes.py`/`media.py` 增加结果保存回调。
- `tests/test_recovery.py`：新增模块错误、取消、尾部损坏、写入冲突、符号链接及刷盘失败场景，未执行。

关联第八类保存/中断、第十类故障隔离/取消需求由“尚未实现”推进为“部分实现（未测试）”；尚不能标记已实现且通过测试。完整限制见架构和测试计划的 Reliability batch。


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

逐项状态仍为部分实现；02类 DNS/TCP/TLS 代码证据新增 connectivity.py。整体进度见 CURRENT_STATUS.md。

## 基础安全第五组（2026-11-01：实现未测试）

新增 `proxydoctor/security.py`：独立 Python collect/render API，接入 suite 独立安全模块和 check 的结构化/双语终端输出。检查固定9个文件/目录的 lstat 权限、所有者和类型，不读取 shadow/gshadow 内容、不提权、不刷新包缓存、不执行任何修复。检测世界可写、同组可写、非root所有者、敏感文件世界可读，均为人工审阅提示而非漏洞确认；shadow 的同组只读本身不报风险。符号链接不跟随判断，结果未知。

更新状态只读取 apt 成功时间戳和可选 update-notifier 缓存的明确英文计数。记录缓存年龄；无缓存/无权限/本地化或不识别格式不解释为零更新。未调用 apt update/upgrade，不联网、不查询付费API。即使缓存为0也不能证明无漏洞或已完整修补。仅固定入口/父目录，不递归审计 sudoers.d/sshd_config.d；ACL、capabilities、运行态、ESM/订阅资格和完整包版本安全比对未实现。

新增 `tests/test_security.py` 九个离线场景（含权限、符号链接、错误不泄密、缓存缺失/年龄/本地化、禁止读取私密内容和非Linux降级），本轮没有执行测试。此前与本轮全部新增实现仍待回归和双Ubuntu实测。
