"""Headless scene data for ground-station markers and satellite links."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping

from .coordinates import (
    CartesianPosition,
    eci_to_ecef,
    orbital_to_eci,
    station_to_ecef,
)
from .errors import MeasurementErrorModel, classroom_error_model
from .ground_stations import GroundStation
from .measurements import (
    SPEED_OF_LIGHT_METERS_PER_SECOND,
    calculate_pseudorange,
)
from .positioning import (
    PseudorangeObservation,
    calculate_position_error,
    solve_position,
)
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


@dataclass(frozen=True)
class ReceiverMeasurementLink:
    """Display-ready pseudorange measurement between receiver and satellite."""

    satellite_id: int
    satellite_ecef: CartesianPosition
    geometric_range_meters: float
    pseudorange_meters: float
    receiver_clock_bias_seconds: float
    is_visible: bool


@dataclass(frozen=True)
class ReceiverPositionFixDisplay:
    """Table-ready true and estimated receiver fix details."""

    true_receiver_ecef: CartesianPosition
    estimated_receiver_ecef: CartesianPosition | None
    true_clock_bias_seconds: float
    estimated_clock_bias_seconds: float | None
    residuals_meters: tuple[float, ...]
    max_abs_residual_meters: float | None
    rms_residual_meters: float | None
    horizontal_error_meters: float | None
    vertical_error_meters: float | None
    position_error_meters: float | None
    converged: bool
    diagnostic: str | None = None


@dataclass(frozen=True)
class AccuracyComparisonDisplay:
    """Before/after receiver fixes for a repeatable accuracy experiment."""

    baseline: ReceiverPositionFixDisplay
    with_errors: ReceiverPositionFixDisplay
    error_model_seed: int
    total_pseudorange_error_meters: float


@dataclass(frozen=True)
class AccuracyHistoryPoint:
    """One sampled point for the visualizer's position-error history plot."""

    elapsed_seconds: float
    baseline_position_error_meters: float | None
    error_position_error_meters: float | None

    def __post_init__(self) -> None:
        _require_finite("elapsed_seconds", self.elapsed_seconds)
        if self.elapsed_seconds < 0.0:
            raise ValueError("elapsed_seconds must not be negative")
        if self.baseline_position_error_meters is not None:
            _require_finite(
                "baseline_position_error_meters",
                self.baseline_position_error_meters,
            )
            if self.baseline_position_error_meters < 0.0:
                raise ValueError("baseline_position_error_meters must not be negative")
        if self.error_position_error_meters is not None:
            _require_finite(
                "error_position_error_meters",
                self.error_position_error_meters,
            )
            if self.error_position_error_meters < 0.0:
                raise ValueError("error_position_error_meters must not be negative")


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


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


def build_receiver_measurement_links(
    scene: GroundStationScene,
    receiver_clock_bias_seconds: float = 0.000_001,
    signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
) -> tuple[ReceiverMeasurementLink, ...]:
    """Build pseudorange measurement links from receiver to each satellite."""
    measurement_links = []
    for link in scene.satellite_links:
        reading = calculate_pseudorange(
            scene.station_ecef,
            link.satellite_ecef,
            receiver_clock_bias_seconds=receiver_clock_bias_seconds,
            signal_speed_meters_per_second=signal_speed_meters_per_second,
        )
        measurement_links.append(
            ReceiverMeasurementLink(
                satellite_id=link.satellite_id,
                satellite_ecef=link.satellite_ecef,
                geometric_range_meters=reading.geometric_range_meters,
                pseudorange_meters=reading.pseudorange_meters,
                receiver_clock_bias_seconds=reading.receiver_clock_bias_seconds,
                is_visible=link.visibility.is_visible,
            )
        )
    return tuple(measurement_links)


