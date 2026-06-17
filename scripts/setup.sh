#!/usr/bin/env bash
# One-shot setup for VibeVoice Studio (macOS / Linux).
#
#   ./scripts/setup.sh
#
# Creates a virtual environment, installs the app dependencies and the real
# VibeVoice model package, and generates placeholder preview voices.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"

echo "==> Using $($PYTHON --version)"
case "$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" in
  3.10|3.11) ;;
  *) echo "    (note: Python 3.10 or 3.11 is recommended for the model package)";;
esac

echo "==> Creating virtual environment in .venv"
$PYTHON -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
pip install -q --upgrade pip

echo "==> Installing app dependencies"
pip install -r requirements.txt

echo "==> Installing the VibeVoice model package (community fork)"
pip install "vibevoice @ git+https://github.com/vibevoice-community/VibeVoice"

echo "==> Creating placeholder preview voices"
python scripts/make_demo_voices.py || true

cat <<'DONE'

✅ Setup complete.

Next:
  source .venv/bin/activate
  python app.py          # then open the printed http://127.0.0.1:7860

The first real generation downloads the VibeVoice-1.5B weights (~3GB) from
HuggingFace. Uncheck "Preview mode" in the UI to use the real, voice-cloned model.
DONE
