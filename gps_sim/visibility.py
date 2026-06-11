"""Satellite look angles and line-of-sight visibility from a ground station."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .coordinates import (
    CartesianPosition,
    LocalHorizonPosition,
    ecef_to_local_horizon,
)
from .ground_stations import GroundStation


@dataclass(frozen=True)
class VisibilityResult:
    """Look angles, slant range, and elevation-mask visibility."""

    azimuth_degrees: float
    elevation_degrees: float
    range_meters: float
    is_visible: bool


def local_horizon_visibility(
    position: LocalHorizonPosition,
    minimum_elevation_degrees: float = 0.0,
) -> VisibilityResult:
    """Calculate visibility from an east-north-up target displacement."""
    if not math.isfinite(minimum_elevation_degrees):
        raise ValueError("minimum_elevation_degrees must be finite")
    if not 0.0 <= minimum_elevation_degrees <= 90.0:
        raise ValueError(
            "minimum_elevation_degrees must be between 0 and 90"
        )

    horizontal_range = math.hypot(
        position.east_meters,
        position.north_meters,
    )
    slant_range = math.hypot(horizontal_range, position.up_meters)
    if slant_range == 0.0:
        raise ValueError("target position must differ from the station position")

    if horizontal_range == 0.0:
        azimuth_degrees = 0.0
    else:
        azimuth_degrees = math.degrees(
            math.atan2(position.east_meters, position.north_meters)
        ) % 360.0
    elevation_degrees = math.degrees(
        math.atan2(position.up_meters, horizontal_range)
    )

    return VisibilityResult(
        azimuth_degrees=azimuth_degrees,
        elevation_degrees=elevation_degrees,
        range_meters=slant_range,
        is_visible=elevation_degrees >= minimum_elevation_degrees,
    )


def calculate_visibility(
    satellite_ecef: CartesianPosition,
    station: GroundStation,
) -> VisibilityResult:
    """Calculate satellite look angles and visibility from a station."""
    local_position = ecef_to_local_horizon(satellite_ecef, station)
    return local_horizon_visibility(
        local_position,
        station.minimum_elevation_degrees,
    )


__all__ = [
    "VisibilityResult",
    "calculate_visibility",
    "local_horizon_visibility",
]
