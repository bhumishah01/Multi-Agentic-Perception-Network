from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Quality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blur: float = Field(ge=0)
    occlusion_est: float = Field(ge=0, le=1)
    size_px: int = Field(ge=0)


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    camera_id: str
    local_track_id: str
    ts_source: float = Field(ge=0)
    store_ts: float = Field(ge=0)
    frame_idx: int = Field(ge=0)
    bbox_px: tuple[float, float, float, float]
    foot_px: tuple[float, float]
    foot_floor: tuple[float, float] | None = None
    zone: str
    velocity_floor: tuple[float, float] | None = None
    heading_deg: float | None = None
    detector_score: float
    embedding_ref: str
    crop_ref: str
    quality: Quality
    position_basis: str = "uncalibrated_image"
    source_clip_id: str | None = None
    source_filename: str | None = None
    source_clip_ts: float | None = None
