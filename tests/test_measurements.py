from __future__ import annotations

import math
import unittest

from gps_sim.coordinates import CartesianPosition
from gps_sim.measurements import (
    SPEED_OF_LIGHT_METERS_PER_SECOND,
    RangeMeasurement,
    calculate_pseudorange,
    geometric_range,
)


class MeasurementTests(unittest.TestCase):
    def test_geometric_range_uses_ecef_distance(self) -> None:
        receiver = CartesianPosition(1_000.0, -2_000.0, 3_000.0)
        satellite = CartesianPosition(5_000.0, 4_000.0, 15_000.0)

        result = geometric_range(receiver, satellite)

        self.assertEqual(result, 14_000.0)

    def test_zero_clock_bias_pseudorange_matches_geometric_range(self) -> None:
        receiver = CartesianPosition(0.0, 0.0, 0.0)
        satellite = CartesianPosition(3.0, 4.0, 12.0)

        result = calculate_pseudorange(receiver, satellite)

        self.assertEqual(result.geometric_range_meters, 13.0)
        self.assertEqual(result.pseudorange_meters, 13.0)
        self.assertEqual(result.receiver_clock_bias_seconds, 0.0)

    def test_receiver_clock_bias_adds_light_travel_distance(self) -> None:
        receiver = CartesianPosition(0.0, 0.0, 0.0)
        satellite = CartesianPosition(20_200_000.0, 0.0, 0.0)

        result = calculate_pseudorange(
            receiver,
            satellite,
            receiver_clock_bias_seconds=0.000_001,
        )

        self.assertEqual(result.geometric_range_meters, 20_200_000.0)
        self.assertAlmostEqual(
            result.pseudorange_meters,
            20_200_000.0 + SPEED_OF_LIGHT_METERS_PER_SECOND * 0.000_001,
            places=9,
        )

    def test_custom_signal_speed_keeps_classroom_examples_deterministic(self) -> None:
        receiver = CartesianPosition(0.0, 0.0, 0.0)
        satellite = CartesianPosition(1_000.0, 0.0, 0.0)

        result = calculate_pseudorange(
            receiver,
            satellite,
            receiver_clock_bias_seconds=-2.0,
            signal_speed_meters_per_second=100.0,
        )

        self.assertEqual(result.pseudorange_meters, 800.0)

    def test_rejects_invalid_measurement_inputs(self) -> None:
        receiver = CartesianPosition(0.0, 0.0, 0.0)
        satellite = CartesianPosition(1.0, 0.0, 0.0)

        with self.assertRaisesRegex(ValueError, "receiver_clock_bias_seconds"):
            calculate_pseudorange(receiver, satellite, math.nan)
        with self.assertRaisesRegex(ValueError, "signal_speed"):
            calculate_pseudorange(
                receiver,
                satellite,
                signal_speed_meters_per_second=0.0,
            )
        with self.assertRaisesRegex(ValueError, "geometric_range"):
            RangeMeasurement(-1.0, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
