"""Telemetry and experiment export helpers for repeatable classroom labs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .visualization import (
    AccuracyComparisonDisplay,
    AccuracyHistoryPoint,
    GroundStationScene,
    ReceiverPositionFixDisplay,
    build_receiver_measurement_links,
    build_station_visibility_rows,
)

EXPORT_SCHEMA_VERSION = 1


def build_telemetry_export(
    scene: GroundStationScene,
    simulation_time_seconds: float,
    receiver_clock_bias_seconds: float,
    accuracy_comparison: AccuracyComparisonDisplay,
    accuracy_history: tuple[AccuracyHistoryPoint, ...] = (),
) -> dict[str, Any]:
    """Build a JSON-serializable telemetry and experiment result payload."""
    visibility_rows = build_station_visibility_rows(scene)
    measurement_links = build_receiver_measurement_links(
        scene,
        receiver_clock_bias_seconds=receiver_clock_bias_seconds,
    )
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "simulation_time_seconds": simulation_time_seconds,
        "units": {
            "time": "seconds",
            "angle": "degrees",
            "distance": "meters",
            "clock_bias": "seconds",
            "position": "meters_ecef",
        },
        "station": {
            "name": scene.name,
            "latitude_degrees": scene.station.latitude_degrees,
            "longitude_degrees": scene.station.longitude_degrees,
            "altitude_meters": scene.station.altitude_meters,
            "minimum_elevation_degrees": scene.station.minimum_elevation_degrees,
        },
        "visibility": [
            {
                "satellite_id": row.satellite_id,
                "azimuth_degrees": row.azimuth_degrees,
                "elevation_degrees": row.elevation_degrees,
                "range_meters": row.range_meters,
                "is_visible": row.is_visible,
            }
            for row in visibility_rows
        ],
        "measurements": [
            {
                "satellite_id": link.satellite_id,
                "geometric_range_meters": link.geometric_range_meters,
                "pseudorange_meters": link.pseudorange_meters,
                "receiver_clock_bias_seconds": link.receiver_clock_bias_seconds,
                "is_visible": link.is_visible,
            }
            for link in measurement_links
        ],
        "position_fix": _position_fix_payload(accuracy_comparison.baseline),
        "accuracy_comparison": {
            "error_model_seed": accuracy_comparison.error_model_seed,
            "total_pseudorange_error_meters": (
                accuracy_comparison.total_pseudorange_error_meters
            ),
            "baseline": _position_fix_payload(accuracy_comparison.baseline),
            "with_errors": _position_fix_payload(accuracy_comparison.with_errors),
        },
        "accuracy_history": [
            {
                "elapsed_seconds": point.elapsed_seconds,
                "baseline_position_error_meters": (
                    point.baseline_position_error_meters
                ),
                "error_position_error_meters": point.error_position_error_meters,
            }
            for point in accuracy_history
        ],
    }


def save_telemetry_export_json(path: Path, payload: dict[str, Any]) -> None:
    """Write an export payload as formatted JSON."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def save_telemetry_export_csv(path: Path, payload: dict[str, Any]) -> None:
    """Write an export payload as tidy metric rows for spreadsheets."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "record_type",
                "simulation_time_seconds",
                "station_name",
                "satellite_id",
                "sample_index",
                "metric",
                "value",
                "unit",
            ],
        )
        writer.writeheader()
        for row in telemetry_export_csv_rows(payload):
            writer.writerow(row)


def telemetry_export_csv_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a telemetry payload into stable CSV rows."""
    rows: list[dict[str, Any]] = []
    time_seconds = payload["simulation_time_seconds"]
    station_name = payload["station"]["name"]
    units = payload["units"]
    for field, value in payload["station"].items():
        unit = _unit_for_field(field, units)
        rows.append(
            _csv_row("station", time_seconds, station_name, "", "", field, value, unit)
        )
    for visibility in payload["visibility"]:
        for field, value in visibility.items():
            if field == "satellite_id":
                continue
            rows.append(
                _csv_row(
                    "visibility",
                    time_seconds,
                    station_name,
                    visibility["satellite_id"],
                    "",
                    field,
                    value,
                    _unit_for_field(field, units),
                )
            )
    for measurement in payload["measurements"]:
        for field, value in measurement.items():
            if field == "satellite_id":
                continue
            rows.append(
                _csv_row(
                    "measurement",
                    time_seconds,
                    station_name,
                    measurement["satellite_id"],
                    "",
                    field,
                    value,
                    _unit_for_field(field, units),
                )
            )
    _append_position_fix_rows(
        rows,
        "position_fix",
        time_seconds,
        station_name,
        payload["position_fix"],
        units,
    )
    comparison = payload["accuracy_comparison"]
    rows.append(
        _csv_row(
            "accuracy_comparison",
            time_seconds,
            station_name,
            "",
            "",
            "error_model_seed",
            comparison["error_model_seed"],
            "",
        )
    )
    rows.append(
        _csv_row(
            "accuracy_comparison",
            time_seconds,
            station_name,
            "",
            "",
            "total_pseudorange_error_meters",
            comparison["total_pseudorange_error_meters"],
            units["distance"],
        )
    )
    _append_position_fix_rows(
        rows,
        "accuracy_baseline",
        time_seconds,
        station_name,
        comparison["baseline"],
        units,
    )
    _append_position_fix_rows(
        rows,
        "accuracy_with_errors",
        time_seconds,
        station_name,
        comparison["with_errors"],
        units,
    )
    for index, point in enumerate(payload["accuracy_history"]):
        for field, value in point.items():
            rows.append(
                _csv_row(
                    "accuracy_history",
                    time_seconds,
                    station_name,
                    "",
                    index,
                    field,
                    value,
                    _unit_for_field(field, units),
                )
            )
    return rows


