#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    summary = json.loads((args.run / "summary.json").read_text())
    print("\nAPN INTERNAL DEMONSTRATION")
    print("=" * 42)
    print(f"Timeline:       {summary['mode']} (dummy validation footage)")
    print(f"Detector:       {summary['detector']}")
    print(f"Tracker:        {summary['tracker']}")
    print(f"Embedding:      {summary['embedding']}")
    print(f"Observations:   {summary['observations']}")
    print(f"Ledger entries: {summary['ledger_messages']}")
    print(f"Ledger intact:  {'YES' if summary['ledger_intact'] else 'NO'}")
    print(f"Elapsed:        {summary['elapsed_s']} seconds")
    print("\nCAMERA RESULTS")
    for camera in summary["cameras"]:
        print(f"  {camera['camera_id']}: {camera['observations']} observations | "
              f"{camera['processing_fps']} processed FPS")
    print(f"\nStructured observations: {args.run / 'observations.json'}")
    print(f"Tamper-evident ledger:    {args.run / 'ledger.sqlite3'}")
    print(f"Visual previews:          {args.run / 'previews'}")


if __name__ == "__main__":
    main()
