"""Headless scene data for ground-station markers and satellite links."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .coordinates import (
    CartesianPosition,
    eci_to_ecef,
    orbital_to_eci,
    station_to_ecef,
)
from .ground_stations import GroundStation
from .visibility import VisibilityResult, calculate_visibility


@dataclass(frozen=True)
class SatelliteSceneState:
    """Orbital inputs required to place one satellite in the scene."""

    satellite_id: int
    radius_meters: float
    inclination_degrees: float
    longitude_of_ascending_node_degrees: float
    orbital_angle_degrees: float


@dataclass(frozen=True)
class SatelliteLink:
    """Visibility and endpoints for one station-to-satellite link."""

    satellite_id: int
    satellite_eci: CartesianPosition
    satellite_ecef: CartesianPosition
    visibility: VisibilityResult


@dataclass(frozen=True)
class GroundStationScene:
    """Earth-fixed marker and satellite links for one named station."""

    name: str
    station: GroundStation
    station_ecef: CartesianPosition
    satellite_links: tuple[SatelliteLink, ...]


@dataclass(frozen=True)
class StationVisibilityRow:
    """One satellite row for a selected station's live visibility table."""

    satellite_id: int
    azimuth_degrees: float
    elevation_degrees: float
    range_meters: float
    is_visible: bool


def build_station_visibility_rows(
    scene: GroundStationScene,
) -> tuple[StationVisibilityRow, ...]:
    """Build table-ready visibility rows in constellation order."""
    return tuple(
        StationVisibilityRow(
            satellite_id=link.satellite_id,
            azimuth_degrees=link.visibility.azimuth_degrees,
            elevation_degrees=link.visibility.elevation_degrees,
            range_meters=link.visibility.range_meters,
            is_visible=link.visibility.is_visible,
        )
        for link in scene.satellite_links
    )


def build_ground_station_scenes(
    satellites: Iterable[SatelliteSceneState],
    stations: Mapping[str, GroundStation],
    earth_rotation_degrees: float,
) -> tuple[GroundStationScene, ...]:
    """Build deterministic marker and link data for the visualizer."""
    satellite_positions = []
    for satellite in satellites:
        eci = orbital_to_eci(
            satellite.radius_meters,
            satellite.inclination_degrees,
            satellite.longitude_of_ascending_node_degrees,
            satellite.orbital_angle_degrees,
        )
        satellite_positions.append(
            (
                satellite,
                eci,
                eci_to_ecef(eci, earth_rotation_degrees),
            )
        )

    scenes = []
    for name, station in stations.items():
        links = tuple(
            SatelliteLink(
                satellite_id=satellite.satellite_id,
                satellite_eci=eci,
                satellite_ecef=ecef,
                visibility=calculate_visibility(ecef, station),
            )
            for satellite, eci, ecef in satellite_positions
        )
        scenes.append(
            GroundStationScene(
                name=name,
                station=station,
                station_ecef=station_to_ecef(station),
                satellite_links=links,
            )
        )
    return tuple(scenes)


__all__ = [
    "GroundStationScene",
    "SatelliteLink",
    "SatelliteSceneState",
    "StationVisibilityRow",
    "build_ground_station_scenes",
    "build_station_visibility_rows",
]
