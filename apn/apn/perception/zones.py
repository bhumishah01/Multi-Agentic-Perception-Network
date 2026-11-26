from __future__ import annotations

import json
from pathlib import Path
import cv2
import numpy as np


class ZoneResolver:
    def __init__(self, fallback_zone: str, polygon_file: Path | None = None) -> None:
        self.fallback_zone = fallback_zone
        self.polygons: list[tuple[str, np.ndarray]] = []
        if polygon_file and polygon_file.exists():
            data = json.loads(polygon_file.read_text())
            self.polygons = [(item["name"], np.asarray(item["points"], dtype=np.float32)) for item in data["zones"]]

    def resolve(self, point: tuple[float, float]) -> str:
        for name, polygon in self.polygons:
            if cv2.pointPolygonTest(polygon, point, False) >= 0:
                return name
        return self.fallback_zone
