"""Versioned scenario file helpers for repeatable classroom setups."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scenario_parameters import ConstellationParameters, ReceiverParameters


SCENARIO_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class VersionedScenario:
    """Complete editable scenario state that can be saved and restored."""

    constellation: ConstellationParameters = ConstellationParameters()
    receiver: ReceiverParameters = ReceiverParameters()
    simulation_time_seconds: float = 0.0
    orbital_speed_multiplier: float = 1.0

    def __post_init__(self) -> None:
        _require_finite_non_negative(
            "simulation time",
            self.simulation_time_seconds,
        )
        _require_finite_non_negative(
            "orbital speed multiplier",
            self.orbital_speed_multiplier,
        )


def scenario_to_payload(scenario: VersionedScenario) -> dict[str, Any]:
    """Convert a validated scenario into the stable JSON payload shape."""

    return {
        "schema_version": SCENARIO_SCHEMA_VERSION,
        "simulation_time_seconds": scenario.simulation_time_seconds,
        "orbital_speed_multiplier": scenario.orbital_speed_multiplier,
        "constellation": {
            "satellite_count": scenario.constellation.satellite_count,
            "inclination_degrees": scenario.constellation.inclination_degrees,
            "altitude_kilometers": scenario.constellation.altitude_kilometers,
        },
        "receiver": {
            "latitude_degrees": scenario.receiver.latitude_degrees,
            "longitude_degrees": scenario.receiver.longitude_degrees,
            "altitude_meters": scenario.receiver.altitude_meters,
            "minimum_elevation_degrees": (
                scenario.receiver.minimum_elevation_degrees
            ),
            "clock_bias_microseconds": scenario.receiver.clock_bias_microseconds,
        },
    }


def scenario_from_payload(payload: object) -> VersionedScenario:
    """Validate a JSON-like payload and return the corresponding scenario."""

    if not isinstance(payload, dict):
        raise ValueError("scenario file must contain a JSON object")
    version = payload.get("schema_version")
    if version != SCENARIO_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported scenario schema version {version!r}; expected "
            f"{SCENARIO_SCHEMA_VERSION}"
        )

    constellation = _required_mapping(payload, "constellation")
    receiver = _required_mapping(payload, "receiver")
    try:
        return VersionedScenario(
            constellation=ConstellationParameters(
                satellite_count=int(_required(constellation, "satellite_count")),
                inclination_degrees=float(
                    _required(constellation, "inclination_degrees")
                ),
                altitude_kilometers=float(
                    _required(constellation, "altitude_kilometers")
                ),
            ),
            receiver=ReceiverParameters(
                latitude_degrees=float(_required(receiver, "latitude_degrees")),
                longitude_degrees=float(_required(receiver, "longitude_degrees")),
                altitude_meters=float(_required(receiver, "altitude_meters")),
                minimum_elevation_degrees=float(
                    _required(receiver, "minimum_elevation_degrees")
                ),
                clock_bias_microseconds=float(
                    _required(receiver, "clock_bias_microseconds")
                ),
            ),
            simulation_time_seconds=float(
                payload.get("simulation_time_seconds", 0.0)
            ),
            orbital_speed_multiplier=float(
                payload.get("orbital_speed_multiplier", 1.0)
            ),
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid scenario file: {error}") from error


def save_scenario_file(path: Path, scenario: VersionedScenario) -> None:
    """Write a scenario as formatted JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(scenario_to_payload(scenario), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_scenario_file(path: Path) -> VersionedScenario:
    """Read and validate a scenario JSON file."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid scenario JSON: {error.msg}") from error
    except OSError as error:
        raise ValueError(f"could not read scenario file: {error}") from error
    return scenario_from_payload(payload)


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = _required(payload, key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _required(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise ValueError(f"missing {key}")
    return payload[key]


def _require_finite_non_negative(label: str, value: float) -> None:
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{label} must be a finite non-negative value")


__all__ = [
    "SCENARIO_SCHEMA_VERSION",
    "VersionedScenario",
    "load_scenario_file",
    "save_scenario_file",
    "scenario_from_payload",
    "scenario_to_payload",
]
