"""Controllable source-time clock used by deterministic replays."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReplayClock:
    duration_s: float
    position_s: float = 0.0
    speed: float = 1.0
    playing: bool = False

    def play(self) -> None:
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def seek(self, position_s: float) -> None:
        self.position_s = min(self.duration_s, max(0.0, float(position_s)))

    def set_speed(self, speed: float) -> None:
        if not 0.1 <= speed <= 16:
            raise ValueError("replay speed must be between 0.1 and 16")
        self.speed = float(speed)

    def advance(self, real_delta_s: float) -> float:
        if self.playing:
            self.seek(self.position_s + max(0.0, real_delta_s) * self.speed)
            if self.position_s >= self.duration_s:
                self.playing = False
        return self.position_s
