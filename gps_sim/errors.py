"""Deterministic GPS measurement error models for classroom experiments."""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass

from .measurements import SPEED_OF_LIGHT_METERS_PER_SECOND


ERROR_SOURCE_NAMES = (
    "satellite_clock",
    "receiver_clock",
    "ionospheric_delay",
    "tropospheric_delay",
    "multipath",
    "measurement_noise",
)


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


def _stable_seed(seed: int, measurement_key: str, source_name: str) -> int:
    payload = f"{seed}|{measurement_key}|{source_name}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass(frozen=True)
class ErrorSourceModel:
    """One named pseudorange error source in meters."""

    name: str
    bias_meters: float = 0.0
    standard_deviation_meters: float = 0.0
    enabled: bool = True
    scale: float = 1.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        _require_finite("bias_meters", self.bias_meters)
        _require_finite("standard_deviation_meters", self.standard_deviation_meters)
        _require_finite("scale", self.scale)
        if self.standard_deviation_meters < 0.0:
            raise ValueError("standard_deviation_meters must not be negative")
        if self.scale < 0.0:
            raise ValueError("scale must not be negative")

    def sample(self, seed: int, measurement_key: str = "") -> "ErrorContribution":
        """Return this source's deterministic contribution for one measurement."""
        if not self.enabled:
            return ErrorContribution(self.name, 0.0)
        offset = self.bias_meters
        if self.standard_deviation_meters:
            rng = random.Random(_stable_seed(seed, measurement_key, self.name))
            offset += rng.gauss(0.0, self.standard_deviation_meters)
        return ErrorContribution(self.name, offset * self.scale)

    def with_enabled(self, enabled: bool) -> "ErrorSourceModel":
        """Return a copy with this source enabled or disabled."""
        return ErrorSourceModel(
            name=self.name,
            bias_meters=self.bias_meters,
            standard_deviation_meters=self.standard_deviation_meters,
            enabled=enabled,
            scale=self.scale,
        )

    def with_scale(self, scale: float) -> "ErrorSourceModel":
        """Return a copy with this source scaled by a non-negative multiplier."""
        return ErrorSourceModel(
            name=self.name,
            bias_meters=self.bias_meters,
            standard_deviation_meters=self.standard_deviation_meters,
            enabled=self.enabled,
            scale=scale,
        )


@dataclass(frozen=True)
class ErrorContribution:
    """A sampled pseudorange offset from one source."""

    source_name: str
    offset_meters: float

    def __post_init__(self) -> None:
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        _require_finite("offset_meters", self.offset_meters)


@dataclass(frozen=True)
class MeasurementError:
    """All sampled error contributions for a single pseudorange."""

    contributions: tuple[ErrorContribution, ...]

    def __post_init__(self) -> None:
        names = [contribution.source_name for contribution in self.contributions]
        if len(names) != len(set(names)):
            raise ValueError("contributions must use unique source names")

    @property
    def total_meters(self) -> float:
        """Return the summed pseudorange offset in meters."""
        return sum(contribution.offset_meters for contribution in self.contributions)

    def by_source(self) -> dict[str, float]:
        """Return contribution offsets keyed by source name."""
        return {
            contribution.source_name: contribution.offset_meters
            for contribution in self.contributions
        }

    def apply_to_pseudorange(self, pseudorange_meters: float) -> float:
        """Add the total modeled error to a pseudorange value."""
        _require_finite("pseudorange_meters", pseudorange_meters)
        return pseudorange_meters + self.total_meters


