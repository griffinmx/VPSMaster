# 安装、更新与卸载 / Installation

需要 Linux、Python 3.10+ 和标准库 venv；Ubuntu 22.04+ 是主要目标。安装器不下载依赖、不调用 pip/sudo/系统包管理器。缺少 Python 或 venv 时明确退出，由用户自行选择系统依赖安装方式。

## ZIP 安装

从可信的 [Releases](https://github.com/griffinmx/VPSMaster/releases) 渠道取得同一构建的 ZIP 与 `SHA256SUMS.txt`。校验只能验证内容一致性，不能独立证明发布者身份。私有测试期间需访问授权。

```bash
sha256sum -c SHA256SUMS.txt
python3 -m zipfile -e VPSMaster-v1.0.0-beta.1.zip .
cd VPSMaster-v1.0.0-beta.1
python3 -I -B install.py --run
```

默认目录为 `~/.local/share/vpsmaster/1.0.0b1`。`--run` 安装后运行离线 suite；检测有发现时可能返回 1，先查看安装器和检测各自的输出。

安装器检查根目录 `MANIFEST.sha256.json`，创建不含 pip 的隔离 venv，复制 Python 包并提供 `bin/vpsmaster` 与 `bin/proxydoctor`。不要自行移动清单中的文件。

## 自定义目录与重复安装

```bash
python3 -I -B install.py --prefix "$HOME/vpsmaster-beta-test"
"$HOME/vpsmaster-beta-test/bin/vpsmaster" --version
```

必须指定尚不存在的目录；重复安装拒绝覆盖。安装失败会清理本次新建的安装目录，保留既有安装。

## 更新和卸载

更新时先核对新包校验和，安装到新的目录并验证，再切换自己使用的启动器路径。没有自动更新、旧报告迁移或自动卸载。卸载前备份报告、核对实际安装路径，然后仅删除自己确认的安装目录；不要删除整个 `~/.local/share`。

## 源码运行与兼容

```bash
bash vpsmaster.sh check --lang zh
bash proxydoctor.sh check --lang en
```

内部 Python 包与发行元数据仍名为 `proxydoctor`；现有 JSON schema、`PROXYDOCTOR_*` 环境变量保留。没有新增 `VPSMASTER_*` 环境变量别名。旧 `~/.local/share/proxydoctor/` 不自动迁移。

[使用指南](USAGE.md) · [返回首页](../../README.md)
