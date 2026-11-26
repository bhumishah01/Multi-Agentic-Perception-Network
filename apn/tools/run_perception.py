#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apn.config import load_config
from apn.perception.pipeline import PerceptionPipeline, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/cameras.yaml"))
    parser.add_argument("--detector", choices=("yolo", "hog"), default="yolo")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--every", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path("output") / f"phase2_{args.detector}"
    pipeline = PerceptionPipeline(load_config(args.config), Path.cwd(), output,
                                  detector=args.detector, every_n_frames=args.every, model_name=args.model)
    print(json.dumps(run_pipeline(pipeline), indent=2))


if __name__ == "__main__":
    main()
