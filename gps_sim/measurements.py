"""Range and pseudorange measurement helpers for simulated receivers."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .coordinates import CartesianPosition

SPEED_OF_LIGHT_METERS_PER_SECOND = 299_792_458.0


@dataclass(frozen=True)
class RangeMeasurement:
    """Geometric range and clock-biased pseudorange in meters."""

    geometric_range_meters: float
    pseudorange_meters: float
    receiver_clock_bias_seconds: float

    def __post_init__(self) -> None:
        for name, value in (
            ("geometric_range_meters", self.geometric_range_meters),
            ("pseudorange_meters", self.pseudorange_meters),
            ("receiver_clock_bias_seconds", self.receiver_clock_bias_seconds),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.geometric_range_meters < 0.0:
            raise ValueError("geometric_range_meters must not be negative")


def geometric_range(
    receiver_ecef: CartesianPosition,
    satellite_ecef: CartesianPosition,
) -> float:
    """Return straight-line receiver-to-satellite distance in meters."""
    return math.dist(
        (
            receiver_ecef.x_meters,
            receiver_ecef.y_meters,
            receiver_ecef.z_meters,
        ),
        (
            satellite_ecef.x_meters,
            satellite_ecef.y_meters,
            satellite_ecef.z_meters,
        ),
    )


def calculate_pseudorange(
    receiver_ecef: CartesianPosition,
    satellite_ecef: CartesianPosition,
    receiver_clock_bias_seconds: float = 0.0,
    signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
) -> RangeMeasurement:
    """Calculate geometric range plus receiver clock-bias distance."""
    for name, value in (
        ("receiver_clock_bias_seconds", receiver_clock_bias_seconds),
        ("signal_speed_meters_per_second", signal_speed_meters_per_second),
    ):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if signal_speed_meters_per_second <= 0.0:
        raise ValueError("signal_speed_meters_per_second must be greater than zero")

    range_meters = geometric_range(receiver_ecef, satellite_ecef)
    return RangeMeasurement(
        geometric_range_meters=range_meters,
        pseudorange_meters=(
            range_meters
            + receiver_clock_bias_seconds * signal_speed_meters_per_second
        ),
        receiver_clock_bias_seconds=receiver_clock_bias_seconds,
    )


__all__ = [
    "RangeMeasurement",
    "SPEED_OF_LIGHT_METERS_PER_SECOND",
    "calculate_pseudorange",
    "geometric_range",
]
