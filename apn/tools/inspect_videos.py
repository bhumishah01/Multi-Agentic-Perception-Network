#!/usr/bin/env python3
"""Phase 0 footage discovery for APN.

Produces contact sheets and a machine-readable report. Detection counts are a
quick HOG baseline used only for discovery; they are not ground truth.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def video_metadata(path: Path) -> tuple[cv2.VideoCapture, dict[str, Any]]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = int(capture.get(cv2.CAP_PROP_FOURCC))
    codec = "".join(chr((fourcc >> (8 * index)) & 0xFF) for index in range(4)).strip("\x00")
    return capture, {
        "file": str(path), "resolution": [width, height], "fps": round(fps, 3),
        "frame_count": frames, "duration_s": round(frames / fps, 3) if fps else None,
        "codec": codec,
    }


def read_frame(capture: cv2.VideoCapture, frame_index: int) -> np.ndarray:
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Could not read frame {frame_index}")
    return frame


def contact_sheet(frames: list[np.ndarray], labels: list[str], output: Path) -> None:
    cells = []
    for frame, label in zip(frames, labels):
        cell = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        cv2.rectangle(cell, (0, 0), (320, 25), (0, 0, 0), -1)
        cv2.putText(cell, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, .48, (255, 255, 255), 1, cv2.LINE_AA)
        cells.append(cell)
    sheet = np.vstack([np.hstack(cells[row:row + 3]) for row in range(0, 9, 3)])
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), sheet):
        raise RuntimeError(f"Could not write {output}")


def inspect(path: Path, output_dir: Path, sample_count: int) -> dict[str, Any]:
    capture, report = video_metadata(path)
    frame_count = report["frame_count"]
    indices = np.linspace(0, max(0, frame_count - 1), 9, dtype=int).tolist()
    frames = [read_frame(capture, index) for index in indices]
    labels = [f"{index / report['fps']:.1f}s | frame {index}" for index in indices]
    sheet_path = output_dir / f"{path.stem}.jpg"
    contact_sheet(frames, labels, sheet_path)

    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    detection_indices = np.linspace(0, max(0, frame_count - 1), min(sample_count, frame_count), dtype=int)
    detections: list[int] = []
    signatures: list[list[float]] = []
    for index in detection_indices:
        frame = read_frame(capture, int(index))
        scale = min(1.0, 720 / max(frame.shape[:2]))
        scan = cv2.resize(frame, None, fx=scale, fy=scale) if scale < 1 else frame
        boxes, _ = hog.detectMultiScale(scan, winStride=(8, 8), padding=(8, 8), scale=1.05)
        detections.append(len(boxes))
        hsv = cv2.cvtColor(cv2.resize(frame, (64, 36)), cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
        signatures.append(cv2.normalize(hist, hist).flatten().astype(float).tolist())
    capture.release()
    report.update({
        "contact_sheet": str(sheet_path),
        "quick_detection": {
            "method": "OpenCV HOG discovery baseline",
            "sampled_frames": len(detections),
            "frames_with_person_detection": sum(value > 0 for value in detections),
            "max_people_in_sampled_frame": max(detections, default=0),
            "mean_detections_per_sampled_frame": round(float(np.mean(detections)), 3) if detections else 0,
            "warning": "Discovery heuristic only; missed and false detections are expected.",
        },
        "scene_signature": np.mean(np.asarray(signatures), axis=0).round(6).tolist(),
    })
    return report


def add_overlap_estimates(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    estimates = []
    for left_index, left in enumerate(reports):
        for right in reports[left_index + 1:]:
            a = np.asarray(left["scene_signature"], dtype=np.float32)
            b = np.asarray(right["scene_signature"], dtype=np.float32)
            score = float(cv2.compareHist(a, b, cv2.HISTCMP_CORREL))
            estimates.append({
                "camera_a": Path(left["file"]).stem, "camera_b": Path(right["file"]).stem,
                "global_colour_histogram_similarity": round(score, 3),
                "warning": "Not proof of spatial overlap; confirm from contact sheets and recording context.",
            })
    return estimates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/inspect"))
    parser.add_argument("--samples", type=int, default=24)
    args = parser.parse_args()
    reports = [inspect(path, args.output_dir, args.samples) for path in args.videos]
    result = {"videos": reports, "pairwise_scene_estimates": add_overlap_estimates(reports)}
    for report in reports:
        report.pop("scene_signature", None)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "inspection_report.json"
    report_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nSaved report: {report_path}")


if __name__ == "__main__":
    main()
