#!/bin/bash
# Recreate the exact recovered build layout in a NEW WSL workspace.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Run as root inside WSL'; exit 1; }
BASE=${1:?Usage: prepare-chroots.sh /absolute/NEW/workspace}
case "$BASE" in /*) ;; *) echo 'BASE must be absolute'; exit 1;; esac
[ ! -e "$BASE" ] || { echo 'Refusing to overwrite an existing workspace'; exit 1; }
ROOTFS_ARCHIVE=${ROOTFS_ARCHIVE:-/home/ray/workplace/debian12_rootfs/workroot.tar.gz}
KEYRING_FILE=${KEYRING_FILE:-/home/ray/workplace/debian12_rootfs/workroot/usr/share/keyrings/debian-archive-keyring.gpg}
MIRROR=${MIRROR:-https://mirrors.aliyun.com/debian}
REPO=$(cd "$(dirname "$0")/.." && pwd)
command -v debootstrap >/dev/null; command -v curl >/dev/null
[ -f "$ROOTFS_ARCHIVE" ]; [ -f "$KEYRING_FILE" ]; [ -f /usr/bin/qemu-arm-static ]
[ -e /proc/sys/fs/binfmt_misc/qemu-arm ] || { echo 'Enable qemu-arm binfmt first'; exit 1; }
mkdir -p "$BASE"/{amd64,armhf,downloads,logs,artifacts,scripts}
cp "$KEYRING_FILE" "$BASE/debian-archive-keyring.gpg"
fetch() {
  local name=$1 url=$2 digest=$3
  curl -fL --retry 3 --connect-timeout 20 -o "$BASE/downloads/$name" "$url"
  printf '%s  %s\n' "$digest" "$BASE/downloads/$name" | sha256sum -c -
}
fetch faiss-v1.14.3.tar.gz https://codeload.github.com/facebookresearch/faiss/tar.gz/refs/tags/v1.14.3 7f3c4ed9aec3bd7524382862f5fcbd4d8984e2a8979ff3bdb2c0bcea5144149e
fetch python3.12-armhf-standalone.tar.gz https://github.com/duskbreakmist/python3.12_armhf_debian12/releases/download/v1.0.0/python3.12-armhf-standalone.tar.gz 2c05fadc0d069fcb1784c591f82dbf25a4c0636c70be795539d6689eef2407c2
fetch py3_12.tar.gz https://github.com/duskbreakmist/astrbot_env_python3.12_armhf_Debain12/releases/download/1.0.0/py3_12.tar.gz 79a9fcf0a6280e32959a9230108aff0ed5b7f71ecd447daecdca5a27d8b49fa9
printf '%s  %s\n' 804cd09824765422b08e7bc26250e73a0e0fedd22a2f7efeb88d989d5121ace1 "$ROOTFS_ARCHIVE" | sha256sum -c -
debootstrap --arch=amd64 --variant=minbase --keyring="$BASE/debian-archive-keyring.gpg" bookworm "$BASE/amd64" "$MIRROR"
# Restore a COPY. Never extract into the original SDK/offline-rootfs directory.
tar -xzf "$ROOTFS_ARCHIVE" -C "$BASE/armhf" --strip-components=1
mkdir -p "$BASE/armhf/opt"
tar -xzf "$BASE/downloads/python3.12-armhf-standalone.tar.gz" -C "$BASE/armhf/opt"
tar -xzf "$BASE/downloads/py3_12.tar.gz" -C "$BASE/armhf/opt"
cp /usr/bin/qemu-arm-static "$BASE/armhf/usr/bin/"
printf 'deb %s bookworm main\n' "$MIRROR" > "$BASE/amd64/etc/apt/sources.list"
printf 'Acquire::ForceIPv4 "true";\nAcquire::Retries "2";\n' > "$BASE/amd64/etc/apt/apt.conf.d/99-faiss-build-network"
for root in "$BASE/amd64" "$BASE/armhf"; do
 printf '#!/bin/sh\nexit 101\n' > "$root/usr/sbin/policy-rc.d"
 chmod +x "$root/usr/sbin/policy-rc.d"
done
chroot "$BASE/amd64" dpkg --add-architecture armhf
chroot "$BASE/amd64" apt-get update
chroot "$BASE/amd64" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf cmake ninja-build swig \
  python3-dev python3-setuptools python3-wheel pkg-config patchelf \
  libblas-dev:armhf liblapack-dev:armhf libgomp1:armhf libatomic1:armhf
mkdir -p "$BASE/armhf/tmp/faiss-debs"
cp "$BASE"/amd64/var/cache/apt/archives/*_armhf.deb "$BASE/armhf/tmp/faiss-debs/"
chroot "$BASE/armhf" /bin/sh -c 'dpkg -i /tmp/faiss-debs/*.deb'
mkdir -p "$BASE/amd64/armhf" "$BASE/amd64/work/faiss-1.14.3" "$BASE/amd64/usr/local/bin"
mount --bind "$BASE/armhf" "$BASE/amd64/armhf"
cat > "$BASE/amd64/usr/local/bin/armhf-python" <<'EOF'
#!/bin/sh
exec /usr/sbin/chroot /armhf /usr/bin/env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /opt/py3_12/bin/python -B "$@"
EOF
chmod +x "$BASE/amd64/usr/local/bin/armhf-python"
tar -xzf "$BASE/downloads/faiss-v1.14.3.tar.gz" -C "$BASE/amd64/work/faiss-1.14.3" --strip-components=1
patch -d "$BASE/amd64/work/faiss-1.14.3" -p1 < "$REPO/patches/faiss-v1.14.3-armhf.patch"
cp "$REPO/build/toolchain-armhf.cmake" "$BASE/amd64/work/"
cp "$REPO/build/"{build-faiss.sh,package-wheel.py,rebuild-and-package.sh} "$BASE/amd64/work/"
chroot "$BASE/amd64" /bin/bash /work/rebuild-and-package.sh 2>&1 | tee "$BASE/logs/build-and-package.log"
cp "$BASE"/amd64/work/wheels/*.whl "$BASE/artifacts/"
chroot "$BASE/amd64" dpkg-query -W > "$BASE/artifacts/build-packages.tsv"
printf 'Built wheel in %s/artifacts\n' "$BASE"
