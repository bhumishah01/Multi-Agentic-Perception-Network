#!/usr/bin/env python3
"""Discover supermarket validation clips and build camera-specific replay reels.

The source files are never modified.  Every generated reel has a catalogue that
maps reel time back to the exact source clip and records how it was assigned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import cv2


CAMERAS = {
    "CAM-01": {"name": "Entrance & Produce"},
    "CAM-02": {"name": "Grocery Aisles", "numbers": range(1, 8), "anchor": "1"},
    "CAM-03": {"name": "Promotions & Assistance", "numbers": range(8, 11), "anchor": "8"},
    "CAM-04": {"name": "Checkout & Exit", "numbers": range(11, 13), "anchor": "12"},
}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def duration(path: Path) -> float:
    capture = cv2.VideoCapture(str(path))
    fps = float(capture.get(cv2.CAP_PROP_FPS)) or 1.0
    frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    return round(frames / fps, 3)


def signature(path: Path) -> str:
    stat = path.stat()
    return hashlib.sha256(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()[:16]


def classify(path: Path) -> tuple[str | None, str, float]:
    stem = path.stem
    upper = stem.upper()
    explicit = re.search(r"CAM[-_ ]?0?([1-4])", upper)
    if explicit:
        return f"CAM-0{explicit.group(1)}", "filename-camera-id", 1.0
    for camera_id, rule in CAMERAS.items():
        if any(stem.startswith(anchor) for anchor in rule.get("anchors", ())):
            return camera_id, "known-entrance-source", 1.0
    if stem.isdigit():
        number = int(stem)
        for camera_id, rule in CAMERAS.items():
            if number in rule.get("numbers", ()):
                return camera_id, "reviewed-sequence-map", 1.0
    return None, "needs-camera-assignment", 0.0


def write_reel(paths: list[Path], target: Path, work: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    concat = work / f"{target.stem}.concat.txt"
    concat.write_text("".join(f"file '{str(path).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for path in paths))
    temporary = target.with_suffix(".building.mp4")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(temporary)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", "-movflags", "+faststart", str(temporary)]
        subprocess.run(command, check=True)
    temporary.replace(target)


def sync(source: Path, root: Path) -> dict:
    source = source.resolve()
    if not source.is_dir():
        raise SystemExit(f"Surveillance folder not found: {source}")
    media = sorted((path for path in source.iterdir() if path.is_file() and not path.name.startswith((".", "._")) and path.suffix.lower() in VIDEO_SUFFIXES), key=lambda item: (not item.stem.isdigit(), int(item.stem) if item.stem.isdigit() else item.name.lower()))
    clips = []
    grouped: dict[str, list[Path]] = {camera_id: [] for camera_id in CAMERAS}
    for path in media:
        camera_id, method, confidence = classify(path)
        clip = {"clip_id": signature(path), "filename": path.name, "source_path": str(path), "camera_id": camera_id, "assignment_method": method, "assignment_confidence": confidence, "duration_s": duration(path), "validation_media": True, "analysis_exclusion_roi": [0, 0, 190, 64]}
        clips.append(clip)
        if camera_id:
            grouped[camera_id].append(path)
    fingerprint = hashlib.sha256("|".join(f"{item['clip_id']}:{item['camera_id']}" for item in clips).encode()).hexdigest()
    output = root / "data" / "supermarket_final"
    work = output / ".sync"
    work.mkdir(parents=True, exist_ok=True)
    old = {}
    catalog_path = output / "catalog.json"
    if catalog_path.exists():
        old = json.loads(catalog_path.read_text())
    changed = old.get("fingerprint") != fingerprint
    reels = []
    for camera_id, rule in CAMERAS.items():
        paths = grouped[camera_id]
        target = output / "reels" / f"{camera_id.lower()}.mp4"
        if paths and (changed or not target.exists()):
            write_reel(paths, target, work)
        cursor = 0.0
        segments = []
        for path in paths:
            item = next(clip for clip in clips if clip["source_path"] == str(path))
            segments.append({"clip_id": item["clip_id"], "filename": path.name, "reel_start_s": round(cursor, 3), "reel_end_s": round(cursor + item["duration_s"], 3)})
            cursor += item["duration_s"]
        reels.append({"camera_id": camera_id, "name": rule["name"], "file": str(target.relative_to(root)), "duration_s": round(cursor, 3), "clip_count": len(paths), "segments": segments})
    catalog = {"schema_version": 1, "source_directory": str(source), "fingerprint": fingerprint, "changed": changed, "discovered_files": len(clips), "assigned_files": sum(bool(item["camera_id"]) for item in clips), "unassigned_files": sum(not item["camera_id"] for item in clips), "disclosure": "Controlled surveillance validation footage; production claims require synchronized, consented deployment data.", "clips": clips, "reels": reels}
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(catalog, indent=2))
    (output / "fingerprint.txt").write_text(fingerprint + "\n")
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="/Volumes/One Touch/SURVELLIANCE /SUPERMARKET FINAL")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = sync(Path(args.source), args.root.resolve())
    print(json.dumps({key: result[key] for key in ("fingerprint", "changed", "discovered_files", "assigned_files", "unassigned_files")}, indent=2))


if __name__ == "__main__":
    main()
