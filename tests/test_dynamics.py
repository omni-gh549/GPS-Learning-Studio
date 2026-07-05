from __future__ import annotations

import unittest

import gps_sim.dynamics as dynamics
import gps_sim.runtime as runtime


class FakeVisualizer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float | None]] = []
        self.simulation_time_seconds = 0.0

    def get_simulation_time(self) -> float:
        self.calls.append(("get_simulation_time", None))
        return self.simulation_time_seconds

    def pause(self) -> None:
        self.calls.append(("pause", None))

    def play(self) -> None:
        self.calls.append(("play", None))

    def reset(self) -> None:
        self.calls.append(("reset", None))

    def set_simulation_time(self, seconds: float) -> None:
        self.calls.append(("set_simulation_time", seconds))
        self.simulation_time_seconds = seconds

    def set_earth_speed(self, multiplier: float) -> None:
        self.calls.append(("set_earth_speed", multiplier))

    def set_orbit_speed(self, multiplier: float) -> None:
        self.calls.append(("set_orbit_speed", multiplier))

    def step(self, seconds: float) -> None:
        self.calls.append(("step", seconds))
        self.simulation_time_seconds += seconds


class DynamicsFacadeTests(unittest.TestCase):
    def tearDown(self) -> None:
        runtime._visualizer = None

    def test_requires_active_visualizer_binding(self) -> None:
        runtime._visualizer = None

        with self.assertRaisesRegex(RuntimeError, "not connected"):
            dynamics.get_simulation_time()

    def test_forwards_speed_and_playback_controls_to_visualizer(self) -> None:
        visualizer = FakeVisualizer()
        runtime.bind_visualizer(visualizer)

        dynamics.set_orbital_time_scale(2.5)
        dynamics.set_earth_rotation_scale(0.25)
        dynamics.pause_simulation()
        dynamics.step_simulation(30.0)
        dynamics.set_simulation_time(600.0)
        self.assertEqual(600.0, dynamics.get_simulation_time())
        dynamics.play_simulation()
        dynamics.reset_simulation()

        self.assertEqual(
            [
                ("set_orbit_speed", 2.5),
                ("set_earth_speed", 0.25),
                ("pause", None),
                ("step", 30.0),
                ("set_simulation_time", 600.0),
                ("get_simulation_time", None),
                ("play", None),
                ("reset", None),
            ],
            visualizer.calls,
        )

    def test_step_uses_documented_sixty_second_default(self) -> None:
        visualizer = FakeVisualizer()
        runtime.bind_visualizer(visualizer)

        dynamics.step_simulation()

        self.assertEqual([("step", 60.0)], visualizer.calls)


if __name__ == "__main__":
    unittest.main()
