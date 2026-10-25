# 编译环境、路径和完整步骤

## 实际路径结构

```text
WSL Ubuntu-24.04 (x86_64)
/home/ray/workplace/
├── debian12_rootfs/
│   ├── workroot/                  # 旧离线 rootfs；本任务不改动
│   └── workroot.tar.gz            # 恢复输入；只读
├── astrbot-faiss-armhf-1.14.3/
│   ├── debian-archive-keyring.gpg
│   ├── downloads/                # FAISS、Python、旧 venv 原始归档
│   ├── amd64/                    # 新 Debian 12 原生编译 chroot
│   │   ├── armhf/                # 下方 ARM rootfs 的 bind mount
│   │   ├── usr/local/bin/armhf-python
│   │   └── work/
│   │       ├── faiss-1.14.3/      # 已打补丁源码
│   │       ├── build-faiss-armhf/ # Ninja 中间文件
│   │       ├── toolchain-armhf.cmake
│   │       ├── build-faiss.sh
│   │       ├── package-wheel.py
│   │       ├── rebuild-and-package.sh
│   │       └── wheels/
│   ├── armhf/                    # 旧 rootfs 归档的独立副本
│   │   ├── opt/python3.12-standalone/
│   │   ├── opt/py3_12/
│   │   └── tmp/                  # 测试和公开 venv 重建区
│   ├── scripts/
│   ├── artifacts/
│   └── logs/
└── astrbot-4.29.3-upgrade/
    ├── wheelhouse/               # 20 个已校验 wheel
    ├── scripts/ logs/
    ├── private-backup/           # 私有备份，绝不发布
    ├── github-repo/              # 本仓库本地发布工作目录
    └── release-assets/           # 待发布二进制附件

HI3798 board
/opt/python3.12-standalone/        # CPython 3.12.3，不是 /usr/bin/python3
/opt/py3_12/                      # uv venv，system-site-packages=false
/home/ray/astrbot_workplace/       # 业务工作目录，不进入发布附件
/home/ray/astrbot-4.29.3-upgrade/   # 本次安装输入与记录
/home/ray/faiss-1.14.3-validation/  # 初次隔离测试
/etc/systemd/system/astrbot.service
```

## 1. 连接和确认

在 Windows 用 SSH 配置别名 `hi3798_37_10` 连接板子；在 WSL 执行构建：

```powershell
wsl -d Ubuntu-24.04 -u root
ssh hi3798_37_10 'hostname; whoami; pwd'
```

进入 WSL 后先 `hostname; whoami; pwd`。Windows SSH 别名不会自动出现在 WSL 的 SSH 配置里。本轮需要流式备份时，从 WSL 调用 Windows `ssh.exe`，避免 PowerShell 文本管道处理二进制数据。

## 2. 恢复完整编译布局

本次实际用旧 `workroot.tar.gz` 恢复 ARM rootfs，另外 debootstrap 一个干净 Debian 12 amd64 rootfs。不改原 rootfs 或旧 `/home/ray/workplace/faiss`。

宿主需要 debootstrap、curl、tar、patch、qemu-arm-static 和已启用的 qemu-arm binfmt。Debian archive keyring 从原离线 Debian rootfs 只读复制；不禁用签名验证。输入归档来源及 SHA256 见 `manifests/SOURCE-SHA256SUMS`；本地旧 rootfs SHA256 为 `804cd09824765422b08e7bc26250e73a0e0fedd22a2f7efeb88d989d5121ace1`。

仓库 `build/prepare-chroots.sh` 包含下载校验、创建目录、amd64 debootstrap、ARM 归档恢复、工具安装、bind mount、目标 Python 包装器、补丁、编译和打包的完整命令：

```sh
cd /path/to/this/repository
export ROOTFS_ARCHIVE=/home/ray/workplace/debian12_rootfs/workroot.tar.gz
export KEYRING_FILE=/home/ray/workplace/debian12_rootfs/workroot/usr/share/keyrings/debian-archive-keyring.gpg
# 必须用不存在的新目录。脚本拒绝覆盖现有构建区。
sudo -E bash build/prepare-chroots.sh /home/ray/workplace/faiss-rebuild-new
```

此脚本是按本轮已执行步骤整理的重放入口，已做语法检查；没有再次删除成功环境、从空目录完整重跑一遍。它依赖用户现有的本地 rootfs 归档，不代表该归档已公开发布。没有该归档的其他用户需要自行准备 Debian 12 armhf rootfs，并调整输入及校验，不应绕过校验去下载来源不明的镜像。

## 3. 原生交叉编译与 Python 3.12

Debian 12 amd64 内运行 GCC 12.2、CMake 3.25、Ninja、SWIG 4.1；目标为 `arm-linux-gnueabihf`，CPU 参数 `-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard`。GCC/SWIG 自身在 x86_64 执行，避免 QEMU 模拟整个编译器。

CMake 通过 `/usr/local/bin/armhf-python` 使用 `chroot /armhf /opt/py3_12/bin/python` 查询目标 ABI/NumPy；头文件为 `/armhf/opt/python3.12-standalone/include/python3.12` 和 ARM NumPy 2.4.4 的 `_core/include`。宿主 Debian Python 3.11 只负责封装已经编译好的二进制；打包类强制 CPython 3.12/ARM 标签，它的 Python 模块不会进入板上运行依赖。

完整参数见 `build/build-faiss.sh` 与工具链文件。关键选择：generic CPU、GPU/Metal/MKL/SVS/extras/tests 关闭、PIC、核心及 callbacks 静态链接、BLAS/LAPACK 动态链接到板上现有系统库、RUNPATH 为 `$ORIGIN`。

已有成功环境再次构建：

```sh
base=/home/ray/workplace/astrbot-faiss-armhf-1.14.3
mountpoint -q "$base/amd64/armhf" || mount --bind "$base/armhf" "$base/amd64/armhf"
chroot "$base/amd64" /bin/bash /work/rebuild-and-package.sh
# 输出 $base/amd64/work/wheels/faiss_cpu-1.14.3-cp312-cp312-linux_armv7l.whl
```

## 4. 补丁和打包结果

`patches/faiss-v1.14.3-armhf.patch` 已验证可干净应用到官方 v1.14.3。它按指针位宽选择 SWIGWORDSIZE32/64，并修复 IVF 训练、磁盘倒排表哨兵、反序列化上限在 32 位下的移位/截断溢出。

`build/package-wheel.py` 将发行名设为 faiss-cpu，保留版本 1.14.3，标签 `cp312-cp312-linux_armv7l`，Root-Is-Purelib=false，固定 NumPy 2.4.4，保留 MIT LICENSE。最终 wheel 3,576,619 字节；SHA256 为 `277443d76aa83b660a380a5751b7f8f348a1743856f6f4994c05f5b242648403`。

## 5. 换源

只修改新编译 chroot 的 `amd64/etc/apt/sources.list`：

```text
deb https://mirrors.aliyun.com/debian bookworm main
```

然后 `chroot "$base/amd64" apt-get update`。可替换为 Debian 官方、清华或中科大镜像，保持 Debian bookworm 和签名校验；不要混用 Ubuntu 或不同 Debian suite。编译脚本支持 `MIRROR` 环境变量。

PyPI wheel 默认元数据来自官方；网络超时时使用阿里云 `https://mirrors.aliyun.com/pypi` 下载同一文件，逐个与官方 SHA256 核对。所有发布 wheel 的来源和哈希见 manifests，不因为换源跳过校验。
