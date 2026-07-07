#!/usr/bin/env bash
# setup.sh -- one-shot environment bootstrap for the Deepfake Defense & Forensics Toolkit.
#
# Creates a Python virtualenv, installs dependencies, and (if Node.js is
# available) installs the Node evidence-bundle verifier's dev dependencies
# (there are none today, but this keeps the hook in place as the toolkit grows).
#
# Usage:
#   ./scripts/setup.sh [--dev]
#     --dev    also install requirements-dev.txt (flake8, bandit, pytest, coverage)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DEV=false
for arg in "$@"; do
  if [[ "$arg" == "--dev" ]]; then
    DEV=true
  fi
done

echo "==> Setting up Python virtual environment (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python3 -m pip install --upgrade pip -q

if [[ "$DEV" == true ]]; then
  echo "==> Installing requirements-dev.txt"
  pip install -q -r requirements-dev.txt
else
  echo "==> Installing requirements.txt"
  pip install -q -r requirements.txt
fi

if command -v node >/dev/null 2>&1; then
  echo "==> Node.js found ($(node --version)) -- evidence bundle verifier is ready to use"
  echo "    (zero external deps; run: node tools/node-evidence-verifier/verify_bundle.js <bundle.zip>)"
else
  echo "==> Node.js not found -- tools/node-evidence-verifier/ requires Node 18+ if you want to use it"
fi

echo ""
echo "Setup complete. Activate the environment with:"
echo "  source .venv/bin/activate"
echo ""
echo "Then try:"
echo "  make demo"
