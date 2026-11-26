"""Offline deterministic perception pipeline for configured camera footage."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from apn.config import APNConfig
from apn.core import AsyncMessageBus, HashChainedLedger
from .detector import HOGDetectorTracker, YOLOByteTrackDetector
from .models import Observation, Quality
from .reid import HSVEmbedding
from .zones import ZoneResolver


class PerceptionPipeline:
    def __init__(self, config: APNConfig, root: Path, output: Path, detector: str = "yolo",
                 every_n_frames: int = 2, model_name: str = "yolo11n.pt") -> None:
        self.config = config
        self.root = root
        self.output = output
        self.detector_name = detector
        self.every_n_frames = every_n_frames
        self.model_name = model_name

    def _detector(self):
        return HOGDetectorTracker() if self.detector_name == "hog" else YOLOByteTrackDetector(self.model_name)

    @staticmethod
    def render_overlay(frame: np.ndarray, observations: list[Observation]) -> np.ndarray:
        """Render a diagnostic overlay without modifying the source video."""
        rendered = frame.copy()
        for observation in observations:
            x1, y1, x2, y2 = map(int, observation.bbox_px)
            cv2.rectangle(rendered, (x1, y1), (x2, y2), (42, 210, 190), 2)
            cv2.circle(rendered, tuple(map(int, observation.foot_px)), 4, (0, 190, 255), -1)
            cv2.putText(rendered, f"{observation.local_track_id} | {observation.zone}",
                        (x1, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .45,
                        (42, 210, 190), 1, cv2.LINE_AA)
        return rendered

    @staticmethod
    def _overlap_estimate(box: tuple[float, float, float, float], boxes: list[tuple[float, float, float, float]]) -> float:
        x1, y1, x2, y2 = box
        area = max(1.0, (x2 - x1) * (y2 - y1))
        overlaps = []
        for other in boxes:
            if other == box:
                continue
            ox1, oy1, ox2, oy2 = other
            intersection = max(0, min(x2, ox2) - max(x1, ox1)) * max(0, min(y2, oy2) - max(y1, oy1))
            overlaps.append(intersection / area)
        return min(1.0, max(overlaps, default=0.0))

    async def run(self) -> dict[str, Any]:
        self.output.mkdir(parents=True, exist_ok=True)
        # A processing run is a reproducible snapshot.  Reusing an earlier
        # ledger would mix two datasets and make audit counts misleading.
        ledger_path = self.output / "ledger.sqlite3"
        if ledger_path.exists():
            ledger_path.unlink()
        catalog_path = self.root / "data" / "supermarket_final" / "catalog.json"
        catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {"reels": []}
        reel_segments = {item["camera_id"]: item.get("segments", []) for item in catalog.get("reels", [])}
        ledger = HashChainedLedger(ledger_path)
        bus = AsyncMessageBus(ledger)
        embedder = HSVEmbedding()
        all_observations: list[Observation] = []
        camera_summaries = []
        started = time.perf_counter()
        for camera in self.config.cameras:
            detector = self._detector()
            resolver = ZoneResolver(camera.name, self.root / camera.zones_px)
            capture = cv2.VideoCapture(str(self.root / camera.file))
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            processed = detections_count = 0
            frame_index = -1
            camera_started = time.perf_counter()
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index += 1
                if frame_index % self.every_n_frames:
                    continue
                processed += 1
                detections = detector.process(frame)
                boxes = [item.bbox for item in detections]
                for detection_index, detection in enumerate(detections):
                    x1, y1, x2, y2 = detection.bbox
                    height, width = frame.shape[:2]
                    ix1, iy1 = max(0, int(x1)), max(0, int(y1))
                    ix2, iy2 = min(width, int(x2)), min(height, int(y2))
                    if ix2 <= ix1 or iy2 <= iy1:
                        continue
                    crop = frame[iy1:iy2, ix1:ix2]
                    foot = ((x1 + x2) / 2, y2)
                    evidence_key = f"{camera.id}_{frame_index:06d}_{detection.track_id}"
                    crop_path = self.output / "crops" / camera.id / f"{evidence_key}.jpg"
                    embedding_path = self.output / "embeddings" / camera.id / f"{evidence_key}.npy"
                    crop_path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(crop_path), crop)
                    embedder.save(crop, embedding_path)
                    observation = Observation(
                        camera_id=camera.id, local_track_id=detection.track_id,
                        ts_source=frame_index / fps, store_ts=camera.clock_offset_s + frame_index / fps,
                        frame_idx=frame_index, bbox_px=detection.bbox, foot_px=foot,
                        zone=resolver.resolve(foot), detector_score=detection.score,
                        embedding_ref=str(embedding_path.relative_to(self.output)),
                        crop_ref=str(crop_path.relative_to(self.output)),
                        quality=Quality(
                            blur=float(cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()),
                            occlusion_est=self._overlap_estimate(detection.bbox, boxes),
                            size_px=int(crop.shape[0] * crop.shape[1]),
                        ),
                        **self._source_reference(reel_segments.get(camera.id, []), frame_index / fps),
                    )
                    all_observations.append(observation)
                    detections_count += 1
                    await bus.publish(
                        "observation", f"camera-agent:{camera.id}", ts_source=observation.store_ts,
                        observed=observation.model_dump(mode="json"), confidence=None,
                        score=observation.detector_score,
                        evidence=(f"FRAME:{camera.id}:{frame_index}", observation.crop_ref),
                        ts_ingest=observation.store_ts,
                    )
            capture.release()
            elapsed = time.perf_counter() - camera_started
            camera_summaries.append({
                "camera_id": camera.id, "source_frames": frame_count, "processed_frames": processed,
                "observations": detections_count,
                "local_tracks": len({item.local_track_id for item in all_observations if item.camera_id == camera.id}),
                "elapsed_s": round(elapsed, 3),
                "processing_fps": round(processed / elapsed, 3) if elapsed else None,
            })
        observations_path = self.output / "observations.json"
        observations_path.write_text(json.dumps([item.model_dump(mode="json") for item in all_observations], indent=2))
        intact, broken_at = ledger.verify_chain()
        summary = {
            "mode": self.config.mode, "detector": self.detector_name,
            "tracker": "centroid" if self.detector_name == "hog" else "ByteTrack",
            "embedding": embedder.name, "position_basis": "uncalibrated_image",
            "observations": len(all_observations), "ledger_messages": len(ledger.messages()),
            "local_tracks": len({(item.camera_id, item.local_track_id) for item in all_observations}),
            "ledger_intact": intact, "ledger_broken_at": broken_at,
            "elapsed_s": round(time.perf_counter() - started, 3), "cameras": camera_summaries,
            "media_fingerprint": catalog.get("fingerprint"),
            "source_clips": catalog.get("assigned_files", len(self.config.cameras)),
            "limitations": [
                "HSV is a baseline appearance descriptor, not biometric identification.",
                "Floor coordinates, speed and heading remain null until Phase 3 calibration.",
                "Composed footage is an integration dataset, not a cross-camera accuracy benchmark.",
            ],
        }
        (self.output / "summary.json").write_text(json.dumps(summary, indent=2))
        ledger.close()
        return summary

    @staticmethod
    def _source_reference(segments: list[dict[str, Any]], reel_ts: float) -> dict[str, Any]:
        segment = next((item for item in segments if item["reel_start_s"] <= reel_ts < item["reel_end_s"]), None)
        if not segment and segments:
            segment = segments[-1]
        if not segment:
            return {}
        return {"source_clip_id": segment["clip_id"], "source_filename": segment["filename"],
                "source_clip_ts": round(max(0.0, reel_ts - segment["reel_start_s"]), 3)}


def run_pipeline(pipeline: PerceptionPipeline) -> dict[str, Any]:
    return asyncio.run(pipeline.run())
