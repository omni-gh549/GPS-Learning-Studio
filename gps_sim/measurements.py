"""Range and pseudorange measurement helpers for simulated receivers."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .coordinates import CartesianPosition

SPEED_OF_LIGHT_METERS_PER_SECOND = 299_792_458.0


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_signal_speed(signal_speed_meters_per_second: float) -> None:
    _require_finite(
        "signal_speed_meters_per_second",
        signal_speed_meters_per_second,
    )
    if signal_speed_meters_per_second <= 0.0:
        raise ValueError("signal_speed_meters_per_second must be greater than zero")


@dataclass(frozen=True)
class ReceiverClockBias:
    """Configurable receiver clock offset used in pseudorange simulations."""

    seconds: float = 0.0

    def __post_init__(self) -> None:
        _require_finite("seconds", self.seconds)

    @classmethod
    def from_range_error(
        cls,
        range_error_meters: float,
        signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
    ) -> "ReceiverClockBias":
        """Create a clock bias from its equivalent range error in meters."""
        _require_finite("range_error_meters", range_error_meters)
        _require_signal_speed(signal_speed_meters_per_second)
        return cls(range_error_meters / signal_speed_meters_per_second)

    def range_error_meters(
        self,
        signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
    ) -> float:
        """Return the equivalent pseudorange offset in meters."""
        _require_signal_speed(signal_speed_meters_per_second)
        return self.seconds * signal_speed_meters_per_second


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
            _require_finite(name, value)
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
    receiver_clock_bias: ReceiverClockBias | None = None,
) -> RangeMeasurement:
    """Calculate geometric range plus receiver clock-bias distance."""
    _require_finite("receiver_clock_bias_seconds", receiver_clock_bias_seconds)
    _require_signal_speed(signal_speed_meters_per_second)
    if receiver_clock_bias is not None:
        if receiver_clock_bias_seconds != 0.0:
            raise ValueError(
                "receiver_clock_bias_seconds and receiver_clock_bias cannot both be set"
            )
        receiver_clock_bias_seconds = receiver_clock_bias.seconds

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
    "ReceiverClockBias",
    "SPEED_OF_LIGHT_METERS_PER_SECOND",
    "calculate_pseudorange",
    "geometric_range",
]
