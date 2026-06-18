"""Iterative receiver position solver for pseudorange measurements."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from .coordinates import CartesianPosition
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
    "PositionFix",
    "PseudorangeObservation",
    "solve_position",
]
