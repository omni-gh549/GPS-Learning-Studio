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
from .ground_stations import GroundStation, create_station, list_stations, update_station
from .measurements import (
    SPEED_OF_LIGHT_METERS_PER_SECOND,
    calculate_pseudorange,
)
from .positioning import (
    PseudorangeObservation,
    calculate_position_error,
    solve_position,
)
from .scenario_parameters import (
    ConstellationParameters,
    ReceiverParameters,
    SatelliteParameters,
    build_satellite_parameters,
)
from .scenarios import VersionedScenario
from .simulation_time import SimulationClock
from .visibility import VisibilityResult, calculate_visibility


@dataclass(frozen=True)
class SatelliteDisplayState:
    """Visualizer-ready propagated satellite state."""

    satellite_id: int
    radius_meters: float
    inclination_degrees: float
    longitude_of_ascending_node_degrees: float
    orbital_angle_degrees: float
    orbital_period_seconds: float
    color: str = ""

    @property
    def angular_speed_radians_per_second(self) -> float:
        return math.tau / self.orbital_period_seconds


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


@dataclass(frozen=True)
class SimulationFrame:
    """Headless state snapshot consumed by the Tkinter renderer."""

    elapsed_seconds: float
    satellites: tuple[SatelliteDisplayState, ...]
    station_scenes: tuple[GroundStationScene, ...]
    selected_station_scene: GroundStationScene | None
    accuracy_comparison: AccuracyComparisonDisplay | None
    accuracy_history: tuple[AccuracyHistoryPoint, ...]


