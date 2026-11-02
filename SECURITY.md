# VPSMaster Security / 安全反馈

普通检测只读：不更改SSH、防火墙、路由或系统DNS，不自动提权、安装依赖、执行修复或上传完整报告。
离线check/suite模式不发起外部探测（check的--detect-public-ip是显式联网选项）。联网目标仍会看到请求来源。
安装器会创建用户隔离目录，报告会写入本地文件；带宽必须另行允许。密钥使用既有PROXYDOCTOR_*环境变量，不保存到发行包。

不在公开Issues提交密码、Token、私钥、订阅地址或完整原始日志。发布仓库后若开启GitHub私密漏洞报告，优先使用该渠道；未开启时先请求维护者提供私密联系方式，不虚构安全邮箱。
发现凭据暴露时应在提供方轮换。脱敏不是任意文本匿名保证，分享前必须人工检查。

当前安全检查只是只读观察与人工审阅提示，既不是完整漏洞扫描，也不是生产稳定性或独立安全认证。
检查固定路径权限、SSH/端口/防火墙及更新缓存；不读取shadow/gshadow内容，不刷新apt缓存，不递归证明所有ACL/capabilities或补丁状态。
未知/权限不足/缓存缺失不等于安全。联网worker、命令有超时和取消；恢复以完整日志记录为准，SIGKILL/断电不能保证最终JSON。

Do not publish secrets or raw reports. Use private vulnerability reporting if enabled; otherwise ask for a private contact first.
Default checks do not change network/security configuration. This Beta is not an independent security certification.
