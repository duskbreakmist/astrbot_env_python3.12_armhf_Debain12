#!/bin/bash
set -euo pipefail
# Run inside the prepared Debian 12 amd64 chroot, with /armhf bind-mounted.
test "$(dpkg --print-architecture)" = amd64
test -f /armhf/opt/python3.12-standalone/include/python3.12/Python.h
bash /work/build-faiss.sh
arm-linux-gnueabihf-strip --strip-unneeded /work/build-faiss-armhf/faiss/python/_swigfaiss.so
cd /work/build-faiss-armhf/faiss/python
python3 /work/package-wheel.py bdist_wheel --dist-dir /work/wheels
