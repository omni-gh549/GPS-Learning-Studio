from __future__ import annotations

import math
import unittest

from gps_sim.coordinates import (
    LocalHorizonPosition,
    local_horizon_to_ecef,
)
from gps_sim.ground_stations import GroundStation
from gps_sim.visibility import (
    calculate_visibility,
    local_horizon_visibility,
)


class VisibilityTests(unittest.TestCase):
    def test_overhead_target_is_visible_at_zenith(self) -> None:
        result = local_horizon_visibility(
            LocalHorizonPosition(0.0, 0.0, 20_200_000.0),
            minimum_elevation_degrees=10.0,
        )

        self.assertEqual(result.azimuth_degrees, 0.0)
        self.assertEqual(result.elevation_degrees, 90.0)
        self.assertEqual(result.range_meters, 20_200_000.0)
        self.assertTrue(result.is_visible)

    def test_horizon_target_has_known_azimuth_and_range(self) -> None:
        result = local_horizon_visibility(
            LocalHorizonPosition(3_000.0, 4_000.0, 0.0),
        )

        self.assertAlmostEqual(result.azimuth_degrees, 36.86989765)
        self.assertEqual(result.elevation_degrees, 0.0)
        self.assertEqual(result.range_meters, 5_000.0)
        self.assertTrue(result.is_visible)

    def test_elevation_mask_is_inclusive(self) -> None:
        target = LocalHorizonPosition(0.0, 1_000.0, 1_000.0)

        at_mask = local_horizon_visibility(target, 45.0)
        above_mask = local_horizon_visibility(target, 44.9)
        below_mask = local_horizon_visibility(target, 45.1)

        self.assertTrue(at_mask.is_visible)
        self.assertTrue(above_mask.is_visible)
        self.assertFalse(below_mask.is_visible)

    def test_below_horizon_target_is_not_visible(self) -> None:
        result = local_horizon_visibility(
            LocalHorizonPosition(0.0, 1_000.0, -1_000.0),
        )

        self.assertEqual(result.azimuth_degrees, 0.0)
        self.assertEqual(result.elevation_degrees, -45.0)
        self.assertFalse(result.is_visible)

    def test_ecef_calculation_uses_station_mask(self) -> None:
        station = GroundStation(
            57.1497,
            -2.0943,
            altitude_meters=65.0,
            minimum_elevation_degrees=30.0,
        )
        local_target = LocalHorizonPosition(
            10_000.0,
            0.0,
            10_000.0 / math.sqrt(3.0),
        )
        satellite_ecef = local_horizon_to_ecef(local_target, station)

        result = calculate_visibility(satellite_ecef, station)

        self.assertAlmostEqual(result.azimuth_degrees, 90.0, places=9)
        self.assertAlmostEqual(result.elevation_degrees, 30.0, places=9)
        self.assertAlmostEqual(
            result.range_meters,
            math.hypot(10_000.0, 10_000.0 / math.sqrt(3.0)),
            places=6,
        )
        self.assertTrue(result.is_visible)

    def test_rejects_coincident_target_and_invalid_mask(self) -> None:
        with self.assertRaisesRegex(ValueError, "must differ"):
            local_horizon_visibility(LocalHorizonPosition(0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            local_horizon_visibility(
                LocalHorizonPosition(1.0, 0.0, 0.0),
                minimum_elevation_degrees=math.nan,
            )
        with self.assertRaises(ValueError):
            local_horizon_visibility(
                LocalHorizonPosition(1.0, 0.0, 0.0),
                minimum_elevation_degrees=90.1,
            )


if __name__ == "__main__":
    unittest.main()
