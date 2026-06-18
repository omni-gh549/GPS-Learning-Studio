from __future__ import annotations

import unittest

from gps_sim.coordinates import CartesianPosition
from gps_sim.measurements import (
    SPEED_OF_LIGHT_METERS_PER_SECOND,
    calculate_pseudorange,
)
from gps_sim.positioning import PseudorangeObservation, solve_position


class PositioningTests(unittest.TestCase):
    def test_noise_free_four_satellite_fix_converges(self) -> None:
        receiver = CartesianPosition(1_000_000.0, -2_000_000.0, 3_000_000.0)
        clock_bias_seconds = 0.000_0015
        observations = _observations(receiver, clock_bias_seconds)

        fix = solve_position(observations)

        self.assertTrue(fix.converged)
        self.assertLessEqual(fix.iterations, 10)
        self.assertAlmostEqual(fix.receiver_ecef.x_meters, receiver.x_meters, places=3)
        self.assertAlmostEqual(fix.receiver_ecef.y_meters, receiver.y_meters, places=3)
        self.assertAlmostEqual(fix.receiver_ecef.z_meters, receiver.z_meters, places=3)
        self.assertAlmostEqual(
            fix.receiver_clock_bias_seconds,
            clock_bias_seconds,
            places=12,
        )
        self.assertLess(max(abs(residual) for residual in fix.residuals_meters), 0.001)

    def test_extra_measurement_is_fit_in_least_squares(self) -> None:
        receiver = CartesianPosition(2_500_000.0, 1_250_000.0, -3_000_000.0)
        observations = _observations(receiver, -0.000_0008)
        extra_satellite = CartesianPosition(21_000_000.0, 12_000_000.0, 17_000_000.0)
        extra_reading = calculate_pseudorange(
            receiver,
            extra_satellite,
            receiver_clock_bias_seconds=-0.000_0008,
        )
        observations.append(
            PseudorangeObservation(
                extra_satellite,
                extra_reading.pseudorange_meters,
            )
        )

        fix = solve_position(observations)

        self.assertTrue(fix.converged)
        self.assertEqual(len(fix.residuals_meters), 5)
        self.assertAlmostEqual(fix.receiver_ecef.x_meters, receiver.x_meters, places=3)
        self.assertAlmostEqual(fix.receiver_ecef.y_meters, receiver.y_meters, places=3)
        self.assertAlmostEqual(fix.receiver_ecef.z_meters, receiver.z_meters, places=3)

    def test_rejects_invalid_or_poor_geometry_inputs(self) -> None:
        satellite = CartesianPosition(20_200_000.0, 0.0, 0.0)

        with self.assertRaisesRegex(ValueError, "pseudorange_meters"):
            PseudorangeObservation(satellite, 0.0)
        with self.assertRaisesRegex(ValueError, "at least four"):
            solve_position([PseudorangeObservation(satellite, 20_200_000.0)])
        with self.assertRaisesRegex(ValueError, "signal_speed"):
            solve_position(
                [PseudorangeObservation(satellite, 20_200_000.0)] * 4,
                signal_speed_meters_per_second=0.0,
            )
        with self.assertRaisesRegex(ValueError, "singular|poorly conditioned"):
            solve_position(
                [PseudorangeObservation(satellite, 20_200_000.0)] * 4,
            )


def _observations(
    receiver: CartesianPosition,
    receiver_clock_bias_seconds: float,
) -> list[PseudorangeObservation]:
    satellites = (
        CartesianPosition(20_200_000.0, 0.0, 0.0),
        CartesianPosition(0.0, 21_200_000.0, 1_000_000.0),
        CartesianPosition(1_500_000.0, 0.0, 22_200_000.0),
        CartesianPosition(-20_500_000.0, -8_000_000.0, 12_000_000.0),
    )
    observations: list[PseudorangeObservation] = []
    for satellite in satellites:
        reading = calculate_pseudorange(
            receiver,
            satellite,
            receiver_clock_bias_seconds=receiver_clock_bias_seconds,
            signal_speed_meters_per_second=SPEED_OF_LIGHT_METERS_PER_SECOND,
        )
        observations.append(
            PseudorangeObservation(
                satellite_ecef=satellite,
                pseudorange_meters=reading.pseudorange_meters,
            )
        )
    return observations


if __name__ == "__main__":
    unittest.main()
