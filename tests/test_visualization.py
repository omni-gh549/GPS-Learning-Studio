from __future__ import annotations

import unittest

from gps_sim.coordinates import CartesianPosition
from gps_sim.ground_stations import GroundStation
from gps_sim.scenario_parameters import SatelliteParameters
from gps_sim.visualization import (
    AccuracyHistoryPoint,
    SatelliteSceneState,
    append_accuracy_history_point,
    build_accuracy_comparison_display,
    build_receiver_measurement_links,
    build_satellite_display_states,
    build_receiver_position_fix_display,
    build_ground_station_scenes,
    build_station_visibility_rows,
    display_position,
    satellite_orbit_display_point,
    satellite_scene_states,
    satellite_telemetry,
)


class VisualizationTests(unittest.TestCase):
    def test_builds_display_states_from_satellite_parameters(self) -> None:
        parameters = (
            SatelliteParameters(
                satellite_id=3,
                radius_meters=26_560_000.0,
                inclination_degrees=55.0,
                longitude_of_ascending_node_degrees=120.0,
                orbital_angle_degrees=45.0,
                orbital_period_seconds=7200.0,
            ),
        )

        states = build_satellite_display_states(parameters, ("amber",))

        self.assertEqual(len(states), 1)
        self.assertEqual(states[0].satellite_id, 3)
        self.assertEqual(states[0].color, "amber")
        self.assertAlmostEqual(
            states[0].angular_speed_radians_per_second,
            2.0 * 3.141592653589793 / 7200.0,
        )

    def test_satellite_telemetry_and_scene_states_are_headless(self) -> None:
        state = build_satellite_display_states(
            (
                SatelliteParameters(
                    satellite_id=1,
                    radius_meters=26_560_000.0,
                    inclination_degrees=10.0,
                    longitude_of_ascending_node_degrees=20.0,
                    orbital_angle_degrees=30.0,
                    orbital_period_seconds=360.0,
                ),
            )
        )[0]

        telemetry = satellite_telemetry((state,), elapsed_seconds=90.0)
        scene_states = satellite_scene_states((state,), elapsed_seconds=90.0)

        self.assertEqual(telemetry[0]["id"], 1)
        self.assertEqual(telemetry[0]["inclination_degrees"], 10.0)
        self.assertEqual(
            telemetry[0]["longitude_of_ascending_node_degrees"],
            20.0,
        )
        self.assertEqual(telemetry[0]["orbital_angle_degrees"], 120.0)
        self.assertEqual(scene_states[0].satellite_id, 1)
        self.assertAlmostEqual(scene_states[0].orbital_angle_degrees, 120.0)

    def test_display_positions_and_orbit_points_are_headless(self) -> None:
        state = build_satellite_display_states(
            (
                SatelliteParameters(
                    satellite_id=1,
                    radius_meters=26_560_000.0,
                    inclination_degrees=0.0,
                    longitude_of_ascending_node_degrees=0.0,
                    orbital_angle_degrees=0.0,
                    orbital_period_seconds=7200.0,
                ),
            )
        )[0]

        point = satellite_orbit_display_point(state, 0.0, scale=1.58)

        self.assertAlmostEqual(point[0], 1.58)
        self.assertAlmostEqual(point[1], 0.0)
        self.assertAlmostEqual(point[2], 0.0)
        self.assertEqual(
            display_position(CartesianPosition(1.0, 0.0, 0.0), 2.0),
            (2.0, 0.0, 0.0),
        )
        with self.assertRaisesRegex(ValueError, "magnitude"):
            display_position(CartesianPosition(0.0, 0.0, 0.0), 1.0)

    def test_builds_station_marker_and_visible_overhead_link(self) -> None:
        station = GroundStation(0.0, 0.0, minimum_elevation_degrees=10.0)
        satellite = SatelliteSceneState(
            satellite_id=7,
            radius_meters=26_560_000.0,
            inclination_degrees=0.0,
            longitude_of_ascending_node_degrees=0.0,
            orbital_angle_degrees=0.0,
        )

        scenes = build_ground_station_scenes(
            (satellite,),
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )

        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0].name, "Equator")
        self.assertGreater(scenes[0].station_ecef.x_meters, 6_000_000.0)
        link = scenes[0].satellite_links[0]
        self.assertEqual(link.satellite_id, 7)
        self.assertAlmostEqual(link.visibility.elevation_degrees, 90.0)
        self.assertTrue(link.visibility.is_visible)

    def test_earth_rotation_changes_link_visibility(self) -> None:
        station = GroundStation(0.0, 0.0)
        satellite = SatelliteSceneState(1, 26_560_000.0, 0.0, 0.0, 0.0)

        overhead = build_ground_station_scenes(
            (satellite,),
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )[0].satellite_links[0]
        opposite_side = build_ground_station_scenes(
            (satellite,),
            {"Equator": station},
            earth_rotation_degrees=180.0,
        )[0].satellite_links[0]

        self.assertTrue(overhead.visibility.is_visible)
        self.assertFalse(opposite_side.visibility.is_visible)

    def test_preserves_station_and_satellite_order(self) -> None:
        satellites = (
            SatelliteSceneState(2, 26_560_000.0, 0.0, 0.0, 0.0),
            SatelliteSceneState(1, 26_560_000.0, 0.0, 90.0, 0.0),
        )
        stations = {
            "First": GroundStation(0.0, 0.0),
            "Second": GroundStation(45.0, 45.0),
        }

        scenes = build_ground_station_scenes(satellites, stations, 0.0)

        self.assertEqual([scene.name for scene in scenes], ["First", "Second"])
        self.assertEqual(
            [link.satellite_id for link in scenes[0].satellite_links],
            [2, 1],
        )

    def test_builds_visibility_table_rows_for_selected_station(self) -> None:
        station = GroundStation(0.0, 0.0, minimum_elevation_degrees=10.0)
        satellites = (
            SatelliteSceneState(7, 26_560_000.0, 0.0, 0.0, 0.0),
            SatelliteSceneState(8, 26_560_000.0, 0.0, 180.0, 0.0),
        )
        scene = build_ground_station_scenes(
            satellites,
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )[0]

        rows = build_station_visibility_rows(scene)

        self.assertEqual([row.satellite_id for row in rows], [7, 8])
        self.assertAlmostEqual(rows[0].azimuth_degrees, 0.0)
        self.assertAlmostEqual(rows[0].elevation_degrees, 90.0)
        self.assertGreater(rows[0].range_meters, 20_000_000.0)
        self.assertTrue(rows[0].is_visible)
        self.assertFalse(rows[1].is_visible)

    def test_builds_receiver_position_fix_display_for_selected_station(self) -> None:
        station = GroundStation(0.0, 0.0, minimum_elevation_degrees=10.0)
        satellites = (
            SatelliteSceneState(1, 26_560_000.0, 0.0, 0.0, 0.0),
            SatelliteSceneState(2, 26_560_000.0, 55.0, 90.0, 60.0),
            SatelliteSceneState(3, 26_560_000.0, 55.0, 180.0, 130.0),
            SatelliteSceneState(4, 26_560_000.0, 35.0, 270.0, 250.0),
        )
        scene = build_ground_station_scenes(
            satellites,
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )[0]

        display = build_receiver_position_fix_display(scene)

        self.assertTrue(display.converged)
        self.assertIsNotNone(display.estimated_receiver_ecef)
        self.assertIsNotNone(display.estimated_clock_bias_seconds)
        self.assertIsNotNone(display.max_abs_residual_meters)
        self.assertIsNotNone(display.rms_residual_meters)
        self.assertIsNotNone(display.horizontal_error_meters)
        self.assertIsNotNone(display.vertical_error_meters)
        self.assertIsNotNone(display.position_error_meters)
        self.assertLess(display.position_error_meters if display.position_error_meters is not None else 1.0, 0.001)
        self.assertLess(
            abs(display.horizontal_error_meters)
            if display.horizontal_error_meters is not None
            else 1.0,
            0.001,
        )
        self.assertLess(
            abs(display.vertical_error_meters)
            if display.vertical_error_meters is not None
            else 1.0,
            0.001,
        )
        self.assertEqual(len(display.residuals_meters), 4)
        self.assertLess(
            display.max_abs_residual_meters
            if display.max_abs_residual_meters is not None
            else 1.0,
            0.001,
        )
        self.assertLess(
            display.rms_residual_meters
            if display.rms_residual_meters is not None
            else 1.0,
            0.001,
        )

    def test_builds_receiver_measurement_links_for_selected_station(self) -> None:
        station = GroundStation(0.0, 0.0, minimum_elevation_degrees=10.0)
        satellites = (
            SatelliteSceneState(7, 26_560_000.0, 0.0, 0.0, 0.0),
            SatelliteSceneState(8, 26_560_000.0, 0.0, 180.0, 0.0),
        )
        scene = build_ground_station_scenes(
            satellites,
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )[0]

        links = build_receiver_measurement_links(
            scene,
            receiver_clock_bias_seconds=0.000_001,
        )

        self.assertEqual([link.satellite_id for link in links], [7, 8])
        self.assertTrue(links[0].is_visible)
        self.assertFalse(links[1].is_visible)
        self.assertGreater(links[0].geometric_range_meters, 20_000_000.0)
        self.assertAlmostEqual(
            links[0].pseudorange_meters - links[0].geometric_range_meters,
            299.792458,
        )
        self.assertEqual(links[0].receiver_clock_bias_seconds, 0.000_001)

    def test_position_fix_display_reports_geometry_diagnostic(self) -> None:
        station = GroundStation(0.0, 0.0)
        scene = build_ground_station_scenes(
            (SatelliteSceneState(1, 26_560_000.0, 0.0, 0.0, 0.0),),
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )[0]

        display = build_receiver_position_fix_display(scene)

        self.assertFalse(display.converged)
        self.assertIsNone(display.estimated_receiver_ecef)
        self.assertIsNone(display.max_abs_residual_meters)
        self.assertIsNone(display.rms_residual_meters)
        self.assertIsNone(display.horizontal_error_meters)
        self.assertIsNone(display.vertical_error_meters)
        self.assertIsNone(display.position_error_meters)
        self.assertIn("at least four", display.diagnostic or "")

    def test_builds_before_after_accuracy_comparison(self) -> None:
        station = GroundStation(0.0, 0.0, minimum_elevation_degrees=10.0)
        satellites = (
            SatelliteSceneState(1, 26_560_000.0, 0.0, 0.0, 0.0),
            SatelliteSceneState(2, 26_560_000.0, 55.0, 90.0, 60.0),
            SatelliteSceneState(3, 26_560_000.0, 55.0, 180.0, 130.0),
            SatelliteSceneState(4, 26_560_000.0, 35.0, 270.0, 250.0),
        )
        scene = build_ground_station_scenes(
            satellites,
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )[0]

        comparison = build_accuracy_comparison_display(scene)

        self.assertTrue(comparison.baseline.converged)
        self.assertTrue(comparison.with_errors.converged)
        self.assertEqual(comparison.error_model_seed, 42)
        self.assertLess(comparison.baseline.position_error_meters or 1.0, 0.001)
        self.assertGreater(comparison.with_errors.position_error_meters or 0.0, 0.1)
        self.assertNotEqual(comparison.total_pseudorange_error_meters, 0.0)

    def test_accuracy_history_is_bounded_and_preserves_error_samples(self) -> None:
        station = GroundStation(0.0, 0.0, minimum_elevation_degrees=10.0)
        satellites = (
            SatelliteSceneState(1, 26_560_000.0, 0.0, 0.0, 0.0),
            SatelliteSceneState(2, 26_560_000.0, 55.0, 90.0, 60.0),
            SatelliteSceneState(3, 26_560_000.0, 55.0, 180.0, 130.0),
            SatelliteSceneState(4, 26_560_000.0, 35.0, 270.0, 250.0),
        )
        scene = build_ground_station_scenes(
            satellites,
            {"Equator": station},
            earth_rotation_degrees=0.0,
        )[0]
        comparison = build_accuracy_comparison_display(scene)

        history: tuple[AccuracyHistoryPoint, ...] = ()
        for index in range(4):
            history = append_accuracy_history_point(
                history,
                elapsed_seconds=float(index),
                comparison=comparison,
                max_points=3,
            )

        self.assertEqual(len(history), 3)
        self.assertEqual([point.elapsed_seconds for point in history], [1.0, 2.0, 3.0])
        self.assertEqual(
            history[-1].error_position_error_meters,
            comparison.with_errors.position_error_meters,
        )
        with self.assertRaisesRegex(ValueError, "max_points"):
            append_accuracy_history_point(history, 4.0, comparison, max_points=0)


if __name__ == "__main__":
    unittest.main()