def build_receiver_position_fix_display(
    scene: GroundStationScene,
    receiver_clock_bias_seconds: float = 0.000_001,
    signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
    error_model: MeasurementErrorModel | None = None,
) -> ReceiverPositionFixDisplay:
    """Build display-ready receiver true/estimated state from scene links."""
    observations = []
    for link in scene.satellite_links:
        reading = calculate_pseudorange(
            scene.station_ecef,
            link.satellite_ecef,
            receiver_clock_bias_seconds=receiver_clock_bias_seconds,
            signal_speed_meters_per_second=signal_speed_meters_per_second,
        )
        pseudorange_meters = reading.pseudorange_meters
        if error_model is not None:
            pseudorange_meters = error_model.apply_to_pseudorange(
                pseudorange_meters,
                measurement_key=f"{scene.name}-G{link.satellite_id}",
            )
        observations.append(
            PseudorangeObservation(
                satellite_ecef=link.satellite_ecef,
                pseudorange_meters=pseudorange_meters,
            )
        )

    try:
        fix = solve_position(
            observations,
            initial_receiver_ecef=scene.station_ecef,
            signal_speed_meters_per_second=signal_speed_meters_per_second,
        )
    except ValueError as error:
        return ReceiverPositionFixDisplay(
            true_receiver_ecef=scene.station_ecef,
            estimated_receiver_ecef=None,
            true_clock_bias_seconds=receiver_clock_bias_seconds,
            estimated_clock_bias_seconds=None,
            residuals_meters=(),
            max_abs_residual_meters=None,
            rms_residual_meters=None,
            horizontal_error_meters=None,
            vertical_error_meters=None,
            position_error_meters=None,
            converged=False,
            diagnostic=str(error),
        )

    error_report = calculate_position_error(
        fix,
        true_receiver_ecef=scene.station_ecef,
        reference_station=scene.station,
    )
    return ReceiverPositionFixDisplay(
        true_receiver_ecef=scene.station_ecef,
        estimated_receiver_ecef=fix.receiver_ecef,
        true_clock_bias_seconds=receiver_clock_bias_seconds,
        estimated_clock_bias_seconds=fix.receiver_clock_bias_seconds,
        residuals_meters=error_report.residuals_meters,
        max_abs_residual_meters=error_report.max_abs_residual_meters,
        rms_residual_meters=error_report.rms_residual_meters,
        horizontal_error_meters=error_report.horizontal_error_meters,
        vertical_error_meters=error_report.vertical_error_meters,
        position_error_meters=error_report.position_error_meters,
        converged=fix.converged,
    )


def build_accuracy_comparison_display(
    scene: GroundStationScene,
    receiver_clock_bias_seconds: float = 0.000_001,
    error_model: MeasurementErrorModel | None = None,
    signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
) -> AccuracyComparisonDisplay:
    """Compare a clean position fix with one using a deterministic error model."""
    model = error_model or classroom_error_model(seed=42)
    baseline = build_receiver_position_fix_display(
        scene,
        receiver_clock_bias_seconds=receiver_clock_bias_seconds,
        signal_speed_meters_per_second=signal_speed_meters_per_second,
    )
    with_errors = build_receiver_position_fix_display(
        scene,
        receiver_clock_bias_seconds=receiver_clock_bias_seconds,
        signal_speed_meters_per_second=signal_speed_meters_per_second,
        error_model=model,
    )
    total_pseudorange_error_meters = sum(
        model.sample(f"{scene.name}-G{link.satellite_id}").total_meters
        for link in scene.satellite_links
    )
    return AccuracyComparisonDisplay(
        baseline=baseline,
        with_errors=with_errors,
        error_model_seed=model.seed,
        total_pseudorange_error_meters=total_pseudorange_error_meters,
    )


def append_accuracy_history_point(
    history: tuple[AccuracyHistoryPoint, ...],
    elapsed_seconds: float,
    comparison: AccuracyComparisonDisplay,
    max_points: int = 80,
) -> tuple[AccuracyHistoryPoint, ...]:
    """Return a bounded time series with the latest comparison sample appended."""
    if max_points <= 0:
        raise ValueError("max_points must be greater than zero")
    point = AccuracyHistoryPoint(
        elapsed_seconds=elapsed_seconds,
        baseline_position_error_meters=comparison.baseline.position_error_meters,
        error_position_error_meters=comparison.with_errors.position_error_meters,
    )
    return (history + (point,))[-max_points:]


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
    "AccuracyComparisonDisplay",
    "AccuracyHistoryPoint",
    "ReceiverMeasurementLink",
    "ReceiverPositionFixDisplay",
    "SatelliteLink",
    "SatelliteSceneState",
    "StationVisibilityRow",
    "append_accuracy_history_point",
    "build_accuracy_comparison_display",
    "build_receiver_measurement_links",
    "build_receiver_position_fix_display",
    "build_ground_station_scenes",
    "build_station_visibility_rows",
]
