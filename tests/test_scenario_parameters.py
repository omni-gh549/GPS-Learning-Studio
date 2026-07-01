from __future__ import annotations

import unittest

from gps_sim.scenario_parameters import (
    ConstellationParameters,
    ReceiverParameters,
    build_satellite_parameters,
)


class ScenarioParametersTests(unittest.TestCase):
    def test_builds_evenly_distributed_editable_constellation(self) -> None:
        constellation = ConstellationParameters(
            satellite_count=6,
            inclination_degrees=63.0,
            altitude_kilometers=20_200.0,
        )

        satellites = build_satellite_parameters(constellation)

        self.assertEqual(6, len(satellites))
        self.assertEqual([1, 2, 3, 4, 5, 6], [sat.satellite_id for sat in satellites])
        self.assertAlmostEqual(63.0, satellites[0].inclination_degrees)
        self.assertAlmostEqual(60.0, satellites[1].longitude_of_ascending_node_degrees)
        self.assertGreater(satellites[0].radius_meters, 26_000_000.0)
        self.assertGreater(satellites[1].orbital_period_seconds, satellites[0].orbital_period_seconds)

    def test_constellation_rejects_values_that_break_solver_lessons(self) -> None:
        with self.assertRaisesRegex(ValueError, "satellite count"):
            ConstellationParameters(satellite_count=3)
        with self.assertRaisesRegex(ValueError, "inclination"):
            ConstellationParameters(inclination_degrees=120.0)
        with self.assertRaisesRegex(ValueError, "altitude"):
            ConstellationParameters(altitude_kilometers=50.0)

    def test_receiver_parameters_convert_to_station_and_clock_bias(self) -> None:
        receiver = ReceiverParameters(
            latitude_degrees=51.5,
            longitude_degrees=-0.1,
            altitude_meters=40.0,
            minimum_elevation_degrees=15.0,
            clock_bias_microseconds=2.5,
        )

        station = receiver.to_ground_station()

        self.assertAlmostEqual(0.000_002_5, receiver.clock_bias_seconds)
        self.assertEqual(51.5, station.latitude_degrees)
        self.assertEqual(-0.1, station.longitude_degrees)
        self.assertEqual(40.0, station.altitude_meters)
        self.assertEqual(15.0, station.minimum_elevation_degrees)

    def test_receiver_rejects_out_of_range_classroom_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "latitude"):
            ReceiverParameters(latitude_degrees=91.0)
        with self.assertRaisesRegex(ValueError, "longitude"):
            ReceiverParameters(longitude_degrees=-181.0)
        with self.assertRaisesRegex(ValueError, "mask"):
            ReceiverParameters(minimum_elevation_degrees=90.0)
        with self.assertRaisesRegex(ValueError, "clock bias"):
            ReceiverParameters(clock_bias_microseconds=2000.0)


if __name__ == "__main__":
    unittest.main()
