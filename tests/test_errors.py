from __future__ import annotations

import unittest

from gps_sim.errors import (
    ERROR_SOURCE_NAMES,
    ErrorContribution,
    ErrorSourceModel,
    MeasurementError,
    MeasurementErrorModel,
    classroom_error_model,
    clock_error_source,
)
from gps_sim.measurements import SPEED_OF_LIGHT_METERS_PER_SECOND


class ErrorModelTests(unittest.TestCase):
    def test_classroom_model_reports_all_standard_sources(self) -> None:
        model = classroom_error_model(seed=42)

        error = model.sample("satellite-1")

        self.assertEqual(tuple(error.by_source()), ERROR_SOURCE_NAMES)
        self.assertEqual(len(error.contributions), 6)
        self.assertAlmostEqual(
            error.total_meters,
            sum(error.by_source().values()),
        )

    def test_same_seed_and_key_are_reproducible(self) -> None:
        model = classroom_error_model(seed=123)

        first = model.sample("satellite-7")
        second = model.sample("satellite-7")

        self.assertEqual(first, second)

    def test_different_keys_or_seeds_change_sampled_terms(self) -> None:
        model = classroom_error_model(seed=123)
        same_profile_other_key = model.sample("satellite-8")
        other_profile_same_key = classroom_error_model(seed=124).sample("satellite-7")

        self.assertNotEqual(model.sample("satellite-7"), same_profile_other_key)
        self.assertNotEqual(model.sample("satellite-7"), other_profile_same_key)

    def test_apply_to_pseudorange_adds_total_error(self) -> None:
        model = MeasurementErrorModel(
            seed=0,
            satellite_clock=ErrorSourceModel("satellite_clock", 1.0),
            receiver_clock=ErrorSourceModel("receiver_clock", 2.0),
            ionospheric_delay=ErrorSourceModel("ionospheric_delay", 3.0),
            tropospheric_delay=ErrorSourceModel("tropospheric_delay", 4.0),
            multipath=ErrorSourceModel("multipath", 5.0),
            measurement_noise=ErrorSourceModel("measurement_noise", 6.0),
        )

        self.assertEqual(model.sample("fixed").total_meters, 21.0)
        self.assertEqual(model.apply_to_pseudorange(20_200_000.0, "fixed"), 20_200_021.0)

    def test_clock_error_source_converts_seconds_to_range(self) -> None:
        source = clock_error_source(
            "receiver_clock",
            bias_seconds=2.0e-9,
            jitter_seconds=3.0e-9,
        )

        self.assertAlmostEqual(
            source.bias_meters,
            2.0e-9 * SPEED_OF_LIGHT_METERS_PER_SECOND,
        )
        self.assertAlmostEqual(
            source.standard_deviation_meters,
            3.0e-9 * SPEED_OF_LIGHT_METERS_PER_SECOND,
        )

    def test_rejects_invalid_error_models(self) -> None:
        with self.assertRaisesRegex(ValueError, "name"):
            ErrorSourceModel("")
        with self.assertRaisesRegex(ValueError, "standard_deviation"):
            ErrorSourceModel("measurement_noise", standard_deviation_meters=-1.0)
        with self.assertRaisesRegex(ValueError, "unique"):
            MeasurementError(
                (
                    ErrorContribution("measurement_noise", 1.0),
                    ErrorContribution("measurement_noise", 2.0),
                )
            )
        with self.assertRaisesRegex(ValueError, "standard names"):
            MeasurementErrorModel(
                seed=0,
                satellite_clock=ErrorSourceModel("wrong"),
                receiver_clock=ErrorSourceModel("receiver_clock"),
                ionospheric_delay=ErrorSourceModel("ionospheric_delay"),
                tropospheric_delay=ErrorSourceModel("tropospheric_delay"),
                multipath=ErrorSourceModel("multipath"),
                measurement_noise=ErrorSourceModel("measurement_noise"),
            )
        with self.assertRaisesRegex(ValueError, "jitter_seconds"):
            clock_error_source("receiver_clock", jitter_seconds=-1.0)
        with self.assertRaisesRegex(ValueError, "pseudorange_meters"):
            classroom_error_model(seed=0).sample().apply_to_pseudorange(float("nan"))


if __name__ == "__main__":
    unittest.main()
