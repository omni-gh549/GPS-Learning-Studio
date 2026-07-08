from __future__ import annotations

import unittest

from gps_sim.release_notes import format_release_notes, parse_release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_parses_summary_sections_and_migration_notes(self) -> None:
        notes = parse_release_notes(
            "Stable release.\n\n"
            "## Changes\n"
            "- Adds structured release prompts\n"
            "- Keeps checksummed updates\n\n"
            "## Scenario Migrations\n"
            "- Migrates schema 1 saved scenarios\n"
        )

        self.assertEqual("Stable release.", notes.summary)
        self.assertEqual(["Changes", "Scenario Migrations"], [section.title for section in notes.sections])
        self.assertEqual(("Migrates schema 1 saved scenarios",), notes.migration_notes)

    def test_formats_release_notes_for_update_dialog(self) -> None:
        notes = parse_release_notes(
            "Stable release.\n\n"
            "## Changes\n"
            "- First\n"
            "- Second\n"
            "- Third\n"
            "- Fourth\n"
        )

        formatted = format_release_notes(notes)

        self.assertIn("Stable release.", formatted)
        self.assertIn("Changes:", formatted)
        self.assertIn("- First", formatted)
        self.assertIn("- plus 1 more", formatted)


if __name__ == "__main__":
    unittest.main()
