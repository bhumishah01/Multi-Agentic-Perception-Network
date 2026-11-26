"""Selectable person detector and tracker adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    track_id: str
    bbox: tuple[float, float, float, float]
    score: float


class DetectorTracker(Protocol):
    name: str
    def process(self, frame: np.ndarray) -> list[Detection]: ...


class CentroidAssociator:
    def __init__(self, max_distance: float = 100, max_missing: int = 8) -> None:
        self.max_distance = max_distance
        self.max_missing = max_missing
        self.next_id = 1
        self.tracks: dict[int, tuple[np.ndarray, int]] = {}

    def assign(self, boxes: list[tuple[float, float, float, float]]) -> list[int]:
        centres = [np.array([(x1 + x2) / 2, (y1 + y2) / 2]) for x1, y1, x2, y2 in boxes]
        result = [-1] * len(boxes)
        unused = set(self.tracks)
        candidates = []
        for box_index, centre in enumerate(centres):
            for track_id in unused:
                candidates.append((float(np.linalg.norm(centre - self.tracks[track_id][0])), box_index, track_id))
        assigned_boxes: set[int] = set()
        for distance, box_index, track_id in sorted(candidates):
            if distance > self.max_distance or box_index in assigned_boxes or track_id not in unused:
                continue
            result[box_index] = track_id
            assigned_boxes.add(box_index)
            unused.remove(track_id)
        for box_index, centre in enumerate(centres):
            if result[box_index] < 0:
                result[box_index] = self.next_id
                self.next_id += 1
        updated = {track_id: (centres[index], 0) for index, track_id in enumerate(result)}
        for track_id in unused:
            centre, missing = self.tracks[track_id]
            if missing + 1 <= self.max_missing:
                updated[track_id] = (centre, missing + 1)
        self.tracks = updated
        return result


class HOGDetectorTracker:
    name = "hog+centroid"

    def __init__(self) -> None:
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.associator = CentroidAssociator()

    def process(self, frame: np.ndarray) -> list[Detection]:
        boxes, weights = self.hog.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
        xyxy = [(float(x), float(y), float(x + w), float(y + h)) for x, y, w, h in boxes]
        ids = self.associator.assign(xyxy)
        return [Detection(f"T-{track_id:04d}", box, float(weight)) for track_id, box, weight in zip(ids, xyxy, weights)]


class YOLOByteTrackDetector:
    name = "yolo+bytetrack"

    def __init__(self, model_name: str = "yolo11n.pt", confidence: float = .35, imgsz: int = 960) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install requirements-perception.txt to use YOLO") from exc
        self.model = YOLO(model_name)
        self.confidence = confidence
        self.imgsz = imgsz

    def process(self, frame: np.ndarray) -> list[Detection]:
        result = self.model.track(
            frame, persist=True, classes=[0], conf=self.confidence, imgsz=self.imgsz,
            tracker="bytetrack.yaml", verbose=False,
        )[0]
        if result.boxes is None or result.boxes.id is None:
            return []
        boxes = result.boxes.xyxy.cpu().numpy()
        scores = result.boxes.conf.cpu().numpy()
        ids = result.boxes.id.int().cpu().numpy()
        return [Detection(f"T-{int(track_id):04d}", tuple(map(float, box)), float(score))
                for track_id, box, score in zip(ids, boxes, scores)]
