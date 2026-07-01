"""Validated editable parameters for classroom GPS scenarios."""

from __future__ import annotations

from dataclasses import dataclass

from .coordinates import WGS84_SEMI_MAJOR_AXIS_METERS
from .ground_stations import GroundStation


DEFAULT_SATELLITE_COUNT = 4
DEFAULT_INCLINATION_DEGREES = 52.0
DEFAULT_ALTITUDE_KILOMETERS = (
    WGS84_SEMI_MAJOR_AXIS_METERS * 1.58 - WGS84_SEMI_MAJOR_AXIS_METERS
) / 1000.0
DEFAULT_RECEIVER_LATITUDE_DEGREES = 57.1497
DEFAULT_RECEIVER_LONGITUDE_DEGREES = -2.0943
DEFAULT_RECEIVER_ALTITUDE_METERS = 65.0
DEFAULT_RECEIVER_MASK_DEGREES = 5.0
DEFAULT_RECEIVER_CLOCK_BIAS_MICROSECONDS = 1.0


@dataclass(frozen=True)
class SatelliteParameters:
    """One generated satellite orbit used by the visualizer."""

    satellite_id: int
    radius_meters: float
    inclination_degrees: float
    longitude_of_ascending_node_degrees: float
    orbital_angle_degrees: float
    orbital_period_seconds: float


@dataclass(frozen=True)
class ConstellationParameters:
    """Editable constellation controls shared by UI and tests."""

    satellite_count: int = DEFAULT_SATELLITE_COUNT
    inclination_degrees: float = DEFAULT_INCLINATION_DEGREES
    altitude_kilometers: float = DEFAULT_ALTITUDE_KILOMETERS

    def __post_init__(self) -> None:
        if not 4 <= self.satellite_count <= 12:
            raise ValueError("satellite count must be between 4 and 12")
        if not 0.0 <= self.inclination_degrees <= 90.0:
            raise ValueError("inclination must be between 0 and 90 degrees")
        if not 200.0 <= self.altitude_kilometers <= 30_000.0:
            raise ValueError("altitude must be between 200 and 30000 km")

    @property
    def radius_meters(self) -> float:
        return WGS84_SEMI_MAJOR_AXIS_METERS + self.altitude_kilometers * 1000.0


@dataclass(frozen=True)
class ReceiverParameters:
    """Editable receiver inputs for station visibility and pseudorange fixes."""

    latitude_degrees: float = DEFAULT_RECEIVER_LATITUDE_DEGREES
    longitude_degrees: float = DEFAULT_RECEIVER_LONGITUDE_DEGREES
    altitude_meters: float = DEFAULT_RECEIVER_ALTITUDE_METERS
    minimum_elevation_degrees: float = DEFAULT_RECEIVER_MASK_DEGREES
    clock_bias_microseconds: float = DEFAULT_RECEIVER_CLOCK_BIAS_MICROSECONDS

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude_degrees <= 90.0:
            raise ValueError("receiver latitude must be between -90 and 90 degrees")
        if not -180.0 <= self.longitude_degrees <= 180.0:
            raise ValueError("receiver longitude must be between -180 and 180 degrees")
        if not -500.0 <= self.altitude_meters <= 20_000.0:
            raise ValueError("receiver altitude must be between -500 and 20000 meters")
        if not 0.0 <= self.minimum_elevation_degrees <= 89.0:
            raise ValueError("receiver mask must be between 0 and 89 degrees")
        if not -1000.0 <= self.clock_bias_microseconds <= 1000.0:
            raise ValueError("receiver clock bias must be between -1000 and 1000 us")

    @property
    def clock_bias_seconds(self) -> float:
        return self.clock_bias_microseconds / 1_000_000.0

    def to_ground_station(self) -> GroundStation:
        return GroundStation(
            latitude_degrees=self.latitude_degrees,
            longitude_degrees=self.longitude_degrees,
            altitude_meters=self.altitude_meters,
            minimum_elevation_degrees=self.minimum_elevation_degrees,
        )


def build_satellite_parameters(
    parameters: ConstellationParameters,
) -> tuple[SatelliteParameters, ...]:
    """Generate evenly phased classroom satellites from editable controls."""

    count = parameters.satellite_count
    radius_meters = parameters.radius_meters
    return tuple(
        SatelliteParameters(
            satellite_id=index + 1,
            radius_meters=radius_meters,
            inclination_degrees=parameters.inclination_degrees,
            longitude_of_ascending_node_degrees=(index * 360.0 / count) % 360.0,
            orbital_angle_degrees=(index * 137.5) % 360.0,
            orbital_period_seconds=114.0 * 60.0 + index * 15.0,
        )
        for index in range(count)
    )


__all__ = [
    "ConstellationParameters",
    "ReceiverParameters",
    "SatelliteParameters",
    "build_satellite_parameters",
]
