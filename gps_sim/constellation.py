"""Telemetry access for the active GPS satellite constellation."""

from __future__ import annotations

from .runtime import get_visualizer


def get_satellite_states() -> list[dict[str, float | int]]:
    """Return the current propagated state of every simulated satellite."""
    return get_visualizer().satellite_data()


def get_satellite_count() -> int:
    """Return the number of satellites in the active constellation."""
    return len(get_visualizer().satellites)
