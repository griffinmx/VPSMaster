# 开发测试 / Testing

从仓库根目录创建独立开发环境；开发依赖不属于产品运行依赖。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'pytest>=8,<10' 'setuptools>=77,<100' 'wheel>=0.45,<1'
.venv/bin/python -B -m pytest -q
.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
```

Windows 使用 `.venv/Scripts/python.exe`。测试避免访问真实第三方服务，使用 Mock/本地服务模拟 DNS/API 异常、超时、中断、报告和安装失败。Windows 的符号链接权限限制可造成明确 skip，不能计为通过。

## 发行验收

1. 源码和文档变化后重建 manifest 和独立 ZIP，不覆盖旧验收包。
2. 验证 ZIP SHA256、清单、许可证、链接、敏感信息和全部自动化测试。
3. Ubuntu 22.04 Desktop / 24.04 Server 受控虚拟机先保存快照，从最终 ZIP 安装至全新目录。
4. 检查隔离、双入口、重复安装拒绝、篡改拒绝、离线/联网功能、报告恢复、取消与系统配置前后一致。
5. 原始失败日志和私密环境证据留在维护者本地工作区；只公开脱敏结论。新包不可沿用旧 SHA 或旧 CI 成绩。

当前环境范围不包括已全面验证的海外 VPS、ARM、公网 IPv6 或全新 Ubuntu 22.04 Server 镜像。详见[限制](../release/KNOWN_LIMITATIONS.md)和[CI](CI.md)。
