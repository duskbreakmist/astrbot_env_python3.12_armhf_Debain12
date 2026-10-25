# 安装、实际升级与回退

## 新板子从干净恢复包安装

环境要求见首页。新板需先装系统 C/Fortran 运行库；这些不是 Python 3.11 模块：

```sh
apt-get update
apt-get install -y libblas3 liblapack3 libgomp1 libstdc++6 libgfortran5
```

下载 Python runtime v1.0.0 的 `python3.12-armhf-standalone.tar.gz` 和本次 Release 的 venv 包、SHA256SUMS；分别用来源页/清单校验。**下面只用于不存在旧目录的新装位置**：

```sh
test ! -e /opt/python3.12-standalone
test ! -e /opt/py3_12
mkdir -p /opt
tar -xzf python3.12-armhf-standalone.tar.gz -C /opt
tar -xzf py3_12-astrbot-4.29.3-armhf.tar.gz -C /opt
/opt/py3_12/bin/python -B -c 'import sys,faiss,numpy; print(sys.version); print(faiss.__version__,numpy.__version__)'
/usr/local/bin/uv pip check --python /opt/py3_12/bin/python
```

如果尚未安装 uv，需要另行取得兼容 ARMv7 hard-float/内核的 uv。实测版本为 0.11.3；本发布不把 x86_64 uv 混入 ARM venv。恢复包固定 `/opt/py3_12` 和 `/opt/python3.12-standalone`，不能改名后假定绝对路径仍有效。

为实际用户建立业务工作目录后，参考 `systemd/astrbot.service.example`；配置账号、平台、模型均由使用者自行完成。恢复包没有这些私有配置。

## 本次板上实际升级顺序

1. Windows SSH 别名 `hi3798_37_10`，确认 hostname/whoami/pwd。实际主机 HI3798moe26，Python `/opt/py3_12/bin/python`，服务用户 ray，工作目录 `/home/ray/astrbot_workplace`。
2. 记录原环境：AstrBot 4.24.2、FAISS 1.13.2、NumPy 2.4.4，共 144 个包；检查 venv 禁用系统 site-packages，sys.path 没有 Python 3.11。
3. 在 WSL 下载 9 个官方 pure-Python wheel，并加入自建 FAISS wheel。逐项对照官方 SHA256；预演只变更 4 个版本、新增 6 个包。
4. 把 `/opt/py3_12`、`/opt/python3.12-standalone`、systemd 单元流式备份到 WSL；随后停服，再备份完整业务工作目录。两个压缩归档分别约 171 MB、109 MB，存储在 WSL 的 `private-backup/`，未占板上备份空间、未上传 GitHub。
5. 板上使用 `uv pip install` 指定 Python 3.12、保留约束、本地 wheelhouse、`--no-index --only-binary :all:`。首次因 `/tmp` 50 MiB 空间不足失败，尚未卸载旧包；改用任务目录 TMPDIR 后成功。
6. `uv pip check` 验证 150 包依赖兼容，确认目标 Python 导入新包和 FAISS。
7. 启动服务，检查 WebUI/API、配置迁移、数据库、插件与适配器；再重启一次，确认迁移后的环境仍正常启动。
8. 最终 150 个包与固定清单完全相同。正式环境 FAISS 8 组测试通过，WebUI/backend 均 4.29.3，服务 active/running、NRestarts=0。

## 停服备份如何流式保存到 WSL

在 WSL Python 中使用 subprocess 的二进制 stdout/stdin，不把 tar 流经过 Windows PowerShell 文本处理：

