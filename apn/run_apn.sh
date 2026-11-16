#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d .venv ]; then
  echo "Preparing APN computer-vision environment..."
  python3 -m venv .venv
fi

if ! .venv/bin/python -c 'import cv2' >/dev/null 2>&1; then
  echo "Installing the local computer-vision dependency..."
  .venv/bin/python -m pip install -r requirements-cv.txt
fi

if [ ! -f output/realistic_store_v1/replay_evidence.json ]; then
  echo "Building evidence from the supplied camera footage..."
  .venv/bin/python replay_pipeline.py --every 8
fi

echo
echo "Starting APN Operational Theatre..."
echo "Keep this terminal open while using the application."
echo
exec .venv/bin/python server.py
