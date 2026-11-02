# 当前架构 / Architecture

运行时仅依赖 Python 3.10+ 标准库。品牌 VPSMaster，内部包和导入路径仍为 `proxydoctor`。

| 层 | 代码与职责 |
| --- | --- |
| 入口 | `proxydoctor/cli.py` 参数与报告处理；安装器生成两个兼容命令 |
| 本机检测 | `checks.py`、`security.py` 等只读适配器 |
| 网络 | `quality.py`、`routes.py`、`ipquality.py`、`media.py`、`bandwidth.py` 等 |
| 展示与编排 | `console.py`、`suite.py`；部分采集函数仍同时输出终端 |
| 安装与校验 | 根目录 `install.py`、`MANIFEST.sha256.json`，隔离用户目录安装 |

部分模块提供 Python 函数，但尚未承诺完整稳定的外部管理 API，也未完全分离检测和展示。内部字段/业务结果不可机械地映射为“安全”或“解锁”。不为整理目录改动检测实现或现有 schema。

未来 API、Web UI、安全变更执行器及回滚能力见[规划](../security/ROADMAP.md)。早期架构草案保存在[历史目录](../archive/README.md)，不是当前实现承诺。
