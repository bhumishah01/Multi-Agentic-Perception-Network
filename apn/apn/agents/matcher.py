from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from apn.agents.handoff import HandoffPolicy


class TrackMatcher:
    """Ranks every track in a target camera; scores are decision cues, not probabilities."""

    def __init__(self, observations: list[dict], embedding_root: Path, policy: HandoffPolicy) -> None:
        self.root, self.policy = embedding_root, policy
        self.groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in observations:
            self.groups[(row["camera_id"], row["local_track_id"])].append(row)
        for rows in self.groups.values():
            rows.sort(key=lambda row: row["store_ts"])

    def embedding(self, key: tuple[str, str]) -> np.ndarray:
        vectors = [np.load(self.root / row["embedding_ref"]) for row in self.groups[key]]
        return np.mean(vectors, axis=0)

    @staticmethod
    def _cosine(left: np.ndarray, right: np.ndarray) -> float:
        raw = float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right) + 1e-9))
        return max(0.0, min(1.0, raw))

    def rank(self, source: tuple[str, str], target_camera: str, max_transit_s: float = 25.0,
             min_reverse_s: float = -5.0) -> list[dict]:
        source_rows = self.groups[source]
        source_embedding, source_end = self.embedding(source), source_rows[-1]["store_ts"]
        candidates = []
        for key, rows in self.groups.items():
            if key[0] != target_camera:
                continue
            gap = rows[0]["store_ts"] - source_end
            # Composed clips can overlap slightly; large reverse-time jumps are excluded.
            if gap < min_reverse_s or gap > max_transit_s:
                continue
            appearance = self._cosine(source_embedding, self.embedding(key))
            temporal = math.exp(-((max(0.0, gap) / 7.0) ** 2))
            source_x = source_rows[-1]["foot_px"][0] / 1280.0
            target_x = rows[0]["foot_px"][0] / 1280.0
            spatial = max(0.0, 1.0 - abs(source_x - target_x))
            components = {"appearance": appearance, "temporal": temporal, "spatial": spatial,
                          "topology": 1.0, "exclusivity": 1.0}
            raw = sum(self.policy.weights[name] * value for name, value in components.items())
            candidates.append({"track": key, "components": components, "raw_score": raw,
                               "gap_s": gap, "observations": len(rows)})
        candidates.sort(key=lambda item: item["raw_score"], reverse=True)
        for index, candidate in enumerate(candidates):
            runner_up = candidates[index + 1]["raw_score"] if index + 1 < len(candidates) else 0.0
            candidate["decision"] = self.policy.decide(candidate["components"], runner_up)
        return candidates
