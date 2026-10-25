#!/bin/bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cmake -S /work/faiss-1.14.3 -B /work/build-faiss-armhf -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=/work/toolchain-armhf.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  -DCMAKE_INSTALL_RPATH='$ORIGIN' \
  -DFAISS_OPT_LEVEL=generic \
  -DFAISS_ENABLE_GPU=OFF -DFAISS_ENABLE_METAL=OFF \
  -DFAISS_ENABLE_MKL=OFF -DFAISS_ENABLE_SVS=OFF \
  -DFAISS_ENABLE_PYTHON=ON -DFAISS_ENABLE_EXTRAS=OFF \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF \
  -DBLA_VENDOR=Generic \
  -DBLAS_LIBRARIES=/usr/lib/arm-linux-gnueabihf/blas/libblas.so \
  -DLAPACK_LIBRARIES=/usr/lib/arm-linux-gnueabihf/lapack/liblapack.so \
  -DPython_EXECUTABLE=/usr/local/bin/armhf-python \
  -DPython_ROOT_DIR=/armhf/opt/python3.12-standalone \
  -DPython_INCLUDE_DIR=/armhf/opt/python3.12-standalone/include/python3.12 \
  -DPython_NumPy_INCLUDE_DIR=/armhf/opt/py3_12/lib/python3.12/site-packages/numpy/_core/include
cmake --build /work/build-faiss-armhf --target swigfaiss -j6
