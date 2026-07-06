from __future__ import annotations

import unittest

from app import execute_editor_source
import gps_sim.runtime as runtime


class EditorApiVisualizer:
    def __init__(self) -> None:
        self.satellites = [object(), object(), object(), object()]
        self.simulation_time_seconds = 0.0
        self.orbit_speed = 1.0
        self.earth_speed = 1.0
        self.is_playing = True
        self.reset_count = 0

    def get_simulation_time(self) -> float:
        return self.simulation_time_seconds

    def pause(self) -> None:
        self.is_playing = False

    def play(self) -> None:
        self.is_playing = True

    def reset(self) -> None:
        self.reset_count += 1
        self.simulation_time_seconds = 0.0
        self.orbit_speed = 1.0
        self.earth_speed = 1.0
        self.is_playing = True

    def satellite_data(self) -> list[dict[str, float | int]]:
        return [
            {
                "id": index + 1,
                "orbital_angle_degrees": self.simulation_time_seconds + index,
                "inclination_degrees": 55.0,
            }
            for index, _satellite in enumerate(self.satellites)
        ]

    def set_simulation_time(self, seconds: float) -> None:
        self.simulation_time_seconds = seconds

    def set_earth_speed(self, multiplier: float) -> None:
        self.earth_speed = multiplier

    def set_orbit_speed(self, multiplier: float) -> None:
        self.orbit_speed = multiplier

    def step(self, seconds: float) -> None:
        self.simulation_time_seconds += seconds


class EditorApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.visualizer = EditorApiVisualizer()
        runtime.bind_visualizer(self.visualizer)
        self.namespace: dict[str, object] = {"__name__": "__main__"}

    def tearDown(self) -> None:
        runtime._visualizer = None

    def test_editor_script_uses_public_simulator_api(self) -> None:
        output = execute_editor_source(
            "import gps_sim.constellation as constellation\n"
            "import gps_sim.dynamics as dynamics\n\n"
            "dynamics.pause_simulation()\n"
            "dynamics.set_simulation_time(120.0)\n"
            "dynamics.step_simulation(30.0)\n"
            "dynamics.set_orbital_time_scale(3.5)\n"
            "dynamics.set_earth_rotation_scale(0.25)\n"
            "states = constellation.get_satellite_states()\n"
            "print(constellation.get_satellite_count())\n"
            "print(dynamics.get_simulation_time())\n"
            "print(states[0][\"orbital_angle_degrees\"])\n",
            self.namespace,
        )

        self.assertEqual("4\n150.0\n150.0\n", output)
        self.assertFalse(self.visualizer.is_playing)
        self.assertEqual(3.5, self.visualizer.orbit_speed)
        self.assertEqual(0.25, self.visualizer.earth_speed)
        self.assertIn("states", self.namespace)

    def test_editor_namespace_persists_between_runs(self) -> None:
        first_output = execute_editor_source("lab_value = 41\n", self.namespace)
        second_output = execute_editor_source("print(lab_value + 1)\n", self.namespace)

        self.assertEqual("Finished with no output.\n", first_output)
        self.assertEqual("42\n", second_output)

    def test_editor_script_reports_traceback_without_raising_to_ui(self) -> None:
        output = execute_editor_source(
            "import gps_sim.constellation as constellation\n"
            "print(constellation.missing_function())\n",
            self.namespace,
            filename="student_lab.py",
        )

        self.assertIn("Traceback", output)
        self.assertIn("student_lab.py", output)
        self.assertIn("missing_function", output)


if __name__ == "__main__":
    unittest.main()
