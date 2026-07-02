from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import (
    DOCUMENTATION_PAGES,
    DocumentationProgress,
    OrbitStudio,
    documentation_page_marker,
    evaluate_documentation_challenge,
    learning_path_completion_summary,
    learning_path_step_for_page,
    load_documentation_progress,
    reset_documentation_progress,
    save_documentation_progress,
)


class DocumentationTests(unittest.TestCase):
    def test_lesson_pages_have_learning_metadata(self) -> None:
        lessons = [page for page in DOCUMENTATION_PAGES if page.is_lesson]

        self.assertGreaterEqual(len(lessons), 5)
        for page in lessons:
            with self.subTest(page=page.title):
                self.assertGreater(page.estimated_duration_minutes or 0, 0)
                self.assertGreaterEqual(len(page.objectives), 2)
                self.assertGreaterEqual(len(page.prerequisites), 1)
                self.assertTrue(all(objective.strip() for objective in page.objectives))
                self.assertTrue(
                    all(prerequisite.strip() for prerequisite in page.prerequisites)
                )

    def test_documentation_completion_markers_are_headless(self) -> None:
        page = next(page for page in DOCUMENTATION_PAGES if page.title == "Quick start")

        self.assertEqual("[ ] ", documentation_page_marker(page, set()))
        self.assertEqual("[x] ", documentation_page_marker(page, {"Quick start"}))

    def test_learning_path_covers_core_course_order(self) -> None:
        expected = (
            ("Quick start", "Orbit telemetry"),
            ("Ground stations", "Visibility"),
            ("Position fixes", "Positioning"),
            ("Error and accuracy", "Accuracy"),
        )

        for sequence, (page_title, milestone) in enumerate(expected, start=1):
            with self.subTest(page=page_title):
                step = learning_path_step_for_page(page_title)
                self.assertIsNotNone(step)
                self.assertEqual(sequence, step.sequence)
                self.assertEqual(milestone, step.milestone)
                self.assertIn(page_title, {page.title for page in DOCUMENTATION_PAGES})

        self.assertIsNone(learning_path_step_for_page("Welcome"))

    def test_learning_path_overview_page_explains_milestones(self) -> None:
        page = next(page for page in DOCUMENTATION_PAGES if page.title == "Learning path")
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(text for section in page.sections for text in section)
        )

        self.assertFalse(page.placeholder)
        self.assertIn("orbit telemetry", content.lower())
        self.assertIn("visibility", content.lower())
        self.assertIn("positioning", content.lower())
        self.assertIn("accuracy", content.lower())
        self.assertIn("Quick start", content)
        self.assertIn("Ground stations", content)
        self.assertIn("Position fixes", content)
        self.assertIn("Error and accuracy", content)

    def test_learning_path_completion_summary_counts_milestones_only(self) -> None:
        complete, total = learning_path_completion_summary(
            frozenset({"Welcome", "Quick start", "Position fixes"})
        )

        self.assertEqual(2, complete)
        self.assertEqual(4, total)

    def test_dynamics_api_documents_playback_controls(self) -> None:
        page = next(page for page in DOCUMENTATION_PAGES if page.title == "Dynamics API")
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(text for section in page.sections for text in section)
        )

        self.assertIn("play_simulation", content)
        self.assertIn("pause_simulation", content)
        self.assertIn("step_simulation", content)
        self.assertIn("set_simulation_time", content)
        self.assertIn("get_simulation_time", content)
        self.assertIn("set_orbital_time_scale", content)

    def test_simulation_time_display_helpers_are_headless(self) -> None:
        self.assertEqual("01:01:01", OrbitStudio._format_simulation_time(3661.0))
        self.assertEqual(90.0, OrbitStudio._parse_simulation_time("01:30"))
        self.assertEqual(3661.0, OrbitStudio._parse_simulation_time("01:01:01"))
        self.assertEqual(42.5, OrbitStudio._parse_simulation_time("42.5"))
        with self.assertRaisesRegex(ValueError, "below 60"):
            OrbitStudio._parse_simulation_time("00:61")

    def test_documentation_progress_round_trips_locally(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            progress = DocumentationProgress(
                completed_pages=frozenset({"Quick start", "Ground stations"}),
                completed_challenges=frozenset({"Ground stations"}),
                last_open_lesson="Ground stations",
            )

            save_documentation_progress(progress, path)
            loaded = load_documentation_progress(path)

        self.assertEqual(progress, loaded)

    def test_documentation_progress_ignores_unknown_or_invalid_entries(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            path.write_text(
                "{\n"
                "  \"completed_pages\": [\"Quick start\", \"Ghost lesson\"],\n"
                "  \"completed_challenges\": [\"Position fixes\", \"Welcome\"],\n"
                "  \"last_open_lesson\": \"Welcome\"\n"
                "}\n",
                encoding="utf-8",
            )

            progress = load_documentation_progress(path)

        self.assertEqual(frozenset({"Quick start"}), progress.completed_pages)
        self.assertEqual(frozenset({"Position fixes"}), progress.completed_challenges)
        self.assertIsNone(progress.last_open_lesson)

    def test_documentation_progress_can_be_reset_locally(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            save_documentation_progress(
                DocumentationProgress(
                    completed_pages=frozenset({"Quick start"}),
                    completed_challenges=frozenset({"Ground stations"}),
                    last_open_lesson="Ground stations",
                ),
                path,
            )

            reset = reset_documentation_progress(path)
            loaded = load_documentation_progress(path)

        self.assertEqual(DocumentationProgress(), reset)
        self.assertEqual(DocumentationProgress(), loaded)

    def test_lesson_pages_include_runnable_editor_snippets(self) -> None:
        lesson_titles = {
            "Quick start",
            "Ground stations",
            "Position fixes",
            "Error and accuracy",
        }
        lessons = [page for page in DOCUMENTATION_PAGES if page.title in lesson_titles]

        self.assertEqual(lesson_titles, {page.title for page in lessons})
        for page in lessons:
            with self.subTest(page=page.title):
                self.assertGreaterEqual(len(page.snippets), 1)
                for snippet in page.snippets:
                    self.assertTrue(snippet.title.strip())
                    self.assertIn("import ", snippet.code)
                    compile(snippet.code, f"<documentation snippet: {page.title}>", "exec")

    def test_challenge_pages_define_lightweight_checks(self) -> None:
        challenge_pages = [
            page
            for page in DOCUMENTATION_PAGES
            if "Coding challenge" in dict(page.sections)
        ]

        self.assertGreaterEqual(len(challenge_pages), 3)
        for page in challenge_pages:
            with self.subTest(page=page.title):
                self.assertIsNotNone(page.challenge_check)
                self.assertGreaterEqual(len(page.challenge_check.requirements), 4)

    def test_challenge_pages_include_compilable_sample_solutions(self) -> None:
        challenge_pages = [
            page
            for page in DOCUMENTATION_PAGES
            if page.challenge_check is not None
        ]

        self.assertGreaterEqual(len(challenge_pages), 3)
        for page in challenge_pages:
            with self.subTest(page=page.title):
                self.assertIsNotNone(page.sample_solution)
                solution = page.sample_solution or ""
                self.assertIn("print(", solution)
                compile(solution, f"<documentation solution: {page.title}>", "exec")

    def test_documentation_challenge_check_reports_missing_focus_items(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Ground stations"
        )

        feedback = evaluate_documentation_challenge(
            page,
            "import gps_sim.ground_stations as ground_stations\n"
            "station = ground_stations.GroundStation(0.0, 0.0)\n"
            "print(station)\n",
        )

        self.assertFalse(feedback.passed)
        self.assertTrue(any("orbital_to_eci" in message for message in feedback.messages))
        self.assertTrue(any("calculate_visibility" in message for message in feedback.messages))

    def test_documentation_challenge_check_accepts_expected_structure(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Error and accuracy"
        )
        source = (
            "from gps_sim.coordinates import CartesianPosition\n"
            "import gps_sim.errors as errors\n"
            "import gps_sim.measurements as measurements\n"
            "import gps_sim.positioning as positioning\n"
            "receiver = CartesianPosition(1.0, 2.0, 3.0)\n"
            "for source_name in errors.ERROR_SOURCE_NAMES:\n"
            "    model = errors.classroom_error_model(seed=42)\n"
            "    model = model.with_source_settings(source_name, enabled=True)\n"
            "    pseudorange = model.apply_to_pseudorange(10.0, source_name)\n"
            "    observation = positioning.PseudorangeObservation(receiver, pseudorange)\n"
            "    fix = positioning.solve_position([observation, observation, observation, observation])\n"
            "    report = positioning.calculate_position_error(fix, receiver, None)\n"
            "    print(source_name, report.position_error_meters)\n"
        )

        feedback = evaluate_documentation_challenge(page, source)

        self.assertTrue(feedback.passed)

    def test_documentation_challenge_check_reports_syntax_first(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Position fixes"
        )

        feedback = evaluate_documentation_challenge(page, "for\n")

        self.assertFalse(feedback.passed)
        self.assertEqual(1, len(feedback.messages))
        self.assertIn("syntax", feedback.messages[0].lower())

    def test_ground_station_page_is_a_complete_guided_lesson(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Ground stations"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(
                text
                for section in page.sections
                for text in section
            )
        )

        self.assertFalse(page.placeholder)
        self.assertIn("Learning objectives", content)
        self.assertIn("latitude", content.lower())
        self.assertIn("longitude", content.lower())
        self.assertIn("elevation mask", content.lower())
        self.assertIn("pass", content.lower())

    def test_ground_station_lesson_includes_an_executable_challenge_path(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Ground stations"
        )
        sections = dict(page.sections)
        lesson_text = "\n".join(sections.values())

        self.assertIn("Coding challenge", sections)
        self.assertIn("Success check", sections)
        self.assertIn("GroundStation", lesson_text)
        self.assertIn("orbital_to_eci", lesson_text)
        self.assertIn("eci_to_ecef", lesson_text)
        self.assertIn("calculate_visibility", lesson_text)

    def test_measurements_api_page_documents_range_and_pseudorange(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Measurements API"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(
                text
                for section in page.sections
                for text in section
            )
        )

        self.assertFalse(page.placeholder)
        self.assertIn("gps_sim.measurements", content)
        self.assertIn("ReceiverClockBias", content)
        self.assertIn("geometric_range", content)
        self.assertIn("calculate_pseudorange", content)
        self.assertIn("receiver clock bias", content.lower())

    def test_positioning_api_page_documents_solver(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Positioning API"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(
                text
                for section in page.sections
                for text in section
            )
        )

        self.assertFalse(page.placeholder)
        self.assertIn("gps_sim.positioning", content)
        self.assertIn("PseudorangeObservation", content)
        self.assertIn("solve_position", content)
        self.assertIn("calculate_position_error", content)
        self.assertIn("calculate_dilution_of_precision", content)
        self.assertIn("gdop", content.lower())
        self.assertIn("pdop", content.lower())
        self.assertIn("hdop", content.lower())
        self.assertIn("vdop", content.lower())
        self.assertIn("horizontal", content.lower())
        self.assertIn("vertical", content.lower())
        self.assertIn("3d", content.lower())
        self.assertIn("clock bias", content.lower())

    def test_errors_api_page_documents_seeded_error_sources(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Errors API"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(
                text
                for section in page.sections
                for text in section
            )
        )

        self.assertFalse(page.placeholder)
        self.assertIn("gps_sim.errors", content)
        self.assertIn("classroom_error_model", content)
        self.assertIn("satellite clock", content.lower())
        self.assertIn("receiver clock", content.lower())
        self.assertIn("ionospheric delay", content.lower())
        self.assertIn("tropospheric delay", content.lower())
        self.assertIn("multipath", content.lower())
        self.assertIn("measurement noise", content.lower())
        self.assertIn("seed", content.lower())
        self.assertIn("enabled", content.lower())
        self.assertIn("disabled", content.lower())
        self.assertIn("scaled", content.lower())

    def test_positioning_docs_explain_four_satellite_requirement(self) -> None:
        pages = {
            page.title: page
            for page in DOCUMENTATION_PAGES
            if page.title in {"Positioning API", "Position fixes"}
        }
        content = "\n".join(
            text
            for page in pages.values()
            for section in page.sections
            for text in section
        ).lower()

        self.assertIn("why four satellites", content)
        self.assertIn("four unknowns", content)
        self.assertIn("x, y, z", content)
        self.assertIn("clock bias", content)
        self.assertIn("four equations", content)

    def test_position_fixes_page_is_a_complete_guided_lesson(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Position fixes"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(
                text
                for section in page.sections
                for text in section
            )
        )

        self.assertFalse(page.placeholder)
        self.assertIn("Learning objectives", content)
        self.assertIn("trilateration", content.lower())
        self.assertIn("pseudorange", content.lower())
        self.assertIn("clock bias", content.lower())
        self.assertIn("residual", content.lower())

    def test_position_fixes_lesson_includes_solver_challenge_path(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Position fixes"
        )
        sections = dict(page.sections)
        lesson_text = "\n".join(sections.values())

        self.assertIn("Coding challenge", sections)
        self.assertIn("Success check", sections)
        self.assertIn("Stretch goal", sections)
        self.assertIn("CartesianPosition", lesson_text)
        self.assertIn("calculate_pseudorange", lesson_text)
        self.assertIn("PseudorangeObservation", lesson_text)
        self.assertIn("solve_position", lesson_text)

    def test_error_accuracy_page_is_a_complete_controlled_experiment_lesson(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Error and accuracy"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(
                text
                for section in page.sections
                for text in section
            )
        )

        self.assertFalse(page.placeholder)
        self.assertIn("Learning objectives", content)
        self.assertIn("controlled", content.lower())
        self.assertIn("measurement error", content.lower())
        self.assertIn("poor satellite geometry", content.lower())
        self.assertIn("residual", content.lower())
        self.assertIn("horizontal", content.lower())
        self.assertIn("vertical", content.lower())
        self.assertIn("3D", content)
        self.assertIn("DOP", content)

    def test_error_accuracy_lesson_includes_experiment_challenge_path(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Error and accuracy"
        )
        sections = dict(page.sections)
        lesson_text = "\n".join(sections.values())

        self.assertIn("Coding challenge", sections)
        self.assertIn("Success check", sections)
        self.assertIn("Stretch goal", sections)
        self.assertIn("classroom_error_model", lesson_text)
        self.assertIn("ERROR_SOURCE_NAMES", lesson_text)
        self.assertIn("with_source_settings", lesson_text)
        self.assertIn("apply_to_pseudorange", lesson_text)
        self.assertIn("PseudorangeObservation", lesson_text)
        self.assertIn("solve_position", lesson_text)
        self.assertIn("calculate_position_error", lesson_text)

    def test_orbital_view_documents_measurement_links(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Orbital view"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(
                text
                for section in page.sections
                for text in section
            )
        )

        self.assertIn("Measurement links", content)
        self.assertIn("Editable scenario", content)
        self.assertIn("satellite count", content.lower())
        self.assertIn("receiver clock bias", content.lower())
        self.assertIn("horizontal error", content.lower())
        self.assertIn("vertical error", content.lower())
        self.assertIn("pseudorange", content.lower())
        self.assertIn("before", content.lower())
        self.assertIn("after", content.lower())
        self.assertIn("over time", content.lower())
        self.assertIn("scenario file", content.lower())
        self.assertIn("simulation time", content.lower())
        self.assertIn("Amber", content)

    def test_scenario_files_api_documents_versioned_save_load(self) -> None:
        page = next(
            page for page in DOCUMENTATION_PAGES if page.title == "Scenario files API"
        )
        content = "\n".join(
            (page.title, page.eyebrow, page.summary)
            + tuple(text for section in page.sections for text in section)
        )

        self.assertIn("gps_sim.scenarios", content)
        self.assertIn("VersionedScenario", content)
        self.assertIn("save_scenario_file", content)
        self.assertIn("load_scenario_file", content)
        self.assertIn("schema_version", content)
        self.assertIn("simulation timestamp", content.lower())


if __name__ == "__main__":
    unittest.main()
