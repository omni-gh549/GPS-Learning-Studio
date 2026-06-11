"""Coordinate conversions for satellite orbits and ground stations.

Earth-centred inertial (ECI) and Earth-centred, Earth-fixed (ECEF) positions
use meters. Local horizon coordinates use an east, north, up (ENU) frame
centred on a ground station.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .ground_stations import GroundStation

WGS84_SEMI_MAJOR_AXIS_METERS = 6_378_137.0
WGS84_FLATTENING = 1.0 / 298.257223563


@dataclass(frozen=True)
class CartesianPosition:
    """Three-dimensional position or displacement in meters."""

    x_meters: float
    y_meters: float
    z_meters: float

    def __post_init__(self) -> None:
        for name, value in (
            ("x_meters", self.x_meters),
            ("y_meters", self.y_meters),
            ("z_meters", self.z_meters),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class LocalHorizonPosition:
    """East, north, and up displacement from a ground station in meters."""

    east_meters: float
    north_meters: float
    up_meters: float

    def __post_init__(self) -> None:
        for name, value in (
            ("east_meters", self.east_meters),
            ("north_meters", self.north_meters),
            ("up_meters", self.up_meters),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")


def orbital_to_eci(
    radius_meters: float,
    inclination_degrees: float,
    longitude_of_ascending_node_degrees: float,
    orbital_angle_degrees: float,
) -> CartesianPosition:
    """Convert a circular orbit position to Earth-centred inertial coordinates."""
    for name, value in (
        ("radius_meters", radius_meters),
        ("inclination_degrees", inclination_degrees),
        (
            "longitude_of_ascending_node_degrees",
            longitude_of_ascending_node_degrees,
        ),
        ("orbital_angle_degrees", orbital_angle_degrees),
    ):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if radius_meters <= 0.0:
        raise ValueError("radius_meters must be greater than zero")

    inclination = math.radians(inclination_degrees)
    node = math.radians(longitude_of_ascending_node_degrees)
    angle = math.radians(orbital_angle_degrees)
    cos_node, sin_node = math.cos(node), math.sin(node)
    cos_angle, sin_angle = math.cos(angle), math.sin(angle)
    cos_inclination, sin_inclination = (
        math.cos(inclination),
        math.sin(inclination),
    )

    return CartesianPosition(
        radius_meters
        * (cos_node * cos_angle - sin_node * sin_angle * cos_inclination),
        radius_meters
        * (sin_node * cos_angle + cos_node * sin_angle * cos_inclination),
        radius_meters * sin_angle * sin_inclination,
    )


def eci_to_ecef(
    position: CartesianPosition,
    earth_rotation_degrees: float,
) -> CartesianPosition:
    """Rotate an inertial position into the Earth-fixed frame."""
    if not math.isfinite(earth_rotation_degrees):
        raise ValueError("earth_rotation_degrees must be finite")
    angle = math.radians(earth_rotation_degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return CartesianPosition(
        cosine * position.x_meters + sine * position.y_meters,
        -sine * position.x_meters + cosine * position.y_meters,
        position.z_meters,
    )


def ecef_to_eci(
    position: CartesianPosition,
    earth_rotation_degrees: float,
) -> CartesianPosition:
    """Rotate an Earth-fixed position into the inertial frame."""
    return eci_to_ecef(position, -earth_rotation_degrees)


def station_to_ecef(station: GroundStation) -> CartesianPosition:
    """Convert WGS84 geodetic station coordinates to Earth-fixed coordinates."""
    latitude = math.radians(station.latitude_degrees)
    longitude = math.radians(station.longitude_degrees)
    eccentricity_squared = (
        WGS84_FLATTENING * (2.0 - WGS84_FLATTENING)
    )
    prime_vertical_radius = WGS84_SEMI_MAJOR_AXIS_METERS / math.sqrt(
        1.0 - eccentricity_squared * math.sin(latitude) ** 2
    )
    radial_distance = prime_vertical_radius + station.altitude_meters

    return CartesianPosition(
        radial_distance * math.cos(latitude) * math.cos(longitude),
        radial_distance * math.cos(latitude) * math.sin(longitude),
        (
            prime_vertical_radius * (1.0 - eccentricity_squared)
            + station.altitude_meters
        )
        * math.sin(latitude),
    )


def ecef_to_local_horizon(
    position: CartesianPosition,
    station: GroundStation,
) -> LocalHorizonPosition:
    """Convert an ECEF target position to station-centred ENU coordinates."""
    origin = station_to_ecef(station)
    dx = position.x_meters - origin.x_meters
    dy = position.y_meters - origin.y_meters
    dz = position.z_meters - origin.z_meters
    latitude = math.radians(station.latitude_degrees)
    longitude = math.radians(station.longitude_degrees)
    sin_latitude, cos_latitude = math.sin(latitude), math.cos(latitude)
    sin_longitude, cos_longitude = math.sin(longitude), math.cos(longitude)

    return LocalHorizonPosition(
        -sin_longitude * dx + cos_longitude * dy,
        (
            -sin_latitude * cos_longitude * dx
            - sin_latitude * sin_longitude * dy
            + cos_latitude * dz
        ),
        (
            cos_latitude * cos_longitude * dx
            + cos_latitude * sin_longitude * dy
            + sin_latitude * dz
        ),
    )


def local_horizon_to_ecef(
    position: LocalHorizonPosition,
    station: GroundStation,
) -> CartesianPosition:
    """Convert a station-centred ENU position to Earth-fixed coordinates."""
    origin = station_to_ecef(station)
    latitude = math.radians(station.latitude_degrees)
    longitude = math.radians(station.longitude_degrees)
    sin_latitude, cos_latitude = math.sin(latitude), math.cos(latitude)
    sin_longitude, cos_longitude = math.sin(longitude), math.cos(longitude)
    east, north, up = (
        position.east_meters,
        position.north_meters,
        position.up_meters,
    )

    return CartesianPosition(
        origin.x_meters
        - sin_longitude * east
        - sin_latitude * cos_longitude * north
        + cos_latitude * cos_longitude * up,
        origin.y_meters
        + cos_longitude * east
        - sin_latitude * sin_longitude * north
        + cos_latitude * sin_longitude * up,
        origin.z_meters + cos_latitude * north + sin_latitude * up,
    )


__all__ = [
    "CartesianPosition",
    "LocalHorizonPosition",
    "WGS84_FLATTENING",
    "WGS84_SEMI_MAJOR_AXIS_METERS",
    "ecef_to_eci",
    "ecef_to_local_horizon",
    "eci_to_ecef",
    "local_horizon_to_ecef",
    "orbital_to_eci",
    "station_to_ecef",
]
