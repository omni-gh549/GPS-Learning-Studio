"""Time propagation and reset controls for the orbital simulation."""

from __future__ import annotations

from .runtime import get_visualizer


def set_orbital_time_scale(multiplier: float) -> None:
    """Set the orbital propagation time-scale multiplier."""
    get_visualizer().set_orbit_speed(multiplier)


def set_earth_rotation_scale(multiplier: float) -> None:
    """Set the Earth rotation time-scale multiplier."""
    get_visualizer().set_earth_speed(multiplier)


def reset_simulation() -> None:
    """Reset the camera orientation and simulation time scales."""
    get_visualizer().reset()
