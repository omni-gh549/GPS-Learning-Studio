from __future__ import annotations

import unittest

from gps_sim.simulation_time import SimulationClock


class SimulationClockTests(unittest.TestCase):
    def test_playing_clock_advances_by_speed_multiplier(self) -> None:
        clock = SimulationClock(speed_multiplier=2.0, wall_time_seconds=10.0)

        self.assertEqual(10.0, clock.tick(15.0))

    def test_speed_change_does_not_recalculate_prior_elapsed_time(self) -> None:
        clock = SimulationClock(speed_multiplier=1.0, wall_time_seconds=0.0)
        clock.tick(5.0)

        clock.set_speed(10.0, wall_time_seconds=5.0)
        clock.tick(6.0)

        self.assertEqual(15.0, clock.simulation_seconds)

    def test_pause_freezes_time_until_play(self) -> None:
        clock = SimulationClock(wall_time_seconds=0.0)
        clock.pause(2.0)
        clock.tick(20.0)

        self.assertEqual(2.0, clock.simulation_seconds)
        self.assertFalse(clock.is_playing)

        clock.play(20.0)
        clock.tick(23.0)

        self.assertEqual(5.0, clock.simulation_seconds)

    def test_step_advances_while_paused(self) -> None:
        clock = SimulationClock(is_playing=False, wall_time_seconds=0.0)

        self.assertEqual(60.0, clock.step(60.0, wall_time_seconds=10.0))
        self.assertFalse(clock.is_playing)

    def test_set_time_jumps_to_specific_elapsed_seconds(self) -> None:
        clock = SimulationClock(wall_time_seconds=0.0)
        clock.tick(5.0)

        clock.set_time(120.0, wall_time_seconds=5.0)

        self.assertEqual(120.0, clock.simulation_seconds)

    def test_rejects_negative_speed_and_step(self) -> None:
        clock = SimulationClock(wall_time_seconds=0.0)

        with self.assertRaisesRegex(ValueError, "multiplier"):
            clock.set_speed(-1.0, wall_time_seconds=0.0)
        with self.assertRaisesRegex(ValueError, "seconds"):
            clock.step(-1.0, wall_time_seconds=0.0)
        with self.assertRaisesRegex(ValueError, "seconds"):
            clock.set_time(-1.0, wall_time_seconds=0.0)


if __name__ == "__main__":
    unittest.main()