class SimulationStateModel:
    """Mutable simulation state kept independent from any Tkinter widgets."""

    def __init__(
        self,
        *,
        satellite_colors: Iterable[str] = (),
        clock: SimulationClock | None = None,
        receiver_station_name: str = "Receiver",
    ) -> None:
        self.clock = clock or SimulationClock()
        self.receiver_station_name = receiver_station_name
        self.constellation_parameters = ConstellationParameters()
        self.receiver_parameters = ReceiverParameters()
        self.receiver_clock_bias_seconds = (
            self.receiver_parameters.clock_bias_seconds
        )
        self.selected_station_name: str | None = self.receiver_station_name
        self.earth_rotation_degrees = 0.0
        self._satellite_colors = tuple(satellite_colors)
        self.satellites = self._build_satellites(self.constellation_parameters)
        self.accuracy_history: tuple[AccuracyHistoryPoint, ...] = ()
        self.accuracy_history_station: str | None = None
        self._apply_receiver_station(self.receiver_parameters)

    def apply_scenario_parameters(
        self,
        constellation: ConstellationParameters,
        receiver: ReceiverParameters,
    ) -> None:
        self.constellation_parameters = constellation
        self.receiver_parameters = receiver
        self.receiver_clock_bias_seconds = receiver.clock_bias_seconds
        self.selected_station_name = self.receiver_station_name
        self.satellites = self._build_satellites(constellation)
        self.accuracy_history = ()
        self.accuracy_history_station = None
        self._apply_receiver_station(receiver)

    def export_scenario(self) -> VersionedScenario:
        return VersionedScenario(
            constellation=self.constellation_parameters,
            receiver=self.receiver_parameters,
            simulation_time_seconds=self.clock.simulation_seconds,
            orbital_speed_multiplier=self.clock.speed_multiplier,
        )

    def load_scenario(
        self,
        scenario: VersionedScenario,
        wall_time_seconds: float | None = None,
    ) -> None:
        self.apply_scenario_parameters(scenario.constellation, scenario.receiver)
        self.clock.set_time(scenario.simulation_time_seconds, wall_time_seconds)
        self.clock.set_speed(scenario.orbital_speed_multiplier, wall_time_seconds)

    def selected_station_scene(self) -> GroundStationScene | None:
        frame = self.build_frame(update_accuracy_history=False)
        return frame.selected_station_scene

    def build_frame(
        self,
        *,
        update_accuracy_history: bool = True,
    ) -> SimulationFrame:
        elapsed = self.clock.state().simulation_seconds
        station_scenes = build_ground_station_scenes(
            satellite_scene_states(self.satellites, elapsed),
            list_stations(),
            self.earth_rotation_degrees,
        )
        selected_station_scene = self._resolve_selected_station(station_scenes)
        comparison = None
        if selected_station_scene is not None:
            comparison = build_accuracy_comparison_display(
                selected_station_scene,
                receiver_clock_bias_seconds=self.receiver_clock_bias_seconds,
            )
            if update_accuracy_history:
                if self.accuracy_history_station != selected_station_scene.name:
                    self.accuracy_history = ()
                    self.accuracy_history_station = selected_station_scene.name
                self.accuracy_history = append_accuracy_history_point(
                    self.accuracy_history,
                    elapsed_seconds=elapsed,
                    comparison=comparison,
                )
        return SimulationFrame(
            elapsed_seconds=elapsed,
            satellites=self.satellites,
            station_scenes=station_scenes,
            selected_station_scene=selected_station_scene,
            accuracy_comparison=comparison,
            accuracy_history=self.accuracy_history,
        )

    def get_simulation_time(self) -> float:
        return self.clock.state().simulation_seconds

    def play(self) -> None:
        self.clock.play()

    def pause(self) -> None:
        self.clock.pause()

    def toggle_playback(self) -> bool:
        return self.clock.toggle()

    def step(self, seconds: float) -> None:
        self.clock.step(seconds)

    def set_simulation_time(self, seconds: float) -> None:
        self.clock.set_time(seconds)

    def set_orbit_speed(self, multiplier: float) -> None:
        self.clock.set_speed(multiplier)

    def tick(self, wall_time_seconds: float | None = None) -> float:
        return self.clock.tick(wall_time_seconds)

    def advance_earth_rotation(self, radians_delta: float) -> None:
        self.earth_rotation_degrees = (
            self.earth_rotation_degrees + math.degrees(radians_delta)
        ) % 360.0

    def reset(self, wall_time_seconds: float | None = None) -> None:
        self.clock.reset(wall_time_seconds)
        self.earth_rotation_degrees = 0.0
        self.selected_station_name = self.receiver_station_name
        self.accuracy_history = ()
        self.accuracy_history_station = None

    def satellite_data(self) -> list[dict[str, float | int]]:
        elapsed = self.clock.state().simulation_seconds
        return list(satellite_telemetry(self.satellites, elapsed))

    def select_station(self, station_name: str) -> None:
        self.selected_station_name = station_name
        if self.accuracy_history_station != station_name:
            self.accuracy_history = ()
            self.accuracy_history_station = None

    def _build_satellites(
        self,
        parameters: ConstellationParameters,
    ) -> tuple[SatelliteDisplayState, ...]:
        return build_satellite_display_states(
            build_satellite_parameters(parameters),
            self._satellite_colors,
        )

    def _resolve_selected_station(
        self,
        station_scenes: tuple[GroundStationScene, ...],
    ) -> GroundStationScene | None:
        if not station_scenes:
            self.selected_station_name = None
            return None
        station_names = {scene.name for scene in station_scenes}
        if self.selected_station_name not in station_names:
            self.selected_station_name = station_scenes[0].name
        return next(
            scene for scene in station_scenes if scene.name == self.selected_station_name
        )

    def _apply_receiver_station(self, receiver: ReceiverParameters) -> None:
        station_kwargs = {
            "latitude_degrees": receiver.latitude_degrees,
            "longitude_degrees": receiver.longitude_degrees,
            "altitude_meters": receiver.altitude_meters,
            "minimum_elevation_degrees": receiver.minimum_elevation_degrees,
        }
        if self.receiver_station_name in list_stations():
            update_station(self.receiver_station_name, **station_kwargs)
        else:
            create_station(self.receiver_station_name, **station_kwargs)


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def build_satellite_display_states(
    satellite_parameters: Iterable[SatelliteParameters],
    colors: Iterable[str] = (),
) -> tuple[SatelliteDisplayState, ...]:
    """Convert generated satellite parameters into propagated display states."""
    palette = tuple(colors)
    states = []
    for index, satellite in enumerate(satellite_parameters):
        color = palette[index % len(palette)] if palette else ""
        states.append(
            SatelliteDisplayState(
                satellite_id=int(satellite.satellite_id),
                radius_meters=float(satellite.radius_meters),
                inclination_degrees=float(satellite.inclination_degrees),
                longitude_of_ascending_node_degrees=float(
                    satellite.longitude_of_ascending_node_degrees
                ),
                orbital_angle_degrees=float(satellite.orbital_angle_degrees),
                orbital_period_seconds=float(satellite.orbital_period_seconds),
                color=color,
            )
        )
    return tuple(states)


