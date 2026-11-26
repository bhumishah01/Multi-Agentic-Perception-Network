#!/usr/bin/env python3
"""Fit and save a pixel-to-floor homography from matching point pairs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from apn.perception.floor import FloorProjection


def pairs(value: str) -> list[list[float]]:
    return [[float(part) for part in pair.split(",")] for pair in value.split(";")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Example: --image '0,0;100,0;100,100;0,100' --floor '0,0;10,0;10,10;0,10'")
    parser.add_argument("--camera", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--floor", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    projection, residual = FloorProjection.fit(pairs(args.image), pairs(args.floor))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"camera_id": args.camera, "homography": projection.matrix.tolist(),
                                      "residual_error": residual, "approximate": False}, indent=2))
    print(json.dumps({"camera_id": args.camera, "residual_error": residual, "output": str(args.output)}))


if __name__ == "__main__":
    main()
