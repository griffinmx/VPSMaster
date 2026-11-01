# Security / 安全反馈

Do not post vulnerabilities containing passwords, subscription URLs, API keys,
SSH keys or full diagnostic reports to public issues. If this repository is
published with GitHub private vulnerability reporting enabled, use that channel.
Otherwise request a private contact without publishing exploit details or secrets.
This source snapshot does not yet have a public repository or security mailbox.

Rotate any exposed credential at its provider. Report files hide IP addresses by
default, but redaction does not guarantee removal of all identifying information.
Review files before sharing. Native diagnostics do not upload reports or modify
SSH/firewall settings. The default suite contacts external test/data/media
services, which see the request source. `check` and `suite --offline` do not.
Keys are accepted through local environment variables; the product never asks
for them on a public web form. Future deployment/repair features require a
separate review and SSH rollback safeguards.

中文：不要公开提交密码、密钥、订阅地址或完整诊断报告。仓库发布并开启私密漏洞报告后
优先使用该渠道；未配置前先询问私密联系方式，不公开敏感细节。报告脱敏不是匿名保证，
分享前需检查。当前原生检测不修改 SSH/防火墙，不上传报告；联网模式的服务会看到请求来源。
