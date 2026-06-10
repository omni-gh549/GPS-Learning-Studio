"""Ground-station models for receiver location and elevation-mask inputs."""

from __future__ import annotations

import math
from dataclasses import dataclass

_stations: dict[str, GroundStation] = {}


def _validate_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name must not be empty")
    return normalized_name


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


def create_station(
    name: str,
    latitude_degrees: float,
    longitude_degrees: float,
    altitude_meters: float = 0.0,
    minimum_elevation_degrees: float = 5.0,
) -> GroundStation:
    """Create and store a named ground station."""
    normalized_name = _validate_name(name)
    if normalized_name in _stations:
        raise ValueError(f"station already exists: {normalized_name}")

    station = GroundStation(
        latitude_degrees=latitude_degrees,
        longitude_degrees=longitude_degrees,
        altitude_meters=altitude_meters,
        minimum_elevation_degrees=minimum_elevation_degrees,
    )
    _stations[normalized_name] = station
    return station


def update_station(
    name: str,
    *,
    latitude_degrees: float | None = None,
    longitude_degrees: float | None = None,
    altitude_meters: float | None = None,
    minimum_elevation_degrees: float | None = None,
) -> GroundStation:
    """Replace selected fields on an existing named ground station."""
    normalized_name = _validate_name(name)
    try:
        current = _stations[normalized_name]
    except KeyError:
        raise KeyError(f"unknown station: {normalized_name}") from None

    station = GroundStation(
        latitude_degrees=(
            current.latitude_degrees
            if latitude_degrees is None
            else latitude_degrees
        ),
        longitude_degrees=(
            current.longitude_degrees
            if longitude_degrees is None
            else longitude_degrees
        ),
        altitude_meters=(
            current.altitude_meters
            if altitude_meters is None
            else altitude_meters
        ),
        minimum_elevation_degrees=(
            current.minimum_elevation_degrees
            if minimum_elevation_degrees is None
            else minimum_elevation_degrees
        ),
    )
    _stations[normalized_name] = station
    return station


def list_stations() -> dict[str, GroundStation]:
    """Return a snapshot of all stations keyed by name."""
    return dict(_stations)


def remove_station(name: str) -> GroundStation:
    """Remove and return a named ground station."""
    normalized_name = _validate_name(name)
    try:
        return _stations.pop(normalized_name)
    except KeyError:
        raise KeyError(f"unknown station: {normalized_name}") from None


__all__ = [
    "GroundStation",
    "create_station",
    "list_stations",
    "remove_station",
    "update_station",
]