```python
from pathlib import Path
import subprocess
ssh = ['/mnt/c/Windows/System32/OpenSSH/ssh.exe',
       '-o', 'BatchMode=yes', '-o', 'UpdateHostKeys=no',
       '-o', 'User=root', 'hi3798_37_10']
backup = Path('/home/ray/workplace/astrbot-4.29.3-upgrade/private-backup')
backup.mkdir(mode=0o700, parents=True, exist_ok=True)
with (backup/'python-venv-systemd-before.tar.gz').open('wb') as out:
    subprocess.run(ssh+["tar --exclude='__pycache__' -C / -I 'gzip -1' -cf - opt/py3_12 opt/python3.12-standalone etc/systemd/system/astrbot.service"], stdout=out, check=True)
subprocess.run(ssh+['systemctl stop astrbot'], check=True)
with (backup/'astrbot-data-before.tar.gz').open('wb') as out:
    subprocess.run(ssh+["tar -C / -I 'gzip -1' -cf - home/ray/astrbot_workplace"], stdout=out, check=True)
```

实际还对两个 tar 完整读取校验并保存 SHA256。归档包含账号、配置和聊天数据，留在私有目录；发布构建区和备份区严格分开。此示例在备份后保持停服，需紧接安装/回退；若备份失败，应先恢复旧服务，不能继续变更。

## 离线预演和正式安装

将 `astrbot-4.29.3-armhf-upgrade-wheels.tar.gz` 解压到任务目录。板上已存在的 140 个包通过约束保留，20 wheel 包中的另 10 个用于旧公开 134 包基线补齐，不要求板上重复安装已满足的额外项。

```sh
BUNDLE=/home/ray/astrbot-4.29.3-upgrade
cd "$BUNDLE"
sha256sum -c WHEEL-SHA256SUMS
mkdir -p "$BUNDLE/tmp"
TMPDIR="$BUNDLE/tmp" /usr/local/bin/uv pip install \
  --python /opt/py3_12/bin/python \
  --constraint "$BUNDLE/retain-candidates.constraints.txt" \
  --requirement "$BUNDLE/requirements-change-only.in" \
  --find-links "$BUNDLE/wheelhouse" --no-index --only-binary :all: \
  --no-cache --link-mode=copy --dry-run
# 备份完成、服务停止后，使用相同命令去掉 --dry-run。
/usr/local/bin/uv pip check --python /opt/py3_12/bin/python
systemctl start astrbot
```

也可用 `bash scripts/install-upgrade-wheels.sh "$BUNDLE" --dry-run`，确认备份且停服后用 `--apply`。该脚本不替你备份/停服/启动服务；应用参数与本次已执行命令相同，脚本本身另做了语法检查。

如果从旧公开 134 包 venv 手动升级到完整 150 包快照，改用 `--requirement installed-armhf-4.29.3.txt`，仍指定本地 20 个 wheel。已有 134 包的本机二进制复用；此附件不是从空 venv 安装全部 150 包的 wheelhouse。新装优先直接用已生成的干净恢复包。

## 验收

```sh
/opt/py3_12/bin/python -B scripts/validate-environment.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /opt/py3_12/bin/python -B build/validate-faiss.py
systemctl is-active astrbot
```

环境检查脚本按本项目的服务名、工作目录和端口编写；迁移其他部署时需对应修改。它只导出版本和计数，不导出 dashboard 密码、平台 token、模型 API key 或原始业务日志。

## 回退

新版已把部分 trace 配置迁移到 SQLite；仅降级 wheel 不足以可靠回退。必须同时恢复原 venv 和业务数据快照。

本仓库 `scripts/rollback-from-wsl.py` 默认只校验两个私有归档 SHA256、成员路径及目标 hostname，不改板子：

```sh
python3 scripts/rollback-from-wsl.py \
  /home/ray/workplace/astrbot-4.29.3-upgrade/private-backup
```

只有明确需要回退时才加 `--apply`。它会停服，验证固定目录不是符号链接，清理新版 venv 和工作目录，流式恢复原 Python/venv/单元及业务数据，再启动旧服务。正式升级已经成功，本轮没有执行破坏性的回退演练；回退辅助脚本经过语法和只读预检，不把它描述为已在生产恢复过。
