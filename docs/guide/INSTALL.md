# 安装、更新与卸载 / Installation

需要 Linux、Python 3.10+、标准库venv与Git。主要目标为Ubuntu22.04+。安装器不下载依赖，不调用pip、sudo或系统包管理器；缺少依赖时明确退出。

## 从公开GitHub安装（推荐）

```bash
git clone https://github.com/griffinmx/VPSMaster.git
cd VPSMaster
python3 -I -B install.py --run
```

公开仓库克隆不需要GitHub登录。安装器检查根目录MANIFEST.sha256.json列出的文件与哈希，在用户目录创建不含pip的隔离环境。默认位置：`~/.local/share/vpsmaster/1.0.0b1/`。

`--run`安装后执行离线suite，不是联网all。看到Installed表示安装阶段完成；其后返回1可能表示体检发现问题或结果不完整，应分别查看输出。参数/完整性/安装失败通常返回2。不要跳过校验来解决文档与清单不一致问题。

```bash
~/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster --version
~/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster all --lang zh
~/.local/share/vpsmaster/1.0.0b1/bin/vpsmaster all --offline --lang en
```

联网默认300秒、每模块60秒。Server纯文字控制台中文需要字体支持，可以使用英文或支持中文的SSH终端。Git代理不会自动应用到所有诊断探测，下载成功不证明检测目标TCP/TLS可达。

## 新目录安装与重复安装

```bash
python3 -I -B install.py --prefix "$HOME/vpsmaster-beta-test" --run
"$HOME/vpsmaster-beta-test/bin/vpsmaster" all --lang en
```

目标必须事先不存在，重复安装拒绝覆盖，不会擅自删除旧目录。安装器会打印实际入口路径。测试首次安装时可使用独立HOME或显式prefix，不能覆盖已有安装。

## ZIP安装（仅在取得对应发行文件时）

从可信发行渠道取得同一构建ZIP和SHA256SUMS.txt；[Releases](https://github.com/griffinmx/VPSMaster/releases)中Draft只对有权限的协作者可见，不等于公开发行文件。

```bash
sha256sum -c SHA256SUMS.txt
python3 -m zipfile -e VPSMaster-v1.0.0-beta.1.zip .
cd VPSMaster-v1.0.0-beta.1
python3 -I -B install.py --run
```

GitHub main的文档可能比旧Beta.1 ZIP更新，必须核对具体构建。校验和只验证内容一致性，不能独立证明发布者身份。

## 更新、卸载与兼容

更新时使用新源码目录和新的安装prefix，验证后再切换入口；旧报告不自动迁移。卸载前备份报告并核对安装路径，只删除自己确认的安装目录，不要删除整个~/.local/share。

vpsmaster与proxydoctor命令指向同一实现；内部Python包、JSON schema和PROXYDOCTOR_*环境变量保留。旧~/.local/share/proxydoctor/不自动迁移。源码运行仍支持`bash vpsmaster.sh ...`和`bash proxydoctor.sh ...`。

[使用指南](USAGE.md) · [首页](../../README.md)
