# VPSMaster v1.0.0-beta.1 — Pre-release

**Beta / 公测候选，非稳定正式版。** Python版本1.0.0b1。发布标签建议v1.0.0-beta.1；GitHub应勾选Pre-release，不标记为稳定版。

## Changes / 本轮变更

- 正式品牌VPSMaster；更新CLI标题/帮助/报告/请求标识、项目介绍、中英文README、路线与安全说明。
- 新增vpsmaster命令和vpsmaster.sh；同一安装保留proxydoctor入口及源码脚本。
- 保留Python内部包、导入路径、JSON schema和PROXYDOCTOR_*环境变量，避免大规模重构。
- 新默认目录~/.local/share/vpsmaster/1.0.0b1；旧安装与报告不自动迁移。
- 不新增规划中的管理、监控、CPU/磁盘基准、代理部署或Web UI能力。

## 必须公开的边界

- 流媒体仅公开网页基础可达性，不保证解锁/登录地区权限/实际播放。
- 大陆三网测速实验性、默认关闭，完整可靠覆盖尚未完成。
- ICMP/TCP已知基线有回环成功和有限公网观察，不代表所有线路完整可用；新包以同SHA报告为准。
- BGP/地理信息受第三方准确性、来源、配额和条款限制。
- 海外VPS、ARM、公网IPv6、全新Ubuntu22 Server镜像尚未全面验证。
- Beta不代表生产稳定性或独立安全认证，当前不提供Web UI、自动代理部署或完整管理面板。
- 带宽attempted统计计划样本槽（包含自动跳过项），不是实际网络请求计数。

## 安装与验证

使用VPSMaster-v1.0.0-beta.1.zip与对应校验文件，按README离线隔离安装。
旧ProxyDoctor ZIP不能改名充当新版通过。完整回归、新SHA、最终ZIP安装/关键功能证据写入包外VPSMASTER_TEST_REPORT.md；未验证构建必须标UNVERIFIED。
升级使用新目录，保留旧报告。没有自动更新/迁移。

MIT许可，保留历史版权和第三方来源说明。尚未推送、合并或创建公开Release。
