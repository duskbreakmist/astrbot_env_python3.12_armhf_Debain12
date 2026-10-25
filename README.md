# AstrBot 4.29.3 / Python 3.12 / Debian 12 armhf

HI3798 Cortex-A7（ARMv7 hard-float）上的 AstrBot uv 环境与 FAISS 构建记录。

**2026-10-25：板上 AstrBot 已从 4.24.2 更新到 4.29.3，FAISS 从 1.13.2 更新到 1.14.3。WebUI 与 API 均确认 4.29.3；150 个发行包依赖检查通过，正式 venv 的 FAISS 测试通过，服务重启正常。** 6 个插件和 2 个 QQ 官方适配器加载完成，本次启动错误计数为 0。

[下载本次 Release](https://github.com/duskbreakmist/astrbot_env_python3.12_armhf_Debain12/releases/tag/astrbot-v4.29.3-armhf-20261025)

## 使用条件

- Debian 12 armhf、glibc 2.36，实测内核 4.4.35-s40，Cortex-A7 NEON/VFPv4。
- Python **3.12.3** runtime 放在 `/opt/python3.12-standalone`；uv venv 固定在 `/opt/py3_12`。
- `include-system-site-packages = false`。不使用系统 Python 3.11 的模块、头文件或 site-packages。
- FAISS wheel：`faiss_cpu-1.14.3-cp312-cp312-linux_armv7l.whl`，仅针对 NumPy **2.4.4** 验证。
- 系统共享运行库 BLAS/LAPACK、libstdc++、OpenMP、libgfortran 与 glibc 仍需存在。它们是 C/Fortran 共享库，不是 Python 3.11 包。此发布不是完全静态的 Linux 应用。

## 目录

```text
README.md
build/                 # chroot 准备、工具链、交叉编译、wheel 打包
patches/               # FAISS v1.14.3 的 ARM 32 位补丁
docs/
  paths-and-build.md   # 完整路径结构、恢复编译环境、换源与编译步骤
  upgrade-and-restore.md # 实际升级、备份、安装和回退
  validation.md       # 编译与实机结果、验证范围及已知边界
requirements/         # 150 个实际版本、140 项保留约束、10 项更新输入
manifests/            # 来源、SHA256、编译包、目标 ABI/系统库
scripts/              # 安装与环境/FAISS 验证
validation/           # 已脱敏实测结果
systemd/              # 服务单元示例
licenses/             # FAISS 等第三方许可证
```

## Release 附件

| 文件 | 用途 |
| --- | --- |
| `faiss_cpu-1.14.3-cp312-cp312-linux_armv7l.whl` | 自建 FAISS 二进制，核心与 callbacks 静态并入 Python 扩展 |
| `astrbot-4.29.3-armhf-upgrade-wheels.tar.gz` | **20 个 wheel**：板上升级所需 10 个，另 10 个用于补齐旧公开 venv。不是全量 150 个包的 wheelhouse |
| `py3_12-astrbot-4.29.3-armhf.tar.gz` | 从旧公开 venv 和已校验官方/自建 wheel 生成的 150 包干净恢复环境；不含业务配置、插件数据或聊天记录 |
| `astrbot-4.29.3-armhf-build-records.tar.gz` | 本仓库对应的步骤、脚本、补丁、清单及测试记录 |
| `installed-armhf-4.29.3.txt` | 150 个实测版本的固定清单；不是 150 个 wheel 的哈希锁 |
| `SHA256SUMS` | 本次全部 Release 附件的 SHA256 |

Python 本体沿用 [Python 3.12.3 runtime v1.0.0](https://github.com/duskbreakmist/python3.12_armhf_debian12/releases/tag/v1.0.0)，不重复上传或伪称更新的 CPython 维护版本。新恢复环境依赖上述固定 runtime 路径，不能随意改 venv 文件夹名。

## 新装与已有环境升级

完整命令见 [安装、升级与回退](docs/upgrade-and-restore.md)。已有板子实际使用：

```sh
# 先停服并将 venv/runtime/业务数据备份到 WSL 或容量足够的外置存储。
# BUNDLE 是已解压的本次升级 wheel 附件。
BUNDLE=/home/ray/astrbot-4.29.3-upgrade
TMPDIR="$BUNDLE/tmp" /usr/local/bin/uv pip install \
  --python /opt/py3_12/bin/python \
  --constraint "$BUNDLE/retain-candidates.constraints.txt" \
  --requirement "$BUNDLE/requirements-change-only.in" \
  --find-links "$BUNDLE/wheelhouse" --no-index --only-binary :all: \
  --no-cache --link-mode=copy
/usr/local/bin/uv pip check --python /opt/py3_12/bin/python
```

板上 `/tmp` 为 50 MiB，实际首次解压新版 WebUI 时空间不足。最终安装将 `TMPDIR` 指向有空间的任务目录；不要省略此条件。安装前先 `mkdir -p "$BUNDLE/tmp"`。

本次更新保留 140 个已有版本，升级 4 项、新增 6 项。没有用 `uv pip sync` 删除额外包，也没有调用系统 Python 3.11。

## 验证与边界

[实机报告](docs/validation.md)包含 WebUI/API、数据库完整性、依赖隔离、服务重启和 FAISS 8 组检查。没有发送对外测试消息或付费模型调用，没有宣称全部插件业务已逐项端到端验证。知识库中没有现存 FAISS 索引文件可供旧索引迁移验收。

保留旧 Python/包的已知缺项：Python 3.12.3 runtime 缺 `_lzma`；`silk-python 0.2.8` 旧安装未提供可用编码后端；PyYAML 使用纯 Python fallback。这些不是本次升级新引入的问题，本次发布没有把它们标记为已修复。需要 QQ SILK 语音功能或完整标准库时，应先另行补齐并验收。

旧 [1.0.0 Release](https://github.com/duskbreakmist/astrbot_env_python3.12_armhf_Debain12/releases/tag/1.0.0)保留为历史资产。旧 FAISS wheel 错标为 `py3-none-any` 且板上缺少其动态库；请使用新 wheel。第三方包保留自身许可证，FAISS MIT 原文同时见 `licenses/FAISS-LICENSE`。
