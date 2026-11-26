from __future__ import annotations

import json
from pathlib import Path
import cv2
import numpy as np


class FloorProjection:
    def __init__(self, matrix: np.ndarray | None, *, approximate: bool = False) -> None:
        self.matrix = matrix
        self.approximate = approximate or matrix is None

    @classmethod
    def load(cls, path: Path) -> "FloorProjection":
        if not path.exists():
            return cls(None, approximate=True)
        data = json.loads(path.read_text())
        return cls(np.asarray(data["homography"], dtype=np.float64), approximate=bool(data.get("approximate", False)))

    @classmethod
    def fit(cls, image_points: list[list[float]], floor_points: list[list[float]]) -> tuple["FloorProjection", float]:
        if len(image_points) < 4 or len(image_points) != len(floor_points):
            raise ValueError("at least four matching point pairs are required")
        source = np.asarray(image_points, dtype=np.float32)
        target = np.asarray(floor_points, dtype=np.float32)
        matrix, _ = cv2.findHomography(source, target, method=0)
        if matrix is None:
            raise ValueError("homography could not be estimated")
        projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
        residual = float(np.sqrt(np.mean(np.sum((projected - target) ** 2, axis=1))))
        return cls(matrix), residual

    def project(self, point: tuple[float, float], frame_size: tuple[int, int] | None = None) -> tuple[float, float]:
        if self.matrix is None:
            if not frame_size:
                raise ValueError("frame size required for approximate projection")
            width, height = frame_size
            return point[0] / width, point[1] / height
        source = np.asarray([[point]], dtype=np.float32)
        result = cv2.perspectiveTransform(source, self.matrix)[0, 0]
        return float(result[0]), float(result[1])
