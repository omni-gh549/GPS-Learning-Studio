"""Iterative receiver position solver for pseudorange measurements."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from .coordinates import (
    CartesianPosition,
    LocalHorizonPosition,
    ecef_to_local_horizon,
    station_to_ecef,
)
from .ground_stations import GroundStation
from .measurements import SPEED_OF_LIGHT_METERS_PER_SECOND


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_positive(name: str, value: float) -> None:
    _require_finite(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be greater than zero")


@dataclass(frozen=True)
class PseudorangeObservation:
    """A satellite ECEF position paired with an observed pseudorange."""

    satellite_ecef: CartesianPosition
    pseudorange_meters: float

    def __post_init__(self) -> None:
        _require_finite("pseudorange_meters", self.pseudorange_meters)
        if self.pseudorange_meters <= 0.0:
            raise ValueError("pseudorange_meters must be greater than zero")


@dataclass(frozen=True)
class PositionFix:
    """Estimated receiver state and final pseudorange residuals."""

    receiver_ecef: CartesianPosition
    receiver_clock_bias_seconds: float
    residuals_meters: tuple[float, ...]
    iterations: int
    converged: bool

    def __post_init__(self) -> None:
        _require_finite(
            "receiver_clock_bias_seconds",
            self.receiver_clock_bias_seconds,
        )
        if self.iterations < 0:
            raise ValueError("iterations must not be negative")
        for index, residual in enumerate(self.residuals_meters):
            _require_finite(f"residuals_meters[{index}]", residual)


@dataclass(frozen=True)
class PositionErrorReport:
    """Residual and position-error metrics for a solved receiver fix."""

    residuals_meters: tuple[float, ...]
    max_abs_residual_meters: float
    rms_residual_meters: float
    local_error: LocalHorizonPosition
    horizontal_error_meters: float
    vertical_error_meters: float
    position_error_meters: float

    def __post_init__(self) -> None:
        for index, residual in enumerate(self.residuals_meters):
            _require_finite(f"residuals_meters[{index}]", residual)
        _require_finite("max_abs_residual_meters", self.max_abs_residual_meters)
        _require_finite("rms_residual_meters", self.rms_residual_meters)
        _require_finite("horizontal_error_meters", self.horizontal_error_meters)
        _require_finite("vertical_error_meters", self.vertical_error_meters)
        _require_finite("position_error_meters", self.position_error_meters)
        if self.max_abs_residual_meters < 0.0:
            raise ValueError("max_abs_residual_meters must not be negative")
        if self.rms_residual_meters < 0.0:
            raise ValueError("rms_residual_meters must not be negative")
        if self.horizontal_error_meters < 0.0:
            raise ValueError("horizontal_error_meters must not be negative")
        if self.position_error_meters < 0.0:
            raise ValueError("position_error_meters must not be negative")


@dataclass(frozen=True)
class DilutionOfPrecisionReport:
    """Satellite geometry quality metrics for a receiver fix."""

    satellite_count: int
    gdop: float
    pdop: float
    hdop: float
    vdop: float

    def __post_init__(self) -> None:
        if self.satellite_count < 4:
            raise ValueError("satellite_count must be at least four")
        for name in ("gdop", "pdop", "hdop", "vdop"):
            value = getattr(self, name)
            _require_finite(name, value)
            if value < 0.0:
                raise ValueError(f"{name} must not be negative")


def solve_position(
    observations: Sequence[PseudorangeObservation],
    initial_receiver_ecef: CartesianPosition | None = None,
    initial_clock_bias_seconds: float = 0.0,
    signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
    max_iterations: int = 12,
    tolerance_meters: float = 0.001,
) -> PositionFix:
    """Estimate receiver ECEF position and clock bias from pseudoranges.

    The solver uses a Gauss-Newton update on four unknowns: receiver x, y, z,
    and receiver clock bias. Four observations are required; extra observations
    are fitted in a least-squares sense.
    """
    if len(observations) < 4:
        raise ValueError("at least four pseudorange observations are required")
    _require_finite("initial_clock_bias_seconds", initial_clock_bias_seconds)
    _require_positive(
        "signal_speed_meters_per_second",
        signal_speed_meters_per_second,
    )
    if max_iterations <= 0:
        raise ValueError("max_iterations must be greater than zero")
    _require_positive("tolerance_meters", tolerance_meters)

    receiver = initial_receiver_ecef or CartesianPosition(0.0, 0.0, 0.0)
    state = [
        receiver.x_meters,
        receiver.y_meters,
        receiver.z_meters,
        initial_clock_bias_seconds,
    ]

    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        rows, residuals = _linearized_system(
            observations,
            state,
            signal_speed_meters_per_second,
        )
        delta = _solve_least_squares(rows, residuals)
        for index, value in enumerate(delta):
            state[index] += value
        iterations = iteration

        clock_delta_meters = abs(delta[3] * signal_speed_meters_per_second)
        position_delta_meters = math.sqrt(
            delta[0] * delta[0] + delta[1] * delta[1] + delta[2] * delta[2]
        )
        if max(position_delta_meters, clock_delta_meters) <= tolerance_meters:
            converged = True
            break

    final_receiver = CartesianPosition(state[0], state[1], state[2])
    final_residuals = _residuals(
        observations,
        state,
        signal_speed_meters_per_second,
    )
    return PositionFix(
        receiver_ecef=final_receiver,
        receiver_clock_bias_seconds=state[3],
        residuals_meters=final_residuals,
        iterations=iterations,
        converged=converged,
    )


def calculate_dilution_of_precision(
    observations: Sequence[PseudorangeObservation],
    receiver_ecef: CartesianPosition,
    reference_station: GroundStation,
) -> DilutionOfPrecisionReport:
    """Calculate GDOP, PDOP, HDOP, and VDOP from satellite geometry.

    DOP values are dimensionless multipliers. Lower values indicate that the
    satellites are spread across the sky in a way that better constrains the
    receiver solution. The reference station defines the local east-north-up
    frame used to split position geometry into horizontal and vertical DOP.
    """
    if len(observations) < 4:
        raise ValueError("at least four pseudorange observations are required")

    rows = _geometry_rows(observations, receiver_ecef)
    covariance = _invert_normal_matrix(rows)
    position_covariance = [row[:3] for row in covariance[:3]]
    local_covariance = _ecef_covariance_to_local_horizon(
        position_covariance,
        reference_station,
    )
    pdop = math.sqrt(_nonnegative_trace(position_covariance))
    gdop = math.sqrt(_nonnegative_trace(covariance))
    hdop = math.sqrt(
        max(0.0, local_covariance[0][0] + local_covariance[1][1])
    )
    vdop = math.sqrt(max(0.0, local_covariance[2][2]))
    return DilutionOfPrecisionReport(
        satellite_count=len(observations),
        gdop=gdop,
        pdop=pdop,
        hdop=hdop,
        vdop=vdop,
    )


def calculate_position_error(
    fix: PositionFix,
    true_receiver_ecef: CartesianPosition,
    reference_station: GroundStation,
) -> PositionErrorReport:
    """Calculate residual, horizontal, vertical, and 3D errors for a fix.

    The reference station defines the local east-north-up frame used to split
    the ECEF position error into horizontal and vertical components.
    """
    dx = fix.receiver_ecef.x_meters - true_receiver_ecef.x_meters
    dy = fix.receiver_ecef.y_meters - true_receiver_ecef.y_meters
    dz = fix.receiver_ecef.z_meters - true_receiver_ecef.z_meters
    position_error_meters = math.sqrt(dx * dx + dy * dy + dz * dz)
    local_error = _ecef_delta_to_local_horizon(
        CartesianPosition(dx, dy, dz),
        reference_station,
    )
    horizontal_error_meters = math.hypot(
        local_error.east_meters,
        local_error.north_meters,
    )
    residuals = fix.residuals_meters
    if residuals:
        max_abs_residual_meters = max(abs(residual) for residual in residuals)
        rms_residual_meters = math.sqrt(
            sum(residual * residual for residual in residuals) / len(residuals)
        )
    else:
        max_abs_residual_meters = 0.0
        rms_residual_meters = 0.0
    return PositionErrorReport(
        residuals_meters=residuals,
        max_abs_residual_meters=max_abs_residual_meters,
        rms_residual_meters=rms_residual_meters,
        local_error=local_error,
        horizontal_error_meters=horizontal_error_meters,
        vertical_error_meters=local_error.up_meters,
        position_error_meters=position_error_meters,
    )


def _linearized_system(
    observations: Sequence[PseudorangeObservation],
    state: Sequence[float],
    signal_speed_meters_per_second: float,
) -> tuple[list[list[float]], list[float]]:
    x, y, z, clock_bias_seconds = state
    rows: list[list[float]] = []
    residuals: list[float] = []
    for observation in observations:
        satellite = observation.satellite_ecef
        dx = x - satellite.x_meters
        dy = y - satellite.y_meters
        dz = z - satellite.z_meters
        range_meters = math.sqrt(dx * dx + dy * dy + dz * dz)
        if range_meters == 0.0:
            raise ValueError("receiver estimate cannot equal a satellite position")
        predicted = (
            range_meters
            + clock_bias_seconds * signal_speed_meters_per_second
        )
        residuals.append(observation.pseudorange_meters - predicted)
        rows.append(
            [
                dx / range_meters,
                dy / range_meters,
                dz / range_meters,
                signal_speed_meters_per_second,
            ]
        )
    return rows, residuals


def _residuals(
    observations: Sequence[PseudorangeObservation],
    state: Sequence[float],
    signal_speed_meters_per_second: float,
) -> tuple[float, ...]:
    _, residuals = _linearized_system(
        observations,
        state,
        signal_speed_meters_per_second,
    )
    return tuple(residuals)


def _geometry_rows(
    observations: Sequence[PseudorangeObservation],
    receiver_ecef: CartesianPosition,
) -> list[list[float]]:
    rows: list[list[float]] = []
    for observation in observations:
        satellite = observation.satellite_ecef
        dx = receiver_ecef.x_meters - satellite.x_meters
        dy = receiver_ecef.y_meters - satellite.y_meters
        dz = receiver_ecef.z_meters - satellite.z_meters
        range_meters = math.sqrt(dx * dx + dy * dy + dz * dz)
        if range_meters == 0.0:
            raise ValueError("receiver position cannot equal a satellite position")
        rows.append([dx / range_meters, dy / range_meters, dz / range_meters, 1.0])
    return rows


def _invert_normal_matrix(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    normal_matrix = [[0.0 for _ in range(4)] for _ in range(4)]
    for row in rows:
        for row_index in range(4):
            for column_index in range(4):
                normal_matrix[row_index][column_index] += (
                    row[row_index] * row[column_index]
                )
    inverse_columns = []
    for column_index in range(4):
        rhs = [0.0, 0.0, 0.0, 0.0]
        rhs[column_index] = 1.0
        inverse_columns.append(_solve_4x4([row[:] for row in normal_matrix], rhs))
    return [
        [inverse_columns[column_index][row_index] for column_index in range(4)]
        for row_index in range(4)
    ]


def _ecef_covariance_to_local_horizon(
    covariance: Sequence[Sequence[float]],
    reference_station: GroundStation,
) -> list[list[float]]:
    latitude = math.radians(reference_station.latitude_degrees)
    longitude = math.radians(reference_station.longitude_degrees)
    sin_lat = math.sin(latitude)
    cos_lat = math.cos(latitude)
    sin_lon = math.sin(longitude)
    cos_lon = math.cos(longitude)
    basis = (
        (-sin_lon, cos_lon, 0.0),
        (-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat),
        (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat),
    )
    return [
        [
            sum(
                basis[row_index][ecef_row]
                * covariance[ecef_row][ecef_column]
                * basis[column_index][ecef_column]
                for ecef_row in range(3)
                for ecef_column in range(3)
            )
            for column_index in range(3)
        ]
        for row_index in range(3)
    ]


def _nonnegative_trace(matrix: Sequence[Sequence[float]]) -> float:
    return max(0.0, sum(matrix[index][index] for index in range(len(matrix))))


def _ecef_delta_to_local_horizon(
    delta: CartesianPosition,
    reference_station: GroundStation,
) -> LocalHorizonPosition:
    origin = station_to_ecef(reference_station)
    target = CartesianPosition(
        origin.x_meters + delta.x_meters,
        origin.y_meters + delta.y_meters,
        origin.z_meters + delta.z_meters,
    )
    return ecef_to_local_horizon(target, reference_station)


def _solve_least_squares(
    rows: Sequence[Sequence[float]],
    residuals: Sequence[float],
) -> list[float]:
    normal_matrix = [[0.0 for _ in range(4)] for _ in range(4)]
    normal_rhs = [0.0 for _ in range(4)]
    for row, residual in zip(rows, residuals):
        for row_index in range(4):
            normal_rhs[row_index] += row[row_index] * residual
            for column_index in range(4):
                normal_matrix[row_index][column_index] += (
                    row[row_index] * row[column_index]
                )
    return _solve_4x4(normal_matrix, normal_rhs)


def _solve_4x4(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, rhs)]
    for pivot_index in range(4):
        pivot_row = max(
            range(pivot_index, 4),
            key=lambda row_index: abs(augmented[row_index][pivot_index]),
        )
        pivot_value = augmented[pivot_row][pivot_index]
        if abs(pivot_value) < 1e-12:
            raise ValueError("satellite geometry is singular or poorly conditioned")
        if pivot_row != pivot_index:
            augmented[pivot_index], augmented[pivot_row] = (
                augmented[pivot_row],
                augmented[pivot_index],
            )

        pivot_value = augmented[pivot_index][pivot_index]
        for column_index in range(pivot_index, 5):
            augmented[pivot_index][column_index] /= pivot_value
        for row_index in range(4):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            for column_index in range(pivot_index, 5):
                augmented[row_index][column_index] -= (
                    factor * augmented[pivot_index][column_index]
                )
    return [augmented[row_index][4] for row_index in range(4)]


__all__ = [
    "DilutionOfPrecisionReport",
    "PositionErrorReport",
    "PositionFix",
    "PseudorangeObservation",
    "calculate_dilution_of_precision",
    "calculate_position_error",
    "solve_position",
]
