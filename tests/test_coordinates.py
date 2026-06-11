from __future__ import annotations

import math
import unittest

from gps_sim.coordinates import (
    CartesianPosition,
    LocalHorizonPosition,
    WGS84_SEMI_MAJOR_AXIS_METERS,
    ecef_to_eci,
    ecef_to_local_horizon,
    eci_to_ecef,
    local_horizon_to_ecef,
    orbital_to_eci,
    station_to_ecef,
)
from gps_sim.ground_stations import GroundStation


class CoordinateTests(unittest.TestCase):
    def assertPositionAlmostEqual(
        self,
        actual: CartesianPosition,
        expected: CartesianPosition,
        places: int = 6,
    ) -> None:
        self.assertAlmostEqual(actual.x_meters, expected.x_meters, places=places)
        self.assertAlmostEqual(actual.y_meters, expected.y_meters, places=places)
        self.assertAlmostEqual(actual.z_meters, expected.z_meters, places=places)

    def test_orbital_axes_have_known_inertial_positions(self) -> None:
        radius = 26_560_000.0

        ascending_node = orbital_to_eci(radius, 55.0, 90.0, 0.0)
        northern_limit = orbital_to_eci(radius, 90.0, 0.0, 90.0)

        self.assertPositionAlmostEqual(
            ascending_node,
            CartesianPosition(0.0, radius, 0.0),
        )
        self.assertPositionAlmostEqual(
            northern_limit,
            CartesianPosition(0.0, 0.0, radius),
        )

    def test_eci_and_ecef_rotation_round_trip(self) -> None:
        original = CartesianPosition(12_000.0, -34_000.0, 56_000.0)

        earth_fixed = eci_to_ecef(original, 73.25)
        recovered = ecef_to_eci(earth_fixed, 73.25)

        self.assertPositionAlmostEqual(recovered, original)

    def test_equatorial_station_has_known_wgs84_position(self) -> None:
        station = GroundStation(0.0, 0.0, altitude_meters=100.0)

        position = station_to_ecef(station)

        self.assertPositionAlmostEqual(
            position,
            CartesianPosition(WGS84_SEMI_MAJOR_AXIS_METERS + 100.0, 0.0, 0.0),
        )

    def test_local_horizon_axes_at_equator_and_prime_meridian(self) -> None:
        station = GroundStation(0.0, 0.0)
        origin = station_to_ecef(station)
        target = CartesianPosition(
            origin.x_meters + 30.0,
            origin.y_meters + 10.0,
            origin.z_meters + 20.0,
        )

        local = ecef_to_local_horizon(target, station)

        self.assertEqual(local, LocalHorizonPosition(10.0, 20.0, 30.0))

    def test_local_horizon_and_ecef_round_trip(self) -> None:
        station = GroundStation(57.1497, -2.0943, altitude_meters=65.0)
        local = LocalHorizonPosition(1_250.0, -480.0, 22_000.0)

        earth_fixed = local_horizon_to_ecef(local, station)
        recovered = ecef_to_local_horizon(earth_fixed, station)

        self.assertAlmostEqual(recovered.east_meters, local.east_meters, places=6)
        self.assertAlmostEqual(
            recovered.north_meters,
            local.north_meters,
            places=6,
        )
        self.assertAlmostEqual(recovered.up_meters, local.up_meters, places=6)

    def test_rejects_invalid_orbital_inputs(self) -> None:
        with self.assertRaises(ValueError):
            orbital_to_eci(0.0, 55.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            orbital_to_eci(26_560_000.0, math.nan, 0.0, 0.0)

    def test_position_types_reject_non_finite_values(self) -> None:
        with self.assertRaises(ValueError):
            CartesianPosition(math.inf, 0.0, 0.0)
        with self.assertRaises(ValueError):
            LocalHorizonPosition(0.0, math.nan, 0.0)


if __name__ == "__main__":
    unittest.main()