def satellite_telemetry(
    satellites: Iterable[SatelliteDisplayState],
    elapsed_seconds: float,
) -> tuple[dict[str, float | int], ...]:
    """Return public telemetry dictionaries for propagated satellite states."""
    return tuple(
        {
            "id": satellite.satellite_id,
            "inclination_degrees": round(satellite.inclination_degrees, 2),
            "longitude_of_ascending_node_degrees": round(
                satellite.longitude_of_ascending_node_degrees,
                2,
            ),
            "orbital_angle_degrees": round(
                (
                    satellite.orbital_angle_degrees
                    + math.degrees(
                        elapsed_seconds
                        * satellite.angular_speed_radians_per_second
                    )
                )
                % 360.0,
                2,
            ),
        }
        for satellite in satellites
    )


def satellite_scene_states(
    satellites: Iterable[SatelliteDisplayState],
    elapsed_seconds: float,
) -> tuple[SatelliteSceneState, ...]:
    """Build scene states after propagating orbital angles by elapsed time."""
    return tuple(
        SatelliteSceneState(
            satellite_id=satellite.satellite_id,
            radius_meters=satellite.radius_meters,
            inclination_degrees=satellite.inclination_degrees,
            longitude_of_ascending_node_degrees=(
                satellite.longitude_of_ascending_node_degrees
            ),
            orbital_angle_degrees=(
                satellite.orbital_angle_degrees
                + math.degrees(
                    elapsed_seconds
                    * satellite.angular_speed_radians_per_second
                )
            ),
        )
        for satellite in satellites
    )


def display_position(
    position: CartesianPosition,
    scale: float,
) -> tuple[float, float, float]:
    """Convert an ECI/ECEF vector into the visualizer's normalized axes."""
    magnitude = math.sqrt(
        position.x_meters ** 2
        + position.y_meters ** 2
        + position.z_meters ** 2
    )
    if magnitude == 0.0:
        raise ValueError("position magnitude must be greater than zero")
    return (
        position.x_meters / magnitude * scale,
        position.z_meters / magnitude * scale,
        position.y_meters / magnitude * scale,
    )


def satellite_orbit_display_point(
    satellite: SatelliteDisplayState,
    orbital_angle_degrees: float,
    scale: float,
) -> tuple[float, float, float]:
    """Return one display-space point along a satellite's circular orbit."""
    position = orbital_to_eci(
        satellite.radius_meters,
        satellite.inclination_degrees,
        satellite.longitude_of_ascending_node_degrees,
        orbital_angle_degrees,
    )
    return display_position(position, scale)


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
    "SatelliteDisplayState",
    "SatelliteLink",
    "SatelliteSceneState",
    "SimulationFrame",
    "SimulationStateModel",
    "StationVisibilityRow",
    "append_accuracy_history_point",
    "build_satellite_display_states",
    "build_accuracy_comparison_display",
    "build_receiver_measurement_links",
    "build_receiver_position_fix_display",
    "build_ground_station_scenes",
    "build_station_visibility_rows",
    "display_position",
    "satellite_orbit_display_point",
    "satellite_scene_states",
    "satellite_telemetry",
]