@dataclass(frozen=True)
class MeasurementErrorModel:
    """Seeded collection of GPS pseudorange error source models."""

    seed: int
    satellite_clock: ErrorSourceModel
    receiver_clock: ErrorSourceModel
    ionospheric_delay: ErrorSourceModel
    tropospheric_delay: ErrorSourceModel
    multipath: ErrorSourceModel
    measurement_noise: ErrorSourceModel

    def __post_init__(self) -> None:
        expected = ERROR_SOURCE_NAMES
        actual = tuple(source.name for source in self.sources)
        if actual != expected:
            raise ValueError("MeasurementErrorModel sources must use standard names")

    @property
    def sources(self) -> tuple[ErrorSourceModel, ...]:
        """Return source models in a stable teaching order."""
        return (
            self.satellite_clock,
            self.receiver_clock,
            self.ionospheric_delay,
            self.tropospheric_delay,
            self.multipath,
            self.measurement_noise,
        )

    def sample(self, measurement_key: str = "") -> MeasurementError:
        """Sample all sources deterministically for one measurement key."""
        return MeasurementError(
            tuple(source.sample(self.seed, measurement_key) for source in self.sources)
        )

    def apply_to_pseudorange(
        self,
        pseudorange_meters: float,
        measurement_key: str = "",
    ) -> float:
        """Sample this model and add its total error to a pseudorange."""
        return self.sample(measurement_key).apply_to_pseudorange(pseudorange_meters)

    def source(self, source_name: str) -> ErrorSourceModel:
        """Return one source model by standard name."""
        for source in self.sources:
            if source.name == source_name:
                return source
        raise ValueError(f"unknown error source: {source_name}")

    def with_source_settings(
        self,
        source_name: str,
        *,
        enabled: bool | None = None,
        scale: float | None = None,
    ) -> "MeasurementErrorModel":
        """Return a copy with one source enabled, disabled, or scaled."""
        updated_sources = []
        found = False
        for source in self.sources:
            if source.name != source_name:
                updated_sources.append(source)
                continue
            found = True
            updated = source
            if enabled is not None:
                updated = updated.with_enabled(enabled)
            if scale is not None:
                updated = updated.with_scale(scale)
            updated_sources.append(updated)
        if not found:
            raise ValueError(f"unknown error source: {source_name}")
        return MeasurementErrorModel(
            seed=self.seed,
            satellite_clock=updated_sources[0],
            receiver_clock=updated_sources[1],
            ionospheric_delay=updated_sources[2],
            tropospheric_delay=updated_sources[3],
            multipath=updated_sources[4],
            measurement_noise=updated_sources[5],
        )


def clock_error_source(
    name: str,
    bias_seconds: float = 0.0,
    jitter_seconds: float = 0.0,
    signal_speed_meters_per_second: float = SPEED_OF_LIGHT_METERS_PER_SECOND,
) -> ErrorSourceModel:
    """Create a clock-driven range error source from seconds."""
    _require_finite("bias_seconds", bias_seconds)
    _require_finite("jitter_seconds", jitter_seconds)
    _require_signal_speed(signal_speed_meters_per_second)
    if jitter_seconds < 0.0:
        raise ValueError("jitter_seconds must not be negative")
    return ErrorSourceModel(
        name=name,
        bias_meters=bias_seconds * signal_speed_meters_per_second,
        standard_deviation_meters=jitter_seconds * signal_speed_meters_per_second,
    )


def classroom_error_model(seed: int = 0) -> MeasurementErrorModel:
    """Return a small, reproducible error profile for lessons."""
    return MeasurementErrorModel(
        seed=seed,
        satellite_clock=clock_error_source(
            "satellite_clock",
            bias_seconds=8.0e-9,
            jitter_seconds=1.5e-9,
        ),
        receiver_clock=clock_error_source(
            "receiver_clock",
            bias_seconds=35.0e-9,
            jitter_seconds=4.0e-9,
        ),
        ionospheric_delay=ErrorSourceModel(
            "ionospheric_delay",
            bias_meters=4.5,
            standard_deviation_meters=0.8,
        ),
        tropospheric_delay=ErrorSourceModel(
            "tropospheric_delay",
            bias_meters=2.3,
            standard_deviation_meters=0.3,
        ),
        multipath=ErrorSourceModel(
            "multipath",
            bias_meters=0.0,
            standard_deviation_meters=1.5,
        ),
        measurement_noise=ErrorSourceModel(
            "measurement_noise",
            bias_meters=0.0,
            standard_deviation_meters=0.6,
        ),
    )


__all__ = [
    "ERROR_SOURCE_NAMES",
    "ErrorContribution",
    "ErrorSourceModel",
    "MeasurementError",
    "MeasurementErrorModel",
    "classroom_error_model",
    "clock_error_source",
]
