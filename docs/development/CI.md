# Beta CI

此工作流仅workflow_dispatch手动触发，contents:read，不批准PR，不上传制品/缓存，不运行部署/加固。
checkout固定至官方v7.0.1提交3d3c42e5aac5ba805825da76410c181273ba90b1，关闭凭据持久化。
开发测试在用户venv里使用pytest、setuptools和wheel；这些不是产品运行依赖，不打入发行ZIP。

使用self-hosted Linux x64 runner标签vpsmaster-ubuntu22 / vpsmaster-ubuntu24，分别要求Python3.10/3.12。
维护者验收可临时注册已授权实验VM为ephemeral runner，完成后移除，不安装后台服务、不使用GitHub托管计费额度。
没有临时runner时手动执行会排队；不能把排队或本地测试当作远端CI通过。未来更换CI方式须单独核实费用、安全边界和凭据。
仅对受信任已审代码使用本地runner；不得把持久自托管runner直接暴露给不受信任公开PR。

CI原始系统报告不上传；只在临时runner保存并按本轮清理。公开仓库中的GitHub原生步骤日志可能公开，禁止打印主机私密信息或凭据。
Self-hosted免费政策参考：https://docs.github.com/en/billing/concepts/product-billing/github-actions ，执行时须核对当前政策。
