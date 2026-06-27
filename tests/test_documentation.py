from __future__ import annotations

import unittest

from app import DOCUMENTATION_PAGES, documentation_page_marker


class DocumentationTests(unittest.TestCase):
    def test_lesson_pages_have_learning_metadata(self) -> None:
        lessons = [page for page in DOCUMENTATION_PAGES if page.is_lesson]

        self.assertGreaterEqual(len(lessons), 4)
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
        self.assertIn("horizontal error", content.lower())
        self.assertIn("vertical error", content.lower())
        self.assertIn("pseudorange", content.lower())
        self.assertIn("before", content.lower())
        self.assertIn("after", content.lower())
        self.assertIn("over time", content.lower())
        self.assertIn("Amber", content)


if __name__ == "__main__":
    unittest.main()
