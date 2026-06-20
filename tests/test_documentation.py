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
