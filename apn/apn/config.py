"""Validated APN configuration models (Phase 0)."""
from __future__ import annotations

from datetime import datetime
from json import loads
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CameraEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    side: Literal["left", "right", "top", "bottom"]
    leads_to: str


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^CAM-\d{2}$")
    name: str
    file: Path
    clock_offset_s: float = 0.0
    zones_px: Path
    homography: Path
    neighbours: list[str]
    edges: list[CameraEdge]


class APNConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["SYNC", "COMPOSED"]
    store_clock_start: datetime
    cameras: list[CameraConfig] = Field(min_length=1)
    floorplan: Path

    @model_validator(mode="after")
    def validate_topology(self) -> "APNConfig":
        ids = [camera.id for camera in self.cameras]
        if len(ids) != len(set(ids)):
            raise ValueError("camera ids must be unique")
        known = set(ids)
        for camera in self.cameras:
            if not set(camera.neighbours) <= known:
                raise ValueError(f"{camera.id} has an unknown neighbour")
            if any(edge.leads_to not in camera.neighbours for edge in camera.edges):
                raise ValueError(f"{camera.id} edge must lead to a configured neighbour")
        return self


def load_config(path: str | Path) -> APNConfig:
    """Load JSON-compatible YAML without adding a Phase 0 YAML dependency."""
    return APNConfig.model_validate(loads(Path(path).read_text()))
