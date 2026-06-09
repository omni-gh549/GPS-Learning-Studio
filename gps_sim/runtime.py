"""Internal connection between public simulator modules and the active UI."""

from __future__ import annotations

from typing import Protocol


class Visualizer(Protocol):
    satellites: list[object]

    def reset(self) -> None: ...

    def satellite_data(self) -> list[dict[str, float | int]]: ...

    def set_earth_speed(self, multiplier: float) -> None: ...

    def set_orbit_speed(self, multiplier: float) -> None: ...


_visualizer: Visualizer | None = None


def bind_visualizer(visualizer: Visualizer) -> None:
    global _visualizer
    _visualizer = visualizer


def get_visualizer() -> Visualizer:
    if _visualizer is None:
        raise RuntimeError(
            "The simulator API is not connected. Run this code inside GPS Learning Studio."
        )
    return _visualizer
