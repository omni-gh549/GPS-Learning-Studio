from __future__ import annotations

import unittest

from gps_sim.ground_stations import GroundStation
from gps_sim.visualization import (
    SatelliteSceneState,
    build_ground_station_scenes,
)


class VisualizationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
