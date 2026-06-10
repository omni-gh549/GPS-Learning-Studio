from __future__ import annotations

import math
import unittest
from dataclasses import FrozenInstanceError

from gps_sim.ground_stations import GroundStation


class GroundStationTests(unittest.TestCase):
    def test_stores_valid_geodetic_inputs(self) -> None:
        station = GroundStation(
            latitude_degrees=57.1497,
            longitude_degrees=-2.0943,
            altitude_meters=65.0,
            minimum_elevation_degrees=10.0,
        )

        self.assertEqual(station.latitude_degrees, 57.1497)
        self.assertEqual(station.longitude_degrees, -2.0943)
        self.assertEqual(station.altitude_meters, 65.0)
        self.assertEqual(station.minimum_elevation_degrees, 10.0)

    def test_uses_documented_defaults(self) -> None:
        station = GroundStation(0.0, 0.0)

        self.assertEqual(station.altitude_meters, 0.0)
        self.assertEqual(station.minimum_elevation_degrees, 5.0)

    def test_is_immutable(self) -> None:
        station = GroundStation(0.0, 0.0)

        with self.assertRaises(FrozenInstanceError):
            station.latitude_degrees = 1.0

    def test_rejects_out_of_range_coordinates_and_mask(self) -> None:
        invalid_arguments = (
            {"latitude_degrees": -90.1, "longitude_degrees": 0.0},
            {"latitude_degrees": 0.0, "longitude_degrees": 180.1},
            {
                "latitude_degrees": 0.0,
                "longitude_degrees": 0.0,
                "minimum_elevation_degrees": -0.1,
            },
            {
                "latitude_degrees": 0.0,
                "longitude_degrees": 0.0,
                "minimum_elevation_degrees": 90.1,
            },
        )

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    GroundStation(**arguments)

    def test_rejects_non_finite_values(self) -> None:
        for value in (math.inf, -math.inf, math.nan):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    GroundStation(value, 0.0)


if __name__ == "__main__":
    unittest.main()