def _append_position_fix_rows(
    rows: list[dict[str, Any]],
    record_type: str,
    time_seconds: float,
    station_name: str,
    payload: dict[str, Any],
    units: dict[str, str],
) -> None:
    for field, value in payload.items():
        if isinstance(value, dict):
            for nested_field, nested_value in value.items():
                rows.append(
                    _csv_row(
                        record_type,
                        time_seconds,
                        station_name,
                        "",
                        "",
                        f"{field}.{nested_field}",
                        nested_value,
                        _unit_for_field(nested_field, units),
                    )
                )
        elif isinstance(value, list):
            for index, item in enumerate(value):
                rows.append(
                    _csv_row(
                        record_type,
                        time_seconds,
                        station_name,
                        "",
                        index,
                        field,
                        item,
                        units["distance"],
                    )
                )
        else:
            rows.append(
                _csv_row(
                    record_type,
                    time_seconds,
                    station_name,
                    "",
                    "",
                    field,
                    value,
                    _unit_for_field(field, units),
                )
            )


def _position_fix_payload(display: ReceiverPositionFixDisplay) -> dict[str, Any]:
    return {
        "true_receiver_ecef": _position_payload(display.true_receiver_ecef),
        "estimated_receiver_ecef": (
            _position_payload(display.estimated_receiver_ecef)
            if display.estimated_receiver_ecef is not None
            else None
        ),
        "true_clock_bias_seconds": display.true_clock_bias_seconds,
        "estimated_clock_bias_seconds": display.estimated_clock_bias_seconds,
        "residuals_meters": list(display.residuals_meters),
        "max_abs_residual_meters": display.max_abs_residual_meters,
        "rms_residual_meters": display.rms_residual_meters,
        "horizontal_error_meters": display.horizontal_error_meters,
        "vertical_error_meters": display.vertical_error_meters,
        "position_error_meters": display.position_error_meters,
        "converged": display.converged,
        "diagnostic": display.diagnostic,
    }


def _position_payload(position: Any) -> dict[str, float]:
    return {
        "x_meters": position.x_meters,
        "y_meters": position.y_meters,
        "z_meters": position.z_meters,
    }


def _csv_row(
    record_type: str,
    simulation_time_seconds: float,
    station_name: str,
    satellite_id: Any,
    sample_index: Any,
    metric: str,
    value: Any,
    unit: str,
) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "simulation_time_seconds": simulation_time_seconds,
        "station_name": station_name,
        "satellite_id": satellite_id,
        "sample_index": sample_index,
        "metric": metric,
        "value": value,
        "unit": unit,
    }


def _unit_for_field(field: str, units: dict[str, str]) -> str:
    if field.endswith("_degrees"):
        return units["angle"]
    if field.endswith("_meters") or field.endswith("_ecef"):
        return units["distance"]
    if field.endswith("_seconds"):
        return units["time"]
    if field.endswith("_bias_seconds"):
        return units["clock_bias"]
    return ""


__all__ = [
    "EXPORT_SCHEMA_VERSION",
    "build_telemetry_export",
    "save_telemetry_export_csv",
    "save_telemetry_export_json",
    "telemetry_export_csv_rows",
]
