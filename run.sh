#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "오류: MacMessageMerge는 macOS에서만 실행할 수 있습니다."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "오류: Python 3가 필요합니다."
  echo "Homebrew가 있다면: brew install python"
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit('오류: Python 3.9 이상이 필요합니다.')
print(f'Python {sys.version.split()[0]}')
PY

VENV=".venv"
MARKER="$VENV/.requirements-installed"
if [ ! -x "$VENV/bin/python" ]; then
  echo "가상환경을 생성합니다..."
  python3 -m venv "$VENV"
fi

if [ ! -f "$MARKER" ] || [ requirements.txt -nt "$MARKER" ]; then
  echo "필요 패키지를 설치합니다..."
  "$VENV/bin/python" -m pip install -r requirements.txt
  touch "$MARKER"
fi

PORT="${PORT:-5001}"
export PORT
URL="http://127.0.0.1:${PORT}"

echo "MacMessageMerge를 시작합니다."
echo "$URL"
echo "종료하려면 Ctrl+C"

(sleep 1.2; open "$URL" >/dev/null 2>&1 || true) &
exec "$VENV/bin/python" app.py
