"""Ground-station models for receiver location and elevation-mask inputs."""

from __future__ import annotations

import math
from dataclasses import dataclass


def _validate_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class GroundStation:
    """Geodetic inputs for a stationary GPS receiver."""

    latitude_degrees: float
    longitude_degrees: float
    altitude_meters: float = 0.0
    minimum_elevation_degrees: float = 5.0

    def __post_init__(self) -> None:
        values = (
            ("latitude_degrees", self.latitude_degrees),
            ("longitude_degrees", self.longitude_degrees),
            ("altitude_meters", self.altitude_meters),
            ("minimum_elevation_degrees", self.minimum_elevation_degrees),
        )
        for name, value in values:
            _validate_finite(name, value)

        if not -90.0 <= self.latitude_degrees <= 90.0:
            raise ValueError("latitude_degrees must be between -90 and 90")
        if not -180.0 <= self.longitude_degrees <= 180.0:
            raise ValueError("longitude_degrees must be between -180 and 180")
        if not 0.0 <= self.minimum_elevation_degrees <= 90.0:
            raise ValueError(
                "minimum_elevation_degrees must be between 0 and 90"
            )


__all__ = ["GroundStation"]
