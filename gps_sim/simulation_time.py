"""Headless simulation-time controls for GPS Learning Studio."""

from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(frozen=True)
class SimulationClockState:
    """Current playback state for display and API callers."""

    simulation_seconds: float
    speed_multiplier: float
    is_playing: bool


class SimulationClock:
    """Advance simulation seconds from wall-clock time with playback controls."""

    def __init__(
        self,
        *,
        speed_multiplier: float = 1.0,
        is_playing: bool = True,
        wall_time_seconds: float | None = None,
    ) -> None:
        self._simulation_seconds = 0.0
        self._speed_multiplier = self._require_non_negative(
            "speed_multiplier",
            speed_multiplier,
        )
        self._is_playing = bool(is_playing)
        self._last_wall_time = self._wall_time(wall_time_seconds)

    @property
    def simulation_seconds(self) -> float:
        return self._simulation_seconds

    @property
    def speed_multiplier(self) -> float:
        return self._speed_multiplier

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def state(self, wall_time_seconds: float | None = None) -> SimulationClockState:
        self.tick(wall_time_seconds)
        return SimulationClockState(
            simulation_seconds=self._simulation_seconds,
            speed_multiplier=self._speed_multiplier,
            is_playing=self._is_playing,
        )

    def tick(self, wall_time_seconds: float | None = None) -> float:
        wall_time = self._wall_time(wall_time_seconds)
        elapsed = max(0.0, wall_time - self._last_wall_time)
        if self._is_playing:
            self._simulation_seconds += elapsed * self._speed_multiplier
        self._last_wall_time = wall_time
        return self._simulation_seconds

    def play(self, wall_time_seconds: float | None = None) -> None:
        self._last_wall_time = self._wall_time(wall_time_seconds)
        self._is_playing = True

    def pause(self, wall_time_seconds: float | None = None) -> None:
        self.tick(wall_time_seconds)
        self._is_playing = False

    def toggle(self, wall_time_seconds: float | None = None) -> bool:
        if self._is_playing:
            self.pause(wall_time_seconds)
        else:
            self.play(wall_time_seconds)
        return self._is_playing

    def step(self, seconds: float, wall_time_seconds: float | None = None) -> float:
        self.tick(wall_time_seconds)
        self._simulation_seconds += self._require_non_negative("seconds", seconds)
        return self._simulation_seconds

    def set_time(
        self,
        seconds: float,
        wall_time_seconds: float | None = None,
    ) -> None:
        self.tick(wall_time_seconds)
        self._simulation_seconds = self._require_non_negative("seconds", seconds)

    def set_speed(
        self,
        multiplier: float,
        wall_time_seconds: float | None = None,
    ) -> None:
        self.tick(wall_time_seconds)
        self._speed_multiplier = self._require_non_negative("multiplier", multiplier)

    def reset(self, wall_time_seconds: float | None = None) -> None:
        self._simulation_seconds = 0.0
        self._speed_multiplier = 1.0
        self._is_playing = True
        self._last_wall_time = self._wall_time(wall_time_seconds)

    @staticmethod
    def _wall_time(wall_time_seconds: float | None) -> float:
        return time.perf_counter() if wall_time_seconds is None else float(wall_time_seconds)

    @staticmethod
    def _require_non_negative(name: str, value: float) -> float:
        value = float(value)
        if value < 0.0:
            raise ValueError(f"{name} must be non-negative")
        return value
