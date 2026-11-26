#!/usr/bin/env python3
"""Render one diagnostic preview per camera from Phase 2 JSON observations."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apn.config import load_config
from apn.perception.models import Observation
from apn.perception.pipeline import PerceptionPipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("output/phase2_yolo"))
    parser.add_argument("--config", type=Path, default=Path("config/cameras.yaml"))
    args = parser.parse_args()
    observations = [Observation.model_validate(item) for item in json.loads((args.run / "observations.json").read_text())]
    by_camera_frame: dict[str, dict[int, list[Observation]]] = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        by_camera_frame[observation.camera_id][observation.frame_idx].append(observation)
    config = load_config(args.config)
    preview_dir = args.run / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for camera in config.cameras:
        frame_groups = by_camera_frame[camera.id]
        if not frame_groups:
            print(f"{camera.id}: no observations")
            continue
        frame_index = max(frame_groups, key=lambda index: (len(frame_groups[index]), -index))
        capture = cv2.VideoCapture(str(PROJECT_ROOT / camera.file))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        capture.release()
        if not ok:
            raise RuntimeError(f"Could not read {camera.id} frame {frame_index}")
        rendered = PerceptionPipeline.render_overlay(frame, frame_groups[frame_index])
        cv2.rectangle(rendered, (0, 0), (rendered.shape[1], 42), (8, 12, 18), -1)
        cv2.putText(rendered, f"{camera.id} | {camera.name} | frame {frame_index} | COMPOSED TIMELINE",
                    (14, 27), cv2.FONT_HERSHEY_SIMPLEX, .65, (42, 210, 190), 2, cv2.LINE_AA)
        output = preview_dir / f"{camera.id.lower()}_preview.jpg"
        cv2.imwrite(str(output), rendered)
        print(f"{camera.id}: {output}")


if __name__ == "__main__":
    main()
