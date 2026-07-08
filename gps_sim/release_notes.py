"""Structured release-note helpers for updater and publishing workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseNoteSection:
    """One named group of release-note bullets."""

    title: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class StructuredReleaseNotes:
    """Parsed release notes with an optional summary and named sections."""

    summary: str
    sections: tuple[ReleaseNoteSection, ...]

    @property
    def migration_notes(self) -> tuple[str, ...]:
        """Return bullets from sections that describe user-data migration."""

        return tuple(
            item
            for section in self.sections
            if "migration" in section.title.lower()
            for item in section.items
        )


def parse_release_notes(markdown: str) -> StructuredReleaseNotes:
    """Parse a small markdown release body into summary text and sections."""

    summary_lines: list[str] = []
    sections: list[ReleaseNoteSection] = []
    current_title: str | None = None
    current_items: list[str] = []

    def flush_section() -> None:
        nonlocal current_title, current_items
        if current_title is not None:
            sections.append(
                ReleaseNoteSection(current_title, tuple(item for item in current_items if item))
            )
        current_title = None
        current_items = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            flush_section()
            current_title = line.lstrip("#").strip()
            continue
        if line.startswith(("- ", "* ")):
            item = line[2:].strip()
            if current_title is None:
                current_title = "Changes"
            current_items.append(item)
            continue
        if current_title is None:
            summary_lines.append(line)
        else:
            current_items.append(line)

    flush_section()
    return StructuredReleaseNotes(
        summary="\n".join(summary_lines).strip(),
        sections=tuple(sections),
    )


def format_release_notes(notes: StructuredReleaseNotes, max_items_per_section: int = 3) -> str:
    """Format parsed notes into concise plain text for the update dialog."""

    lines: list[str] = []
    if notes.summary:
        lines.append(notes.summary)
    for section in notes.sections:
        items = section.items[:max_items_per_section]
        if not items:
            continue
        if lines:
            lines.append("")
        lines.append(f"{section.title}:")
        lines.extend(f"- {item}" for item in items)
        remaining = len(section.items) - len(items)
        if remaining > 0:
            lines.append(f"- plus {remaining} more")
    return "\n".join(lines)


__all__ = [
    "ReleaseNoteSection",
    "StructuredReleaseNotes",
    "format_release_notes",
    "parse_release_notes",
]
