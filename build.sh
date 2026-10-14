#!/usr/bin/env bash
# Build Swiz13 on Linux.
#   ./build.sh            fast build: reuses the shipped glyph blend (build/blend.pkl), takes seconds
#   ./build.sh --full     rebuild everything from the donor fonts (blend step: ~10-15 min)
#   SPECIMENS=1 ./build.sh   also render the specimen / comparison PNGs
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null; then
  echo "error: $PY not found. Install Python 3.10+ (e.g. 'sudo apt install python3 python3-venv')." >&2; exit 1
fi
"$PY" - <<'PYEOF' || { echo "error: Python 3.10 or newer is required." >&2; exit 1; }
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
PYEOF

if [ ! -d .venv ]; then
  echo "==> creating virtual environment (.venv)"
  "$PY" -m venv .venv || { echo "error: 'python3 -m venv' failed. On Debian/Ubuntu: sudo apt install python3-venv" >&2; exit 1; }
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if ! python -c "import fontTools, shapely, cv2, skimage, scipy, PIL, numpy, brotli" 2>/dev/null; then
  echo "==> installing Python dependencies"
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r requirements.txt
fi

ARGS=()
if [ "${1:-}" = "--full" ]; then
  echo "==> full rebuild: discarding the cached blend (this takes 10-15 minutes)"
  rm -f build/blend.pkl build/blend-raw.pkl
else
  ARGS+=(--skip-blend)
fi
[ "${SPECIMENS:-0}" = "1" ] || ARGS+=(--no-specimens)

python scripts/make.py "${ARGS[@]}"
python -m unittest discover -s tests 2>&1 | tail -3
echo
echo "Built: fonts/Swiz13-Regular.ttf  and  fonts/Swiz13-Regular.woff2"
echo "Next:  ./install.sh"
