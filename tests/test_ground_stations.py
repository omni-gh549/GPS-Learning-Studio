from __future__ import annotations

import math
import unittest
from dataclasses import FrozenInstanceError

from gps_sim.ground_stations import (
    GroundStation,
    create_station,
    list_stations,
    remove_station,
    update_station,
)


class GroundStationTests(unittest.TestCase):
    def setUp(self) -> None:
        for name in list_stations():
            remove_station(name)

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

    def test_creates_and_lists_named_stations(self) -> None:
        station = create_station("Aberdeen", 57.1497, -2.0943, 65.0, 10.0)

        self.assertEqual(list_stations(), {"Aberdeen": station})

    def test_normalizes_station_names_and_rejects_duplicates(self) -> None:
        create_station("  Equator  ", 0.0, 0.0)

        with self.assertRaisesRegex(ValueError, "already exists"):
            create_station("Equator", 1.0, 1.0)

    def test_rejects_invalid_station_names(self) -> None:
        with self.assertRaises(ValueError):
            create_station("  ", 0.0, 0.0)
        with self.assertRaises(TypeError):
            create_station(42, 0.0, 0.0)

    def test_updates_selected_fields_without_mutating_original(self) -> None:
        original = create_station("Lab", 10.0, 20.0, 30.0, 5.0)

        updated = update_station(
            "Lab",
            altitude_meters=45.0,
            minimum_elevation_degrees=15.0,
        )

        self.assertEqual(original.altitude_meters, 30.0)
        self.assertEqual(updated.latitude_degrees, 10.0)
        self.assertEqual(updated.longitude_degrees, 20.0)
        self.assertEqual(updated.altitude_meters, 45.0)
        self.assertEqual(updated.minimum_elevation_degrees, 15.0)
        self.assertIs(list_stations()["Lab"], updated)

    def test_invalid_update_preserves_existing_station(self) -> None:
        original = create_station("Lab", 10.0, 20.0)

        with self.assertRaises(ValueError):
            update_station("Lab", latitude_degrees=91.0)

        self.assertIs(list_stations()["Lab"], original)

    def test_list_returns_a_snapshot(self) -> None:
        station = create_station("Lab", 10.0, 20.0)

        snapshot = list_stations()
        snapshot.clear()

        self.assertEqual(list_stations(), {"Lab": station})

    def test_removes_and_returns_station(self) -> None:
        station = create_station("Lab", 10.0, 20.0)

        self.assertIs(remove_station("Lab"), station)
        self.assertEqual(list_stations(), {})

    def test_unknown_station_operations_raise_clear_errors(self) -> None:
        with self.assertRaisesRegex(KeyError, "unknown station"):
            update_station("Missing", altitude_meters=1.0)
        with self.assertRaisesRegex(KeyError, "unknown station"):
            remove_station("Missing")


if __name__ == "__main__":
    unittest.main()
