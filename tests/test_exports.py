from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from gps_sim.exports import (
    EXPORT_SCHEMA_VERSION,
    build_telemetry_export,
    save_telemetry_export_csv,
    save_telemetry_export_json,
    telemetry_export_csv_rows,
)
from gps_sim.ground_stations import GroundStation
from gps_sim.visualization import (
    AccuracyHistoryPoint,
    SatelliteSceneState,
    build_accuracy_comparison_display,
    build_ground_station_scenes,
)


def _sample_scene():
    station = GroundStation(0.0, 0.0, minimum_elevation_degrees=10.0)
    satellites = (
        SatelliteSceneState(1, 26_560_000.0, 0.0, 0.0, 0.0),
        SatelliteSceneState(2, 26_560_000.0, 55.0, 90.0, 60.0),
        SatelliteSceneState(3, 26_560_000.0, 55.0, 180.0, 130.0),
        SatelliteSceneState(4, 26_560_000.0, 35.0, 270.0, 250.0),
    )
    return build_ground_station_scenes(
        satellites,
        {"Receiver": station},
        earth_rotation_degrees=0.0,
    )[0]


class TelemetryExportTests(unittest.TestCase):
    def test_export_payload_includes_units_timestamp_and_experiment_results(self) -> None:
        scene = _sample_scene()
        comparison = build_accuracy_comparison_display(scene)
        payload = build_telemetry_export(
            scene,
            simulation_time_seconds=123.5,
            receiver_clock_bias_seconds=0.000_001,
            accuracy_comparison=comparison,
            accuracy_history=(
                AccuracyHistoryPoint(123.5, 0.0, comparison.with_errors.position_error_meters),
            ),
        )

        self.assertEqual(EXPORT_SCHEMA_VERSION, payload["schema_version"])
        self.assertEqual(123.5, payload["simulation_time_seconds"])
        self.assertEqual("seconds", payload["units"]["time"])
        self.assertEqual("meters", payload["units"]["distance"])
        self.assertEqual("Receiver", payload["station"]["name"])
        self.assertEqual([1, 2, 3, 4], [row["satellite_id"] for row in payload["visibility"]])
        self.assertEqual(
            [1, 2, 3, 4],
            [row["satellite_id"] for row in payload["measurements"]],
        )
        self.assertIn("pseudorange_meters", payload["measurements"][0])
        self.assertTrue(payload["position_fix"]["converged"])
        self.assertIn("with_errors", payload["accuracy_comparison"])
        self.assertEqual(1, len(payload["accuracy_history"]))

    def test_writes_json_and_tidy_csv_exports(self) -> None:
        scene = _sample_scene()
        comparison = build_accuracy_comparison_display(scene)
        payload = build_telemetry_export(
            scene,
            simulation_time_seconds=600.0,
            receiver_clock_bias_seconds=0.000_001,
            accuracy_comparison=comparison,
        )

        with TemporaryDirectory() as directory:
            json_path = Path(directory) / "lab.gps-telemetry.json"
            csv_path = Path(directory) / "lab.csv"

            save_telemetry_export_json(json_path, payload)
            save_telemetry_export_csv(csv_path, payload)

            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            with csv_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(EXPORT_SCHEMA_VERSION, loaded["schema_version"])
        self.assertTrue(any(row["record_type"] == "visibility" for row in rows))
        self.assertTrue(any(row["record_type"] == "measurement" for row in rows))
        self.assertTrue(any(row["metric"] == "pseudorange_meters" for row in rows))
        self.assertTrue(
            any(
                row["record_type"] == "accuracy_comparison"
                and row["metric"] == "total_pseudorange_error_meters"
                and row["unit"] == "meters"
                for row in rows
            )
        )

    def test_csv_rows_expose_simulation_time_and_units(self) -> None:
        scene = _sample_scene()
        comparison = build_accuracy_comparison_display(scene)
        payload = build_telemetry_export(
            scene,
            simulation_time_seconds=42.0,
            receiver_clock_bias_seconds=0.000_001,
            accuracy_comparison=comparison,
        )

        rows = telemetry_export_csv_rows(payload)

        self.assertTrue(rows)
        self.assertTrue(all(row["simulation_time_seconds"] == 42.0 for row in rows))
        self.assertIn(
            {
                "record_type": "measurement",
                "simulation_time_seconds": 42.0,
                "station_name": "Receiver",
                "satellite_id": 1,
                "sample_index": "",
                "metric": "pseudorange_meters",
                "value": payload["measurements"][0]["pseudorange_meters"],
                "unit": "meters",
            },
            rows,
        )


if __name__ == "__main__":
    unittest.main()
