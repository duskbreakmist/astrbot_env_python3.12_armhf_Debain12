#!/bin/bash
# Run only after saving a stopped-service backup outside the board rootfs.
# Does not stop/restart services or manipulate business data.
set -euo pipefail
BUNDLE=${1:?Usage: install-upgrade-wheels.sh /path/to/extracted-bundle [--dry-run]}
MODE=${2:---dry-run}
[ "$MODE" = --dry-run ] || [ "$MODE" = --apply ] || exit 2
PYTHON=${PYTHON:-/opt/py3_12/bin/python}
UV=${UV:-/usr/local/bin/uv}
"$PYTHON" -B -c 'import sys; assert sys.version_info[:2] == (3,12); assert not any("python3.11" in p or "dist-packages" in p for p in sys.path)'
(cd "$BUNDLE" && sha256sum -c WHEEL-SHA256SUMS)
mkdir -p "$BUNDLE/tmp"
export TMPDIR="$BUNDLE/tmp"
ARGS=(pip install --python "$PYTHON" --constraint "$BUNDLE/retain-candidates.constraints.txt" --requirement "$BUNDLE/requirements-change-only.in" --find-links "$BUNDLE/wheelhouse" --no-index --only-binary :all: --no-cache --link-mode=copy)
[ "$MODE" != --dry-run ] || ARGS+=(--dry-run)
"$UV" "${ARGS[@]}"
[ "$MODE" != --apply ] || "$UV" pip check --python "$PYTHON"
