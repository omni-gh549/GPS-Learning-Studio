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


if __name__ == "__main__":
    unittest.main()
