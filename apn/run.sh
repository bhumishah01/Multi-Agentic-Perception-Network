#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON=".venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv .venv
fi
if ! "$PYTHON" -c 'import cv2,pydantic,ultralytics,fastapi,uvicorn' >/dev/null 2>&1; then
  "$PYTHON" -m pip install -r requirements.txt
fi

echo "[APN] validating core"
"$PYTHON" -m unittest discover -s tests -v

echo "[APN] discovering supermarket footage and assembling camera reels"
EXTERNAL_MEDIA="${APN_MEDIA_SOURCE:-/Volumes/One Touch/SURVELLIANCE /SUPERMARKET FINAL}"
if [[ -d "$EXTERNAL_MEDIA" ]]; then
  export APN_MEDIA_SOURCE="$EXTERNAL_MEDIA"
else
  export APN_MEDIA_SOURCE="$(pwd)/data/realistic_store_v1/videos"
  echo "[APN] external surveillance drive is unavailable — using the bundled validation pack"
fi
PREVIOUS_MEDIA=""
if [[ -f output/phase2_yolo/media_fingerprint.txt ]]; then
  PREVIOUS_MEDIA="$(tr -d '\n' < output/phase2_yolo/media_fingerprint.txt)"
fi
"$PYTHON" tools/sync_supermarket_media.py --source "$APN_MEDIA_SOURCE"
CURRENT_MEDIA="$(tr -d '\n' < data/supermarket_final/fingerprint.txt)"

if [[ ! -f output/phase2_yolo/summary.json || "$PREVIOUS_MEDIA" != "$CURRENT_MEDIA" ]]; then
  echo "[APN] new footage found — running YOLO + ByteTrack"
  mkdir -p output/phase2_yolo
  "$PYTHON" tools/run_perception.py --detector yolo --every 4 --output output/phase2_yolo
  cp data/supermarket_final/fingerprint.txt output/phase2_yolo/media_fingerprint.txt
fi

"$PYTHON" tools/render_phase2_previews.py --run output/phase2_yolo
"$PYTHON" tools/make_scenario.py
"$PYTHON" eval/run_eval.py

if [[ ! -d web2/node_modules ]]; then
  (cd web2 && npm install)
fi
(cd web2 && npm run build)
"$PYTHON" tools/attack_demo.py
"$PYTHON" tools/verify_build.py

export APN_TOKEN="${APN_TOKEN:-apn-local-demo}"
echo
echo "APN ready: http://127.0.0.1:8766"
echo "Local token: $APN_TOKEN"
echo "COMPOSED TIMELINE — clips aligned manually"
EXISTING_PID="$(lsof -tiTCP:8766 -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "$EXISTING_PID" ]] && ps -p "$EXISTING_PID" -o command= | grep -q "uvicorn apn.api.main:app"; then
  echo "[APN] replacing stale local APN process on port 8766"
  kill "$EXISTING_PID"
  sleep 1
fi
exec "$PYTHON" -m uvicorn apn.api.main:app --host 127.0.0.1 --port 8766
