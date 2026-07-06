from __future__ import annotations

from pathlib import Path
import unittest


def _iter_test_ids(suite: unittest.TestSuite) -> list[str]:
    test_ids: list[str] = []
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            test_ids.extend(_iter_test_ids(test))
        else:
            test_ids.append(test.id())
    return test_ids


class StandardDiscoveryTests(unittest.TestCase):
    def test_default_unittest_discovery_finds_full_suite(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]

        suite = unittest.defaultTestLoader.discover(str(repo_root))
        test_ids = _iter_test_ids(suite)

        self.assertGreaterEqual(len(test_ids), 100)
        self.assertIn(
            "tests.test_editor_api.EditorApiIntegrationTests."
            "test_editor_script_uses_public_simulator_api",
            test_ids,
        )
        self.assertIn(
            "tests.test_visualization.VisualizationTests."
            "test_simulation_state_model_builds_headless_frame",
            test_ids,
        )
