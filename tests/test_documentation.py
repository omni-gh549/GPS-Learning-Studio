from __future__ import annotations

import unittest

from app import DOCUMENTATION_PAGES


class DocumentationTests(unittest.TestCase):
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
        self.assertIn("clock bias", content.lower())

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
        self.assertIn("pseudorange", content.lower())
        self.assertIn("Amber", content)


if __name__ == "__main__":
    unittest.main()
