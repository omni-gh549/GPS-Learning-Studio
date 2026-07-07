from __future__ import annotations

from pathlib import Path
import unittest


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_gates_publish_on_tests_and_packaged_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        workflow = repo_root / ".github" / "workflows" / "release.yml"
        content = workflow.read_text(encoding="utf-8")

        test_command = "python -m unittest discover -v"
        build_command = "pyinstaller --clean GPS-Learning-Studio.spec"
        smoke_command = r".\dist\GPS-Learning-Studio.exe --smoke-test"
        release_command = "gh release create"

        self.assertIn(test_command, content)
        self.assertIn(build_command, content)
        self.assertIn(smoke_command, content)
        self.assertIn(release_command, content)
        self.assertLess(content.index(test_command), content.index(build_command))
        self.assertLess(content.index(build_command), content.index(smoke_command))
        self.assertLess(content.index(smoke_command), content.index(release_command))
        self.assertIn("if: github.event_name == 'push'", content)

    def test_packaged_smoke_entrypoint_is_documented_in_app(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        content = (repo_root / "app.py").read_text(encoding="utf-8")

        self.assertIn("def run_smoke_test() -> int:", content)
        self.assertIn('"--smoke-test"', content)
        self.assertIn("get_example_scenario(\"strong_geometry\")", content)


if __name__ == "__main__":
    unittest.main()
