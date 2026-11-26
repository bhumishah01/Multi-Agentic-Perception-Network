#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

MODE="${1:-existing}"
PYTHON=".venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing .venv. Run ./run_apn.sh once to prepare the environment."
  exit 1
fi

echo "[1/4] Running APN internal tests"
"$PYTHON" -m unittest discover -s tests -v

if [[ "$MODE" == "yolo" ]]; then
  echo "[2/4] Running YOLO + ByteTrack on all four cameras (about 2 minutes)"
  "$PYTHON" tools/run_perception.py --detector yolo --every 4 --output output/phase2_yolo
elif [[ "$MODE" == "hog" ]]; then
  echo "[2/4] Running HOG baseline on all four cameras (about 20 seconds)"
  "$PYTHON" tools/run_perception.py --detector hog --every 8 --output output/phase2_hog
else
  echo "[2/4] Using the completed YOLO run"
  if [[ ! -f output/phase2_yolo/summary.json ]]; then
    echo "No completed run found. Starting YOLO + ByteTrack."
    "$PYTHON" tools/run_perception.py --detector yolo --every 4 --output output/phase2_yolo
  fi
fi

RUN="output/phase2_yolo"
if [[ "$MODE" == "hog" ]]; then RUN="output/phase2_hog"; fi

echo "[3/4] Generating visual perception previews"
"$PYTHON" tools/render_phase2_previews.py --run "$RUN"

echo "[4/4] Summarising verified results"
"$PYTHON" tools/summarise_internal_run.py "$RUN"

echo
echo "Done. Open $RUN/previews to inspect what the perception system saw."
