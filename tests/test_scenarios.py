from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from gps_sim.scenario_parameters import ConstellationParameters, ReceiverParameters
from gps_sim.scenarios import (
    SCENARIO_SCHEMA_VERSION,
    VersionedScenario,
    load_scenario_file,
    save_scenario_file,
    scenario_from_payload,
    scenario_to_payload,
)


class ScenarioFileTests(unittest.TestCase):
    def test_scenario_payload_round_trips_initial_state(self) -> None:
        scenario = VersionedScenario(
            constellation=ConstellationParameters(
                satellite_count=7,
                inclination_degrees=64.0,
                altitude_kilometers=21_100.0,
            ),
            receiver=ReceiverParameters(
                latitude_degrees=40.7,
                longitude_degrees=-74.0,
                altitude_meters=25.0,
                minimum_elevation_degrees=12.5,
                clock_bias_microseconds=-4.25,
            ),
            simulation_time_seconds=3661.0,
            orbital_speed_multiplier=20.0,
        )

        restored = scenario_from_payload(scenario_to_payload(scenario))

        self.assertEqual(scenario, restored)

    def test_scenario_file_is_versioned_json(self) -> None:
        scenario = VersionedScenario(
            constellation=ConstellationParameters(satellite_count=5),
            receiver=ReceiverParameters(clock_bias_microseconds=3.5),
            simulation_time_seconds=120.0,
            orbital_speed_multiplier=2.0,
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "lab.gps-scenario.json"

            save_scenario_file(path, scenario)
            payload = json.loads(path.read_text(encoding="utf-8"))
            loaded = load_scenario_file(path)

        self.assertEqual(SCENARIO_SCHEMA_VERSION, payload["schema_version"])
        self.assertEqual(scenario, loaded)

    def test_rejects_unsupported_schema_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported scenario schema version"):
            scenario_from_payload({"schema_version": 99})

    def test_rejects_missing_scenario_sections(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing constellation"):
            scenario_from_payload({"schema_version": SCENARIO_SCHEMA_VERSION})

    def test_rejects_invalid_parameter_values_with_actionable_message(self) -> None:
        payload = scenario_to_payload(VersionedScenario())
        payload["receiver"]["minimum_elevation_degrees"] = 90.0

        with self.assertRaisesRegex(ValueError, "receiver mask"):
            scenario_from_payload(payload)

    def test_rejects_negative_simulation_time(self) -> None:
        payload = scenario_to_payload(VersionedScenario())
        payload["simulation_time_seconds"] = -1.0

        with self.assertRaisesRegex(ValueError, "simulation time"):
            scenario_from_payload(payload)

    def test_rejects_invalid_json_file(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "broken.gps-scenario.json"
            path.write_text("{", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid scenario JSON"):
                load_scenario_file(path)


if __name__ == "__main__":
    unittest.main()
