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


def play_simulation() -> None:
    """Resume simulation-time playback."""
    get_visualizer().play()


def pause_simulation() -> None:
    """Pause simulation-time playback."""
    get_visualizer().pause()


def step_simulation(seconds: float = 60.0) -> None:
    """Advance simulation time by a fixed number of seconds."""
    get_visualizer().step(seconds)


def set_simulation_time(seconds: float) -> None:
    """Jump the simulator to a specific elapsed simulation time."""
    get_visualizer().set_simulation_time(seconds)


def get_simulation_time() -> float:
    """Return the current elapsed simulation time in seconds."""
    return get_visualizer().get_simulation_time()
