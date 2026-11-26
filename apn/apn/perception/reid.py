"""Anonymous appearance descriptors; no facial recognition."""
from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np


class HSVEmbedding:
    """Documented baseline embedding used until OSNet is benchmarked."""
    name = "hsv-histogram-baseline"

    def encode(self, crop: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        histogram = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
        return cv2.normalize(histogram, histogram).flatten().astype(np.float32)

    def save(self, crop: np.ndarray, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, self.encode(crop))
