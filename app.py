from __future__ import annotations

import builtins
import contextlib
import io
import json
import keyword
import math
import os
import queue
import random
import re
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from gps_sim.coordinates import (
    CartesianPosition,
    WGS84_SEMI_MAJOR_AXIS_METERS,
    orbital_to_eci,
)
from gps_sim.ground_stations import create_station, list_stations, update_station
from gps_sim.runtime import bind_visualizer
from gps_sim.scenario_parameters import (
    ConstellationParameters,
    ReceiverParameters,
    SatelliteParameters,
    build_satellite_parameters,
)
from gps_sim.scenarios import (
    VersionedScenario,
    get_example_scenario,
    list_example_scenarios,
    load_scenario_file,
    save_scenario_file,
)
from gps_sim.simulation_time import SimulationClock
from gps_sim.updater import CURRENT_VERSION, download_and_install, find_update, is_packaged
from gps_sim.visualization import (
    AccuracyComparisonDisplay,
    AccuracyHistoryPoint,
    GroundStationScene,
    ReceiverPositionFixDisplay,
    SatelliteSceneState,
    append_accuracy_history_point,
    build_accuracy_comparison_display,
    build_receiver_measurement_links,
    build_ground_station_scenes,
    build_station_visibility_rows,
)


BG = "#242628"
PANEL = "#2b2e31"
BORDER = "#4a4e52"
TEXT = "#d7d9dc"
MUTED = "#92979c"
ACCENT = "#9bb7cc"
EARTH = "#6f91a8"
ORBIT = "#555f67"
SATELLITE_COLORS = ("#d7a86e", "#7db6a6", "#b58dc7", "#d6cc75")
STATION = "#ef8f72"
VISIBLE_LINK = "#86d5b4"
MEASUREMENT_LINK = "#d6cc75"
SATELLITE_ORBIT_RADIUS_METERS = WGS84_SEMI_MAJOR_AXIS_METERS * 1.58
PROGRESS_SCHEMA_VERSION = 1

SIMULATOR_COMPLETIONS = (
    ("import gps_sim.constellation as constellation", "import gps_sim.constellation as constellation", "#8eb6d8"),
    ("import gps_sim.coordinates as coordinates", "import gps_sim.coordinates as coordinates", "#8eb6d8"),
    ("import gps_sim.dynamics as dynamics", "import gps_sim.dynamics as dynamics", "#8eb6d8"),
    ("import gps_sim.errors as errors", "import gps_sim.errors as errors", "#8eb6d8"),
    ("import gps_sim.ground_stations as ground_stations", "import gps_sim.ground_stations as ground_stations", "#8eb6d8"),
    ("import gps_sim.measurements as measurements", "import gps_sim.measurements as measurements", "#8eb6d8"),
    ("import gps_sim.positioning as positioning", "import gps_sim.positioning as positioning", "#8eb6d8"),
    ("import gps_sim.scenario_parameters as scenario_parameters", "import gps_sim.scenario_parameters as scenario_parameters", "#8eb6d8"),
    ("import gps_sim.scenarios as scenarios", "import gps_sim.scenarios as scenarios", "#8eb6d8"),
    ("scenarios.list_example_scenarios()", "scenarios.list_example_scenarios()", "#7db6a6"),
    ("import gps_sim.visibility as visibility", "import gps_sim.visibility as visibility", "#8eb6d8"),
    ("constellation.get_satellite_states()  -> list[dict]", "constellation.get_satellite_states()", "#7db6a6"),
    ("constellation.get_satellite_count()  -> int", "constellation.get_satellite_count()", "#7db6a6"),
    ("dynamics.set_orbital_time_scale(2.0)", "dynamics.set_orbital_time_scale(2.0)", "#d7a86e"),
    ("dynamics.set_earth_rotation_scale(0.5)", "dynamics.set_earth_rotation_scale(0.5)", "#d7a86e"),
    ("dynamics.reset_simulation()", "dynamics.reset_simulation()", "#d7a86e"),
    ("ground_stations.GroundStation(0.0, 0.0)", "ground_stations.GroundStation(0.0, 0.0)", "#7db6a6"),
    ("ground_stations.create_station(\"Home\", 0.0, 0.0)", "ground_stations.create_station(\"Home\", 0.0, 0.0)", "#7db6a6"),
    ("ground_stations.update_station(\"Home\", altitude_meters=10.0)", "ground_stations.update_station(\"Home\", altitude_meters=10.0)", "#7db6a6"),
    ("ground_stations.list_stations()  -> dict", "ground_stations.list_stations()", "#7db6a6"),
    ("ground_stations.remove_station(\"Home\")", "ground_stations.remove_station(\"Home\")", "#7db6a6"),
    ("coordinates.orbital_to_eci(...)", "coordinates.orbital_to_eci(26560000.0, 55.0, 0.0, 0.0)", "#7db6a6"),
    ("coordinates.eci_to_ecef(...)", "coordinates.eci_to_ecef(eci, 0.0)", "#7db6a6"),
    ("coordinates.ecef_to_local_horizon(...)", "coordinates.ecef_to_local_horizon(ecef, station)", "#7db6a6"),
    ("errors.classroom_error_model(seed=42)", "errors.classroom_error_model(seed=42)", "#7db6a6"),
    ("error_model.with_source_settings(...)", "error_model.with_source_settings(\"multipath\", enabled=False)", "#7db6a6"),
    ("errors.clock_error_source(...)", "errors.clock_error_source(\"receiver_clock\", bias_seconds=1e-8)", "#7db6a6"),
    ("measurements.ReceiverClockBias(...)", "measurements.ReceiverClockBias(seconds=0.000001)", "#7db6a6"),
    ("measurements.geometric_range(...)", "measurements.geometric_range(receiver_ecef, satellite_ecef)", "#7db6a6"),
    ("measurements.calculate_pseudorange(...)", "measurements.calculate_pseudorange(receiver_ecef, satellite_ecef)", "#7db6a6"),
    ("positioning.PseudorangeObservation(...)", "positioning.PseudorangeObservation(satellite_ecef, pseudorange_meters)", "#7db6a6"),
    ("positioning.solve_position(...)", "positioning.solve_position(observations)", "#7db6a6"),
    ("positioning.calculate_position_error(...)", "positioning.calculate_position_error(fix, station_ecef, station)", "#7db6a6"),
    ("positioning.calculate_dilution_of_precision(...)", "positioning.calculate_dilution_of_precision(observations, station_ecef, station)", "#7db6a6"),
    ("visibility.calculate_visibility(...)", "visibility.calculate_visibility(ecef, station)", "#7db6a6"),
    ("print(value)  e.g. print(\"Satellite state\")", "print()", "#c59bcf"),
    ("len(iterable)  e.g. len(states)", "len()", "#c59bcf"),
    ("range(stop)  e.g. range(4)", "range(4)", "#c59bcf"),
    ("round(number, ndigits)  e.g. round(angle, 2)", "round(angle, 2)", "#c59bcf"),
    ("min(iterable)  e.g. min(angles)", "min(angles)", "#c59bcf"),
    ("max(iterable)  e.g. max(angles)", "max(angles)", "#c59bcf"),
    ("sum(iterable)  e.g. sum(values)", "sum(values)", "#c59bcf"),
    ("enumerate(iterable)  e.g. enumerate(states)", "enumerate(states)", "#c59bcf"),
    ("sorted(iterable)  e.g. sorted(values)", "sorted(values)", "#c59bcf"),
    ("abs(number)  e.g. abs(error)", "abs(error)", "#c59bcf"),
)

@dataclass(frozen=True)
class DocumentationSnippet:
    title: str
    code: str


@dataclass(frozen=True)
class ChallengeRequirement:
    label: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class DocumentationChallengeCheck:
    success_message: str
    requirements: tuple[ChallengeRequirement, ...]


@dataclass(frozen=True)
class ChallengeFeedback:
    passed: bool
    messages: tuple[str, ...]


@dataclass(frozen=True)
class LearningPathStep:
    sequence: int
    page_title: str
    milestone: str
    outcome: str


@dataclass(frozen=True)
class DocumentationProgress:
    completed_pages: frozenset[str] = frozenset()
    completed_challenges: frozenset[str] = frozenset()
    last_open_lesson: str | None = None


@dataclass(frozen=True)
class DocumentationPage:
    title: str
    eyebrow: str
    summary: str
    sections: tuple[tuple[str, str], ...]
    placeholder: bool = False
    objectives: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    estimated_duration_minutes: int | None = None
    snippets: tuple[DocumentationSnippet, ...] = ()
    challenge_check: DocumentationChallengeCheck | None = None
    sample_solution: str | None = None
    lesson_scenario_key: str | None = None

    @property
    def is_lesson(self) -> bool:
        return self.estimated_duration_minutes is not None


def default_documentation_progress_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "GPS Learning Studio" / "documentation-progress.json"
    return Path.home() / ".gps-learning-studio" / "documentation-progress.json"


def _valid_documentation_titles() -> set[str]:
    return {page.title for page in DOCUMENTATION_PAGES}


def _valid_challenge_titles() -> set[str]:
    return {page.title for page in DOCUMENTATION_PAGES if page.challenge_check is not None}


def _valid_lesson_titles() -> set[str]:
    return {page.title for page in DOCUMENTATION_PAGES if page.is_lesson}


def load_documentation_progress(path: Path | None = None) -> DocumentationProgress:
    progress_path = path or default_documentation_progress_path()
    try:
        raw = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DocumentationProgress()
    if not isinstance(raw, dict):
        return DocumentationProgress()

    valid_titles = _valid_documentation_titles()
    valid_challenges = _valid_challenge_titles()
    valid_lessons = _valid_lesson_titles()
    completed_pages = frozenset(
        title
        for title in raw.get("completed_pages", ())
        if isinstance(title, str) and title in valid_titles
    )
    completed_challenges = frozenset(
        title
        for title in raw.get("completed_challenges", ())
        if isinstance(title, str) and title in valid_challenges
    )
    last_open_lesson = raw.get("last_open_lesson")
    if not isinstance(last_open_lesson, str) or last_open_lesson not in valid_lessons:
        last_open_lesson = None
    return DocumentationProgress(
        completed_pages=completed_pages,
        completed_challenges=completed_challenges,
        last_open_lesson=last_open_lesson,
    )


def save_documentation_progress(
    progress: DocumentationProgress,
    path: Path | None = None,
) -> None:
    progress_path = path or default_documentation_progress_path()
    payload = {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "completed_pages": sorted(progress.completed_pages),
        "completed_challenges": sorted(progress.completed_challenges),
        "last_open_lesson": progress.last_open_lesson,
    }
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def reset_documentation_progress(path: Path | None = None) -> DocumentationProgress:
    progress = DocumentationProgress()
    save_documentation_progress(progress, path)
    return progress


def learning_path_step_for_page(page_title: str) -> LearningPathStep | None:
    for step in LEARNING_PATH:
        if step.page_title == page_title:
            return step
    return None


def learning_path_completion_summary(
    completed_pages: set[str] | frozenset[str],
) -> tuple[int, int]:
    complete = sum(1 for step in LEARNING_PATH if step.page_title in completed_pages)
    return complete, len(LEARNING_PATH)


def lesson_scenario_for_page(page: DocumentationPage) -> VersionedScenario | None:
    """Return the bundled starting scenario for a lesson page, if one is set."""

    if page.lesson_scenario_key is None:
        return None
    return get_example_scenario(page.lesson_scenario_key).scenario


def evaluate_documentation_challenge(
    page: DocumentationPage,
    source: str,
) -> ChallengeFeedback:
    if page.challenge_check is None:
        return ChallengeFeedback(False, ("This page does not define a challenge check.",))
    if not source.strip():
        return ChallengeFeedback(False, ("Add your challenge script to the editor first.",))
    try:
        compile(source, "<documentation challenge>", "exec")
    except SyntaxError as error:
        line = error.lineno or "?"
        return ChallengeFeedback(
            False,
            (f"Fix the Python syntax on line {line}: {error.msg}.",),
        )

    missing = []
    for requirement in page.challenge_check.requirements:
        if not any(token in source for token in requirement.tokens):
            missing.append(f"Use {requirement.label}.")
    if missing:
        return ChallengeFeedback(False, tuple(missing))
    return ChallengeFeedback(True, (page.challenge_check.success_message,))


DOCUMENTATION_PAGES = (
    DocumentationPage(
        "Welcome",
        "START HERE",
        "Learn Python by changing a live orbital simulation and reading its telemetry.",
        (
            ("Your workspace", "The left pane is a rotatable model of Earth, named ground stations, and the active satellite constellation. The right pane is a Python editor with output below it."),
            ("First run", "Press F5 or choose Run. The starter script imports the constellation module, reads every satellite state, and prints the result."),
            ("A good next experiment", "Change the script so it prints only each satellite ID and orbital angle. Run it several times and watch the angles advance."),
        ),
    ),
    DocumentationPage(
        "Learning path",
        "COURSE MAP",
        "Follow the core course from orbit telemetry through visibility, positioning, and accuracy.",
        (
            (
                "How to use the path",
                "Work through the four milestone lessons in order. Mark each lesson complete after running the lab snippet and checking the expected output or visual result.",
            ),
            (
                "1. Orbit telemetry",
                "Quick start introduces live satellite telemetry, orbital angles, and simulation time controls. This is the baseline for every later observation.",
            ),
            (
                "2. Visibility",
                "Ground stations turns orbital positions into local azimuth, elevation, range, and pass visibility for a receiver on Earth.",
            ),
            (
                "3. Positioning",
                "Position fixes builds pseudoranges into a four-unknown receiver solution with residuals and clock-bias checks.",
            ),
            (
                "4. Accuracy",
                "Error and accuracy compares clean and error-affected fixes so students can separate measurement error from poor satellite geometry.",
            ),
            (
                "Completion target",
                "The path is complete when Quick start, Ground stations, Position fixes, and Error and accuracy are all marked complete. Challenge checks on the three lab lessons provide stronger evidence than reading alone.",
            ),
        ),
        objectives=(
            "Connect orbit telemetry to receiver visibility.",
            "Use pseudoranges to solve a receiver position.",
            "Interpret accuracy experiments from residuals, position error, and DOP.",
        ),
        prerequisites=("Welcome",),
        estimated_duration_minutes=65,
    ),
    DocumentationPage(
        "Quick start",
        "5 MINUTE LESSON",
        "Run a script, inspect changing telemetry, and speed up the simulation.",
        (
            ("1. Read the constellation", "import gps_sim.constellation as constellation\n\nfor satellite in constellation.get_satellite_states():\n    print(satellite[\"id\"], satellite[\"orbital_angle_degrees\"])"),
            ("2. Change time", "import gps_sim.dynamics as dynamics\n\ndynamics.set_orbital_time_scale(20.0)"),
            ("3. Reset", "dynamics.reset_simulation()\n\nReset restores both time scales and returns the camera to its starting angle."),
        ),
        objectives=(
            "Run the starter script from the editor.",
            "Inspect live constellation telemetry.",
            "Change the simulation time scale and reset it.",
        ),
        prerequisites=("No Python experience required.",),
        estimated_duration_minutes=5,
        lesson_scenario_key="strong_geometry",
        snippets=(
            DocumentationSnippet(
                "Read constellation telemetry",
                "import gps_sim.constellation as constellation\n\n"
                "print(\"Satellite orbital angles:\")\n"
                "for satellite in constellation.get_satellite_states():\n"
                "    print(satellite[\"id\"], round(satellite[\"orbital_angle_degrees\"], 2))\n",
            ),
            DocumentationSnippet(
                "Speed up then reset",
                "import gps_sim.dynamics as dynamics\n\n"
                "dynamics.set_orbital_time_scale(20.0)\n"
                "print(\"Orbital time scale set to 20x\")\n"
                "dynamics.reset_simulation()\n"
                "print(\"Simulation reset\")\n",
            ),
        ),
    ),
    DocumentationPage(
        "Constellation API",
        "API REFERENCE",
        "Read the size and current propagated state of the simulated constellation.",
        (
            ("Import", "import gps_sim.constellation as constellation"),
            ("get_satellite_states()", "constellation.get_satellite_states()\n\nReturns a list of dictionaries. Each dictionary contains id, inclination_degrees, longitude_of_ascending_node_degrees, and orbital_angle_degrees."),
            ("get_satellite_count()", "constellation.get_satellite_count()\n\nReturns the number of satellites in the active constellation."),
        ),
    ),
    DocumentationPage(
        "Dynamics API",
        "API REFERENCE",
        "Control playback, simulation time, orbital propagation, Earth rotation, and reset.",
        (
            ("Import", "import gps_sim.dynamics as dynamics"),
            ("play_simulation() / pause_simulation()", "dynamics.pause_simulation()\ndynamics.play_simulation()\n\nPauses or resumes simulation-time playback without resetting the current timestamp."),
            ("step_simulation(seconds)", "dynamics.step_simulation(60.0)\n\nAdvances the simulation by a fixed number of seconds. This works while paused, which is useful for frame-by-frame classroom observations."),
            ("set_simulation_time(seconds)", "dynamics.set_simulation_time(3600.0)\nprint(dynamics.get_simulation_time())\n\nJumps to a specific elapsed simulation time and reports the current timestamp in seconds."),
            ("set_orbital_time_scale(multiplier)", "dynamics.set_orbital_time_scale(2.0)\n\nSets orbital speed. Use 1.0 for real time, a larger number to accelerate, or 0.0 for a stopped clock."),
            ("set_earth_rotation_scale(multiplier)", "dynamics.set_earth_rotation_scale(0.5)\n\nSets the visual Earth rotation speed independently of satellite motion."),
            ("reset_simulation()", "dynamics.reset_simulation()\n\nRestores the camera and both time scales to their defaults."),
        ),
    ),
    DocumentationPage(
        "Ground stations API",
        "API REFERENCE",
        "Create and manage named stationary receivers using validated geodetic inputs.",
        (
            ("Import", "import gps_sim.ground_stations as ground_stations"),
            ("GroundStation(...)", "station = ground_stations.GroundStation(\n    latitude_degrees=57.1497,\n    longitude_degrees=-2.0943,\n    altitude_meters=65.0,\n    minimum_elevation_degrees=10.0,\n)\n\nLatitude and longitude are expressed in degrees, altitude in meters, and the elevation mask in degrees. Coordinates and masks are validated when the immutable station is constructed."),
            ("create_station(...)", "ground_stations.create_station(\"Aberdeen\", 57.1497, -2.0943, 65.0, 10.0)\n\nCreates a validated station under a unique name and returns it."),
            ("update_station(...)", "ground_stations.update_station(\"Aberdeen\", minimum_elevation_degrees=15.0)\n\nUpdates only the supplied fields and returns a new immutable station."),
            ("list_stations()", "stations = ground_stations.list_stations()\nprint(stations)\n\nReturns a dictionary snapshot keyed by station name."),
            ("remove_station(name)", "removed = ground_stations.remove_station(\"Aberdeen\")\n\nRemoves and returns the named station."),
        ),
    ),
    DocumentationPage(
        "Coordinates API",
        "API REFERENCE",
        "Convert circular satellite orbits and WGS84 stations through inertial, Earth-fixed, and local horizon frames.",
        (
            ("Import", "import gps_sim.coordinates as coordinates"),
            ("orbital_to_eci(...)", "eci = coordinates.orbital_to_eci(\n    radius_meters=26_560_000.0,\n    inclination_degrees=55.0,\n    longitude_of_ascending_node_degrees=30.0,\n    orbital_angle_degrees=120.0,\n)\n\nReturns a CartesianPosition in the Earth-centred inertial frame. The educational orbit model assumes a circular orbit."),
            ("eci_to_ecef(...)", "ecef = coordinates.eci_to_ecef(eci, earth_rotation_degrees=15.0)\n\nRotates an inertial position into the Earth-centred, Earth-fixed frame. Use ecef_to_eci(...) for the inverse conversion."),
            ("station_to_ecef(station)", "station_ecef = coordinates.station_to_ecef(station)\n\nConverts a GroundStation latitude, longitude, and altitude to a WGS84 Earth-fixed position."),
            ("ecef_to_local_horizon(...)", "local = coordinates.ecef_to_local_horizon(ecef, station)\nprint(local.east_meters, local.north_meters, local.up_meters)\n\nReturns station-centred east, north, and up coordinates. Use local_horizon_to_ecef(...) for the inverse conversion."),
        ),
    ),
    DocumentationPage(
        "Visibility API",
        "API REFERENCE",
        "Calculate satellite look angles, slant range, and elevation-mask visibility from a ground station.",
        (
            ("Import", "import gps_sim.visibility as visibility"),
            ("calculate_visibility(...)", "look = visibility.calculate_visibility(satellite_ecef, station)\nprint(look.azimuth_degrees)\nprint(look.elevation_degrees)\nprint(look.range_meters)\nprint(look.is_visible)\n\nAzimuth is measured clockwise from north. A satellite is visible when its elevation is greater than or equal to the station minimum elevation angle."),
            ("local_horizon_visibility(...)", "look = visibility.local_horizon_visibility(local, minimum_elevation_degrees=10.0)\n\nCalculates the same result directly from east, north, and up coordinates. Exact zenith uses an azimuth of 0 degrees by convention."),
        ),
    ),
    DocumentationPage(
        "Measurements API",
        "API REFERENCE",
        "Calculate geometric range and receiver-clock-biased pseudorange measurements.",
        (
            ("Import", "import gps_sim.measurements as measurements"),
            ("ReceiverClockBias(...)", "clock_bias = measurements.ReceiverClockBias(seconds=0.000001)\nprint(clock_bias.range_error_meters())\n\nA positive receiver clock bias makes the receiver clock run ahead of GPS time and adds distance to the pseudorange. Use ReceiverClockBias.from_range_error(...) when a lesson starts from the equivalent range error in meters."),
            ("geometric_range(...)", "range_m = measurements.geometric_range(receiver_ecef, satellite_ecef)\nprint(range_m)\n\nReturns the straight-line distance between receiver and satellite Earth-fixed positions in meters."),
            ("calculate_pseudorange(...)", "reading = measurements.calculate_pseudorange(\n    receiver_ecef,\n    satellite_ecef,\n    receiver_clock_bias=clock_bias,\n)\nprint(reading.geometric_range_meters)\nprint(reading.pseudorange_meters)\n\nPseudorange equals geometric range plus receiver clock bias multiplied by the signal speed. The default signal speed is the speed of light."),
        ),
    ),
    DocumentationPage(
        "Positioning API",
        "API REFERENCE",
        "Estimate receiver ECEF position, clock bias, and satellite-geometry quality from pseudoranges.",
        (
            ("Import", "import gps_sim.positioning as positioning"),
            ("PseudorangeObservation(...)", "observation = positioning.PseudorangeObservation(\n    satellite_ecef=satellite_ecef,\n    pseudorange_meters=reading.pseudorange_meters,\n)\n\nEach observation pairs one satellite Earth-fixed position with the pseudorange measured by the receiver."),
            ("Why four satellites?", "A 3D GPS fix has four unknowns: receiver x, y, z, and receiver clock bias. Each pseudorange adds one distance equation, so three satellites can constrain position only if the receiver clock is already known. A fourth satellite gives the solver enough independent equations to estimate clock bias at the same time as position."),
            ("solve_position(...)", "fix = positioning.solve_position(observations)\nprint(fix.receiver_ecef)\nprint(fix.receiver_clock_bias_seconds)\nprint(fix.residuals_meters)\n\nThe solver estimates x, y, z, and receiver clock bias together. A clear ValueError is raised when fewer than four satellites are supplied or the satellite geometry is singular."),
            ("calculate_position_error(...)", "report = positioning.calculate_position_error(\n    fix,\n    true_receiver_ecef=station_ecef,\n    reference_station=station,\n)\nprint(report.max_abs_residual_meters)\nprint(report.horizontal_error_meters)\nprint(report.vertical_error_meters)\nprint(report.position_error_meters)\n\nThe report keeps residual statistics and splits ECEF position error into local horizontal, vertical, and 3D components for accuracy experiments."),
            ("calculate_dilution_of_precision(...)", "dop = positioning.calculate_dilution_of_precision(\n    observations,\n    receiver_ecef=station_ecef,\n    reference_station=station,\n)\nprint(dop.gdop, dop.pdop)\nprint(dop.hdop, dop.vdop)\n\nGDOP, PDOP, HDOP, and VDOP are dimensionless satellite-geometry multipliers. Lower values mean the satellites are spread in a way that better constrains the receiver solution."),
        ),
    ),
    DocumentationPage(
        "Errors API",
        "API REFERENCE",
        "Build deterministic, seedable pseudorange error scenarios.",
        (
            ("Import", "import gps_sim.errors as errors"),
            ("classroom_error_model(seed)", "model = errors.classroom_error_model(seed=42)\nerror = model.sample(measurement_key=\"satellite-1\")\nprint(error.by_source())\nprint(error.total_meters)\n\nThe classroom profile includes satellite clock, receiver clock, ionospheric delay, tropospheric delay, multipath, and measurement noise. The same seed and measurement key always produce the same offsets."),
            ("with_source_settings(...)", "iono_only = model.with_source_settings(\"multipath\", enabled=False)\nscaled = model.with_source_settings(\"ionospheric_delay\", scale=2.0)\nprint(iono_only.sample(\"satellite-1\").by_source())\nprint(scaled.source(\"ionospheric_delay\").scale)\n\nEach standard error source can be enabled, disabled, or scaled independently. Disabled sources still appear in by_source() with a zero-meter contribution, so lessons can compare one component at a time."),
            ("clock_error_source(...)", "receiver_clock = errors.clock_error_source(\n    \"receiver_clock\",\n    bias_seconds=35e-9,\n    jitter_seconds=4e-9,\n)\nprint(receiver_clock.bias_meters)\n\nClock errors are converted from seconds into equivalent range offsets using the speed of light by default."),
            ("apply_to_pseudorange(...)", "reading_with_error = model.apply_to_pseudorange(\n    reading.pseudorange_meters,\n    measurement_key=\"satellite-1\",\n)\n\nThis keeps the clean geometric and clock-biased measurement available while adding a reproducible total error for accuracy experiments."),
        ),
    ),
    DocumentationPage(
        "Scenario files API",
        "API REFERENCE",
        "Save and load versioned classroom scenario files.",
        (
            ("Import", "import gps_sim.scenario_parameters as scenario_parameters\nimport gps_sim.scenarios as scenarios"),
            ("VersionedScenario(...)", "scenario = scenarios.VersionedScenario(\n    constellation=scenario_parameters.ConstellationParameters(satellite_count=6),\n    receiver=scenario_parameters.ReceiverParameters(clock_bias_microseconds=2.0),\n    simulation_time_seconds=600.0,\n    orbital_speed_multiplier=10.0,\n)\n\nA scenario captures the editable constellation, receiver, simulation timestamp, and orbital speed multiplier needed to reproduce a classroom starting state."),
            ("list_example_scenarios()", "for example in scenarios.list_example_scenarios():\n    print(example.name, example.description)\n\nThe bundled examples cover strong geometry, poor geometry, clock bias, atmospheric delay, and multipath labs. Each example provides a validated VersionedScenario and optional focus_error_sources for the matching Errors API experiment."),
            ("get_example_scenario(...)", "example = scenarios.get_example_scenario(\"clock_bias\")\nscenario = example.scenario\nprint(scenario.receiver.clock_bias_microseconds)\n\nUse a key such as strong_geometry, poor_geometry, clock_bias, atmospheric_delay, or multipath to load the same classroom starting point from code, the visualizer Example control, or a lesson's Lesson state action."),
            ("save_scenario_file(...)", "scenarios.save_scenario_file(path, scenario)\n\nWrites a formatted `.gps-scenario.json` file with an explicit schema_version field so future releases can migrate saved labs deliberately."),
            ("load_scenario_file(...)", "loaded = scenarios.load_scenario_file(path)\n\nLoads only supported schema versions and validates every constellation and receiver field before the visualizer applies the state. Invalid files raise ValueError with a focused message."),
        ),
    ),
    DocumentationPage(
        "Editor and files",
        "WORKSPACE GUIDE",
        "Use the editor like a small Python lab built around the simulation.",
        (
            ("Suggestions", "Function suggestions appear while you type imports, module names, or functions. Use Up and Down to select, Enter or Tab to insert, and Escape to close."),
            ("Files", "Open loads a Python file. Import inserts a standard Python import. Save writes the current script to disk."),
            ("Run and output", "Run or F5 executes the editor. Printed values, errors, and tracebacks appear in the output pane. Ctrl+S saves and Ctrl+O opens a script."),
        ),
    ),
    DocumentationPage(
        "Orbital view",
        "VISUALIZER GUIDE",
        "Connect the values in your code to motion in the model.",
        (
            ("Camera", "Hold the left mouse button and drag to rotate the view around Earth."),
            ("Satellites", "Hover a satellite marker to display its Globalstar ID. Each colored marker follows its own inclined orbital plane."),
            ("Ground stations", "Orange markers show named stations. Click a front-facing marker to select it and inspect the live azimuth, elevation, range, and visibility table. Green dashed links connect stations to satellites at or above the elevation mask."),
            ("Editable scenario", "Use the visualizer controls to change satellite count, inclination, orbital altitude, receiver latitude, receiver longitude, elevation mask, and receiver clock bias. Applying changes redraws the constellation and receiver fix. Example loads bundled classroom scenarios for strong geometry, poor geometry, clock bias, atmospheric delay, and multipath. Save writes a versioned scenario file; Load validates one and restores the constellation, receiver, simulation time, and orbital speed."),
            ("Measurement links", "Amber dashed links show the selected receiver's simplified pseudorange measurements to the satellites used by the position-fix display. Brighter amber means the satellite is above the station elevation mask; muted amber keeps below-mask observations visible for comparison."),
            ("Position fix", "The selected station also drives a simulated pseudorange fix. The receiver panel compares the true station position with the estimated position, clock bias, residual statistics, horizontal error, vertical error, and 3D error; a dashed yellow ring marks the estimated receiver on Earth."),
            ("Accuracy comparison", "The accuracy panel compares a clean before fix with an after fix that applies the seeded classroom error model, then plots both 3D position errors over time so students can see the error source change the solution."),
            ("Time", "The satellites use classroom-scale orbital periods near 114 minutes. Increase the orbital time scale to make changes easier to observe during a lesson."),
        ),
    ),
    DocumentationPage(
        "Challenge: Find the leader",
        "PRACTICE",
        "Use list processing to find the satellite with the greatest orbital angle.",
        (
            ("Task", "Read the satellite states, find the dictionary with the largest orbital_angle_degrees value, and print its ID."),
            ("Hint", "states = constellation.get_satellite_states()\nleader = max(states, key=lambda satellite: satellite[\"orbital_angle_degrees\"])\nprint(leader[\"id\"])"),
            ("Stretch goal", "Sort all satellites by orbital angle and print a numbered leaderboard."),
        ),
    ),
    DocumentationPage(
        "Ground stations",
        "15 MINUTE LESSON",
        "Use station coordinates and an elevation mask to decide which satellites are visible.",
        (
            (
                "Learning objectives",
                "Explain how latitude and longitude place a receiver on Earth, interpret azimuth and elevation, and use an elevation mask to identify a simple satellite pass.",
            ),
            (
                "1. Place a receiver",
                "Latitude measures north or south of the equator. Longitude measures east or west of Greenwich. Altitude raises the receiver above the WGS84 reference ellipsoid.\n\n"
                "import gps_sim.ground_stations as ground_stations\n\n"
                "station = ground_stations.GroundStation(\n"
                "    latitude_degrees=57.1497,\n"
                "    longitude_degrees=-2.0943,\n"
                "    altitude_meters=65.0,\n"
                "    minimum_elevation_degrees=10.0,\n"
                ")",
            ),
            (
                "2. Read the sky",
                "Azimuth points clockwise from north. Elevation measures upward from the local horizon: 0 degrees is on the horizon and 90 degrees is directly overhead. Range is the straight-line distance to the satellite.",
            ),
            (
                "3. Apply the elevation mask",
                "Buildings, terrain, and atmospheric effects make low satellites less useful. This lesson uses a 10-degree mask, so a satellite is visible when its elevation is at least 10 degrees. A pass begins when elevation crosses above the mask and ends when it drops below it.",
            ),
            (
                "Guided lab",
                "Run this snapshot several times and compare the visible IDs as the orbital angles advance. The fixed Earth rotation angle keeps the coordinate-frame assumption explicit for this exercise.\n\n"
                "import gps_sim.constellation as constellation\n"
                "import gps_sim.coordinates as coordinates\n"
                "import gps_sim.visibility as visibility\n\n"
                "for satellite in constellation.get_satellite_states():\n"
                "    eci = coordinates.orbital_to_eci(\n"
                "        26_560_000.0,\n"
                "        satellite[\"inclination_degrees\"],\n"
                "        satellite[\"longitude_of_ascending_node_degrees\"],\n"
                "        satellite[\"orbital_angle_degrees\"],\n"
                "    )\n"
                "    ecef = coordinates.eci_to_ecef(eci, earth_rotation_degrees=0.0)\n"
                "    look = visibility.calculate_visibility(ecef, station)\n"
                "    print(satellite[\"id\"], round(look.elevation_degrees, 1), look.is_visible)",
            ),
            (
                "Coding challenge",
                "Create a station at latitude 0 degrees and longitude 0 degrees with a 20-degree elevation mask. Calculate every satellite's visibility, then print only the IDs of satellites above the mask.",
            ),
            (
                "Success check",
                "Your code should use GroundStation, orbital_to_eci, eci_to_ecef, and calculate_visibility. The printed list may change as the simulation advances, but every printed satellite must have is_visible equal to True.",
            ),
            (
                "Stretch goal",
                "Print each visible satellite's azimuth, elevation, and range in kilometres. Run the script repeatedly and note when a satellite rises above or sets below the 20-degree mask.",
            ),
        ),
        objectives=(
            "Create a receiver from latitude, longitude, altitude, and elevation mask.",
            "Convert satellite coordinates into the station horizon frame.",
            "Interpret azimuth, elevation, range, and pass visibility.",
        ),
        prerequisites=(
            "Quick start",
            "Ground stations API",
            "Coordinates API",
            "Visibility API",
        ),
        estimated_duration_minutes=15,
        lesson_scenario_key="strong_geometry",
        snippets=(
            DocumentationSnippet(
                "Find visible satellites",
                "import gps_sim.constellation as constellation\n"
                "import gps_sim.coordinates as coordinates\n"
                "import gps_sim.ground_stations as ground_stations\n"
                "import gps_sim.visibility as visibility\n\n"
                "station = ground_stations.GroundStation(\n"
                "    latitude_degrees=0.0,\n"
                "    longitude_degrees=0.0,\n"
                "    altitude_meters=0.0,\n"
                "    minimum_elevation_degrees=20.0,\n"
                ")\n\n"
                "visible_ids = []\n"
                "for satellite in constellation.get_satellite_states():\n"
                "    eci = coordinates.orbital_to_eci(\n"
                "        26_560_000.0,\n"
                "        satellite[\"inclination_degrees\"],\n"
                "        satellite[\"longitude_of_ascending_node_degrees\"],\n"
                "        satellite[\"orbital_angle_degrees\"],\n"
                "    )\n"
                "    ecef = coordinates.eci_to_ecef(eci, earth_rotation_degrees=0.0)\n"
                "    look = visibility.calculate_visibility(ecef, station)\n"
                "    if look.is_visible:\n"
                "        visible_ids.append(satellite[\"id\"])\n\n"
                "print(\"Visible above 20 degrees:\", visible_ids)\n",
            ),
        ),
        challenge_check=DocumentationChallengeCheck(
            "Ground-station challenge structure looks ready: run it and confirm every printed satellite is above the 20-degree mask.",
            (
                ChallengeRequirement("GroundStation for the receiver", ("GroundStation",)),
                ChallengeRequirement("orbital_to_eci to build satellite ECI positions", ("orbital_to_eci",)),
                ChallengeRequirement("eci_to_ecef to rotate into Earth-fixed coordinates", ("eci_to_ecef",)),
                ChallengeRequirement("calculate_visibility for look angles and mask status", ("calculate_visibility",)),
                ChallengeRequirement("is_visible filtering before printing IDs", ("is_visible",)),
            ),
        ),
        sample_solution=(
            "import gps_sim.constellation as constellation\n"
            "import gps_sim.coordinates as coordinates\n"
            "import gps_sim.ground_stations as ground_stations\n"
            "import gps_sim.visibility as visibility\n\n"
            "station = ground_stations.GroundStation(\n"
            "    latitude_degrees=0.0,\n"
            "    longitude_degrees=0.0,\n"
            "    altitude_meters=0.0,\n"
            "    minimum_elevation_degrees=20.0,\n"
            ")\n\n"
            "visible_ids = []\n"
            "for satellite in constellation.get_satellite_states():\n"
            "    eci = coordinates.orbital_to_eci(\n"
            "        26_560_000.0,\n"
            "        satellite[\"inclination_degrees\"],\n"
            "        satellite[\"longitude_of_ascending_node_degrees\"],\n"
            "        satellite[\"orbital_angle_degrees\"],\n"
            "    )\n"
            "    ecef = coordinates.eci_to_ecef(eci, earth_rotation_degrees=0.0)\n"
            "    look = visibility.calculate_visibility(ecef, station)\n"
            "    if look.is_visible:\n"
            "        visible_ids.append(satellite[\"id\"])\n\n"
            "print(\"Visible satellite IDs:\", visible_ids)\n"
        ),
    ),
    DocumentationPage(
        "Position fixes",
        "20 MINUTE LESSON",
        "Work from pseudorange measurements to a solved receiver position and clock bias.",
        (
            (
                "Learning objectives",
                "Explain trilateration as intersecting distance constraints, account for receiver clock bias, build PseudorangeObservation inputs, and check a solved receiver position against a known truth.",
            ),
            (
                "1. Start with ranges",
                "A geometric range is the straight-line distance from a receiver to one satellite. A pseudorange is what the receiver measures before its clock is perfectly synchronized, so it includes geometric range plus receiver clock bias converted into meters.\n\n"
                "import gps_sim.measurements as measurements\n\n"
                "clock_bias = measurements.ReceiverClockBias(seconds=0.000001)\n"
                "print(round(clock_bias.range_error_meters(), 3))",
            ),
            (
                "Why four satellites?",
                "Each pseudorange measurement says the receiver is somewhere on a sphere around one satellite, but the measured range also includes receiver clock error. A normal 3D fix therefore solves four unknowns together: x, y, z, and clock bias. Four independent satellites provide the four equations needed for that solve; extra satellites improve the least-squares fit and expose residual error.",
            ),
            (
                "2. Build observations",
                "The solver needs one satellite Earth-fixed position and one pseudorange per observation. This worked lab uses a known receiver position so you can verify the solution.\n\n"
                "from gps_sim.coordinates import CartesianPosition\n"
                "import gps_sim.measurements as measurements\n"
                "import gps_sim.positioning as positioning\n\n"
                "receiver = CartesianPosition(1_000_000.0, -2_000_000.0, 3_000_000.0)\n"
                "satellites = [\n"
                "    CartesianPosition(20_200_000.0, 0.0, 0.0),\n"
                "    CartesianPosition(0.0, 21_200_000.0, 1_000_000.0),\n"
                "    CartesianPosition(1_500_000.0, 0.0, 22_200_000.0),\n"
                "    CartesianPosition(-20_500_000.0, -8_000_000.0, 12_000_000.0),\n"
                "]\n"
                "observations = []\n"
                "for satellite in satellites:\n"
                "    reading = measurements.calculate_pseudorange(\n"
                "        receiver,\n"
                "        satellite,\n"
                "        receiver_clock_bias_seconds=0.0000015,\n"
                "    )\n"
                "    observations.append(positioning.PseudorangeObservation(\n"
                "        satellite_ecef=satellite,\n"
                "        pseudorange_meters=reading.pseudorange_meters,\n"
                "    ))",
            ),
            (
                "3. Solve and check",
                "Run the solver, compare estimated x, y, z with the true receiver, and inspect the residuals. In this noise-free lab the maximum residual should be tiny.\n\n"
                "fix = positioning.solve_position(observations)\n"
                "print(fix.converged, fix.iterations)\n"
                "print(round(fix.receiver_ecef.x_meters - receiver.x_meters, 6))\n"
                "print(round(fix.receiver_ecef.y_meters - receiver.y_meters, 6))\n"
                "print(round(fix.receiver_ecef.z_meters - receiver.z_meters, 6))\n"
                "print(round(fix.receiver_clock_bias_seconds, 10))\n"
                "print(round(max(abs(value) for value in fix.residuals_meters), 6))",
            ),
            (
                "Coding challenge",
                "Add a fifth satellite observation, then change one pseudorange by 25 meters to simulate measurement error. Solve again and print the 3D position error plus every residual. The position should still solve, but the residuals should reveal that the measurements no longer agree perfectly.",
            ),
            (
                "Success check",
                "Your code should use CartesianPosition, calculate_pseudorange, PseudorangeObservation, and solve_position. With the original four noise-free observations, the solved receiver coordinates should be within 0.01 meters of the true receiver and the clock bias should be within 1e-10 seconds.",
            ),
            (
                "Stretch goal",
                "Move one satellite close to another and rerun the solver. If the geometry becomes singular or poorly conditioned, catch the ValueError and explain why satellite placement matters as much as the number of satellites.",
            ),
        ),
        objectives=(
            "Generate noise-free pseudoranges from known satellite positions.",
            "Solve receiver x, y, z, and clock bias from four observations.",
            "Use residuals to check whether the measurements agree.",
        ),
        prerequisites=(
            "Quick start",
            "Measurements API",
            "Positioning API",
        ),
        estimated_duration_minutes=20,
        lesson_scenario_key="clock_bias",
        snippets=(
            DocumentationSnippet(
                "Solve a clean four-satellite fix",
                "from gps_sim.coordinates import CartesianPosition\n"
                "import gps_sim.measurements as measurements\n"
                "import gps_sim.positioning as positioning\n\n"
                "receiver = CartesianPosition(1_000_000.0, -2_000_000.0, 3_000_000.0)\n"
                "satellites = [\n"
                "    CartesianPosition(20_200_000.0, 0.0, 0.0),\n"
                "    CartesianPosition(0.0, 21_200_000.0, 1_000_000.0),\n"
                "    CartesianPosition(1_500_000.0, 0.0, 22_200_000.0),\n"
                "    CartesianPosition(-20_500_000.0, -8_000_000.0, 12_000_000.0),\n"
                "]\n\n"
                "observations = []\n"
                "for satellite in satellites:\n"
                "    reading = measurements.calculate_pseudorange(\n"
                "        receiver,\n"
                "        satellite,\n"
                "        receiver_clock_bias_seconds=0.0000015,\n"
                "    )\n"
                "    observations.append(positioning.PseudorangeObservation(\n"
                "        satellite_ecef=satellite,\n"
                "        pseudorange_meters=reading.pseudorange_meters,\n"
                "    ))\n\n"
                "fix = positioning.solve_position(observations)\n"
                "print(fix.converged, fix.iterations)\n"
                "print(round(fix.receiver_ecef.x_meters - receiver.x_meters, 6))\n"
                "print(round(fix.receiver_clock_bias_seconds, 10))\n",
            ),
        ),
        challenge_check=DocumentationChallengeCheck(
            "Position-fix challenge structure looks ready: run it and inspect the printed residuals and 3D error.",
            (
                ChallengeRequirement("CartesianPosition for receiver and satellites", ("CartesianPosition",)),
                ChallengeRequirement("calculate_pseudorange to generate observations", ("calculate_pseudorange",)),
                ChallengeRequirement("PseudorangeObservation inputs for the solver", ("PseudorangeObservation",)),
                ChallengeRequirement("solve_position for the receiver fix", ("solve_position",)),
                ChallengeRequirement("residual output for measurement disagreement", ("residual", "residuals_meters")),
            ),
        ),
        sample_solution=(
            "from gps_sim.coordinates import CartesianPosition\n"
            "import gps_sim.measurements as measurements\n"
            "import gps_sim.positioning as positioning\n\n"
            "receiver = CartesianPosition(1_000_000.0, -2_000_000.0, 3_000_000.0)\n"
            "satellites = [\n"
            "    CartesianPosition(20_200_000.0, 0.0, 0.0),\n"
            "    CartesianPosition(0.0, 21_200_000.0, 1_000_000.0),\n"
            "    CartesianPosition(1_500_000.0, 0.0, 22_200_000.0),\n"
            "    CartesianPosition(-20_500_000.0, -8_000_000.0, 12_000_000.0),\n"
            "    CartesianPosition(18_000_000.0, 16_000_000.0, -8_000_000.0),\n"
            "]\n\n"
            "observations = []\n"
            "for satellite in satellites:\n"
            "    reading = measurements.calculate_pseudorange(\n"
            "        receiver,\n"
            "        satellite,\n"
            "        receiver_clock_bias_seconds=0.0000015,\n"
            "    )\n"
            "    observations.append(positioning.PseudorangeObservation(satellite, reading.pseudorange_meters))\n"
            "observations[-1] = positioning.PseudorangeObservation(\n"
            "    observations[-1].satellite_ecef,\n"
            "    observations[-1].pseudorange_meters + 25.0,\n"
            ")\n\n"
            "fix = positioning.solve_position(observations)\n"
            "report = positioning.calculate_position_error(fix, receiver, None)\n"
            "print(\"3D error meters:\", round(report.position_error_meters, 3))\n"
            "for residual in fix.residuals_meters:\n"
            "    print(\"residual meters:\", round(residual, 3))\n"
        ),
    ),
    DocumentationPage(
        "Error and accuracy",
        "25 MINUTE LESSON",
        "Run controlled experiments that isolate GPS error sources and satellite geometry.",
        (
            (
                "Learning objectives",
                "Distinguish measurement error from poor satellite geometry, isolate one pseudorange error source at a time, interpret residuals, and compare horizontal, vertical, 3D, and DOP accuracy metrics.",
            ),
            (
                "1. Build a clean reference fix",
                "Start each accuracy experiment with a noise-free set of pseudoranges. The clean fix is the control case, so any later change can be traced to the error model or the satellite geometry you changed.\n\n"
                "from gps_sim.coordinates import CartesianPosition\n"
                "import gps_sim.measurements as measurements\n"
                "import gps_sim.positioning as positioning\n\n"
                "receiver = CartesianPosition(1_000_000.0, -2_000_000.0, 3_000_000.0)\n"
                "satellites = [\n"
                "    CartesianPosition(20_200_000.0, 0.0, 0.0),\n"
                "    CartesianPosition(0.0, 21_200_000.0, 1_000_000.0),\n"
                "    CartesianPosition(1_500_000.0, 0.0, 22_200_000.0),\n"
                "    CartesianPosition(-20_500_000.0, -8_000_000.0, 12_000_000.0),\n"
                "    CartesianPosition(18_000_000.0, 16_000_000.0, -8_000_000.0),\n"
                "]\n"
                "clean_observations = []\n"
                "for satellite in satellites:\n"
                "    reading = measurements.calculate_pseudorange(receiver, satellite)\n"
                "    clean_observations.append(positioning.PseudorangeObservation(satellite, reading.pseudorange_meters))\n"
                "clean_fix = positioning.solve_position(clean_observations)\n"
                "print(round(max(abs(value) for value in clean_fix.residuals_meters), 6))",
            ),
            (
                "2. Add one source at a time",
                "A controlled measurement experiment keeps the same receiver, satellites, seed, and solver settings while changing one error source. Disable every source except the one under test, then compare the solved position and residuals with the clean control.\n\n"
                "import gps_sim.errors as errors\n\n"
                "source_under_test = \"ionospheric_delay\"\n"
                "model = errors.classroom_error_model(seed=42)\n"
                "for source_name in errors.ERROR_SOURCE_NAMES:\n"
                "    model = model.with_source_settings(source_name, enabled=(source_name == source_under_test))\n\n"
                "error_observations = []\n"
                "for index, satellite in enumerate(satellites):\n"
                "    reading = measurements.calculate_pseudorange(receiver, satellite)\n"
                "    pseudorange = model.apply_to_pseudorange(reading.pseudorange_meters, f\"satellite-{index}\")\n"
                "    error_observations.append(positioning.PseudorangeObservation(satellite, pseudorange))\n"
                "error_fix = positioning.solve_position(error_observations)\n"
                "for residual in error_fix.residuals_meters:\n"
                "    print(round(residual, 3))",
            ),
            (
                "3. Read the accuracy report",
                "Residuals show how well the measurements agree with the solved receiver. Position error shows how far the solution moved from the known truth. A low residual can still hide a biased position when every pseudorange was shifted in a similar way.",
            ),
            (
                "4. Separate error from geometry",
                "DOP metrics describe satellite placement, not measurement quality. Reuse the same pseudoranges with two satellite layouts: a spread-out layout should have lower GDOP, PDOP, HDOP, and VDOP than a clustered layout. If geometry is poor, small measurement errors can create a large position error.",
            ),
            (
                "Guided lab",
                "Run the one-source experiment for ionospheric_delay, multipath, and measurement_noise. Keep seed=42 for every run, record the maximum absolute residual, then change only the scale for the active source and observe how the error grows.\n\n"
                "for scale in (0.0, 1.0, 2.0):\n"
                "    scaled_model = model.with_source_settings(source_under_test, scale=scale)\n"
                "    print(source_under_test, scale, scaled_model.sample(\"satellite-0\").by_source())",
            ),
            (
                "Coding challenge",
                "Write a script that loops over every name in ERROR_SOURCE_NAMES. For each run, enable only that source, solve the receiver position, and print the source name, maximum residual, and 3D position error.",
            ),
            (
                "Success check",
                "Your code should use classroom_error_model, ERROR_SOURCE_NAMES, with_source_settings, apply_to_pseudorange, PseudorangeObservation, solve_position, and calculate_position_error. The same seed and satellite keys should reproduce the same table on repeated runs.",
            ),
            (
                "Stretch goal",
                "Create a poor-geometry satellite list by moving satellites close together, calculate GDOP, PDOP, HDOP, and VDOP, then rerun the same measurement-noise experiment. Explain why geometry can amplify the same pseudorange noise into a larger horizontal or vertical error.",
            ),
        ),
        objectives=(
            "Run clean control fixes and seeded error experiments.",
            "Isolate one pseudorange error source at a time.",
            "Compare residuals, position error, and DOP geometry metrics.",
        ),
        prerequisites=(
            "Position fixes",
            "Errors API",
            "Positioning API",
        ),
        estimated_duration_minutes=25,
        lesson_scenario_key="atmospheric_delay",
        snippets=(
            DocumentationSnippet(
                "Compare one error source",
                "from gps_sim.coordinates import CartesianPosition\n"
                "import gps_sim.errors as errors\n"
                "import gps_sim.measurements as measurements\n"
                "import gps_sim.positioning as positioning\n\n"
                "receiver = CartesianPosition(1_000_000.0, -2_000_000.0, 3_000_000.0)\n"
                "satellites = [\n"
                "    CartesianPosition(20_200_000.0, 0.0, 0.0),\n"
                "    CartesianPosition(0.0, 21_200_000.0, 1_000_000.0),\n"
                "    CartesianPosition(1_500_000.0, 0.0, 22_200_000.0),\n"
                "    CartesianPosition(-20_500_000.0, -8_000_000.0, 12_000_000.0),\n"
                "    CartesianPosition(18_000_000.0, 16_000_000.0, -8_000_000.0),\n"
                "]\n"
                "source_under_test = \"ionospheric_delay\"\n"
                "model = errors.classroom_error_model(seed=42)\n"
                "for source_name in errors.ERROR_SOURCE_NAMES:\n"
                "    model = model.with_source_settings(\n"
                "        source_name,\n"
                "        enabled=(source_name == source_under_test),\n"
                "    )\n\n"
                "observations = []\n"
                "for index, satellite in enumerate(satellites):\n"
                "    reading = measurements.calculate_pseudorange(receiver, satellite)\n"
                "    pseudorange = model.apply_to_pseudorange(\n"
                "        reading.pseudorange_meters,\n"
                "        f\"satellite-{index}\",\n"
                "    )\n"
                "    observations.append(positioning.PseudorangeObservation(satellite, pseudorange))\n\n"
                "fix = positioning.solve_position(observations)\n"
                "print(source_under_test)\n"
                "print(round(max(abs(value) for value in fix.residuals_meters), 3))\n",
            ),
        ),
        challenge_check=DocumentationChallengeCheck(
            "Accuracy challenge structure looks ready: run it twice and confirm the seeded table repeats.",
            (
                ChallengeRequirement("classroom_error_model for seeded errors", ("classroom_error_model",)),
                ChallengeRequirement("ERROR_SOURCE_NAMES loop coverage", ("ERROR_SOURCE_NAMES",)),
                ChallengeRequirement("with_source_settings to isolate one source", ("with_source_settings",)),
                ChallengeRequirement("apply_to_pseudorange to add each source's offset", ("apply_to_pseudorange",)),
                ChallengeRequirement("PseudorangeObservation inputs for the solver", ("PseudorangeObservation",)),
                ChallengeRequirement("solve_position for each source", ("solve_position",)),
                ChallengeRequirement("calculate_position_error for 3D error", ("calculate_position_error",)),
            ),
        ),
        sample_solution=(
            "from gps_sim.coordinates import CartesianPosition\n"
            "import gps_sim.errors as errors\n"
            "import gps_sim.measurements as measurements\n"
            "import gps_sim.positioning as positioning\n\n"
            "receiver = CartesianPosition(1_000_000.0, -2_000_000.0, 3_000_000.0)\n"
            "satellites = [\n"
            "    CartesianPosition(20_200_000.0, 0.0, 0.0),\n"
            "    CartesianPosition(0.0, 21_200_000.0, 1_000_000.0),\n"
            "    CartesianPosition(1_500_000.0, 0.0, 22_200_000.0),\n"
            "    CartesianPosition(-20_500_000.0, -8_000_000.0, 12_000_000.0),\n"
            "    CartesianPosition(18_000_000.0, 16_000_000.0, -8_000_000.0),\n"
            "]\n\n"
            "for source_name in errors.ERROR_SOURCE_NAMES:\n"
            "    model = errors.classroom_error_model(seed=42)\n"
            "    for candidate in errors.ERROR_SOURCE_NAMES:\n"
            "        model = model.with_source_settings(candidate, enabled=(candidate == source_name))\n"
            "    observations = []\n"
            "    for index, satellite in enumerate(satellites):\n"
            "        reading = measurements.calculate_pseudorange(receiver, satellite)\n"
            "        pseudorange = model.apply_to_pseudorange(\n"
            "            reading.pseudorange_meters,\n"
            "            f\"satellite-{index}\",\n"
            "        )\n"
            "        observations.append(positioning.PseudorangeObservation(satellite, pseudorange))\n"
            "    fix = positioning.solve_position(observations)\n"
            "    report = positioning.calculate_position_error(fix, receiver, None)\n"
            "    max_residual = max(abs(value) for value in fix.residuals_meters)\n"
            "    print(source_name, round(max_residual, 3), round(report.position_error_meters, 3))\n"
        ),
    ),
)


LEARNING_PATH = (
    LearningPathStep(
        1,
        "Quick start",
        "Orbit telemetry",
        "Read satellite IDs, orbital angles, and simulation time controls.",
    ),
    LearningPathStep(
        2,
        "Ground stations",
        "Visibility",
        "Turn satellite positions into azimuth, elevation, range, and pass visibility.",
    ),
    LearningPathStep(
        3,
        "Position fixes",
        "Positioning",
        "Generate pseudoranges and recover receiver position plus clock bias.",
    ),
    LearningPathStep(
        4,
        "Error and accuracy",
        "Accuracy",
        "Compare clean and error-affected fixes using residuals, position error, and DOP.",
    ),
)


def rounded_rectangle(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
                      radius: float, **kwargs) -> int:
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class RoundedPanel(tk.Canvas):
    def __init__(self, master: tk.Misc, padding: int = 2, **kwargs):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0, **kwargs)
        self.padding = padding
        self.body = tk.Frame(self, bg=PANEL)
        self.window_id = self.create_window(padding, padding, anchor="nw", window=self.body)
        self.bind("<Configure>", self._resize)

    def _resize(self, event: tk.Event) -> None:
        self.delete("panel")
        rounded_rectangle(
            self, 1, 1, event.width - 1, event.height - 1, 15,
            fill=PANEL, outline=BORDER, width=1, tags="panel",
        )
        self.tag_lower("panel")
        inset = self.padding + 8
        self.coords(self.window_id, inset, inset)
        self.itemconfigure(
            self.window_id,
            width=max(1, event.width - inset * 2),
            height=max(1, event.height - inset * 2),
        )


class RoundedButton(tk.Canvas):
    def __init__(self, master: tk.Misc, text: str, command, width: int = 58, height: int = 30):
        super().__init__(
            master, width=width, height=height, bg=PANEL,
            highlightthickness=0, bd=0, cursor="hand2",
        )
        self.command = command
        self.label = text
        self.hovered = False
        self.bind("<Enter>", lambda _event: self._set_hover(True))
        self.bind("<Leave>", lambda _event: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._click)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        fill = "#41464a" if self.hovered else "#34383b"
        rounded_rectangle(self, 1, 1, int(self["width"]) - 1, int(self["height"]) - 1, 8,
                          fill=fill, outline=BORDER, width=1)
        self.create_text(
            int(self["width"]) / 2, int(self["height"]) / 2,
            text=self.label, fill=TEXT, font=("Segoe UI", 9),
        )

    def _set_hover(self, hovered: bool) -> None:
        self.hovered = hovered
        self._draw()

    def set_text(self, text: str) -> None:
        self.label = text
        self._draw()

    def _click(self, event: tk.Event) -> None:
        if 0 <= event.x <= int(self["width"]) and 0 <= event.y <= int(self["height"]):
            self.command()


class SidebarIconButton(tk.Canvas):
    def __init__(self, master: tk.Misc, command):
        super().__init__(
            master, width=42, height=42, bg=BG, highlightthickness=0,
            bd=0, cursor="hand2",
        )
        self.command = command
        self.active = False
        self.hovered = False
        self.bind("<Enter>", lambda _event: self._set_hover(True))
        self.bind("<Leave>", lambda _event: self._set_hover(False))
        self.bind("<ButtonRelease-1>", lambda _event: self.command())
        self._draw()

    def set_active(self, active: bool) -> None:
        self.active = active
        self._draw()

    def _set_hover(self, hovered: bool) -> None:
        self.hovered = hovered
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        if self.active or self.hovered:
            rounded_rectangle(
                self, 1, 1, 41, 41, 10,
                fill="#34383b", outline=BORDER if self.active else "#3d4145", width=1,
            )
        color = ACCENT if self.active else TEXT
        self.create_line(12, 11, 19, 9, 19, 30, 12, 32, 12, 11, fill=color, width=1.8)
        self.create_line(30, 11, 23, 9, 23, 30, 30, 32, 30, 11, fill=color, width=1.8)
        self.create_line(19, 12, 23, 12, fill=color, width=1.8)
        self.create_line(19, 30, 23, 30, fill=color, width=1.8)


class DarkScrollbar(tk.Canvas):
    def __init__(self, master: tk.Misc, command, width: int = 13):
        super().__init__(
            master, width=width, bg="#202224", highlightthickness=0, bd=0,
            cursor="hand2",
        )
        self.command = command
        self.first = 0.0
        self.last = 1.0
        self.drag_offset: float | None = None
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda _event: setattr(self, "drag_offset", None))

    def set(self, first: str | float, last: str | float) -> None:
        self.first, self.last = float(first), float(last)
        self._draw()

    def _thumb_bounds(self) -> tuple[float, float]:
        height = max(1, self.winfo_height())
        thumb_height = max(34.0, (self.last - self.first) * height)
        travel = max(1.0, height - thumb_height)
        top = self.first * travel / max(0.0001, 1.0 - (self.last - self.first))
        return top, min(height, top + thumb_height)

    def _draw(self) -> None:
        self.delete("all")
        top, bottom = self._thumb_bounds()
        rounded_rectangle(
            self, 3, top + 2, max(4, self.winfo_width() - 3), bottom - 2, 5,
            fill="#555b60", outline="",
        )

    def _press(self, event: tk.Event) -> None:
        top, bottom = self._thumb_bounds()
        if top <= event.y <= bottom:
            self.drag_offset = event.y - top
        else:
            self.command("scroll", -1 if event.y < top else 1, "pages")

    def _drag(self, event: tk.Event) -> None:
        if self.drag_offset is None:
            return
        height = max(1, self.winfo_height())
        thumb_height = max(34.0, (self.last - self.first) * height)
        travel = max(1.0, height - thumb_height)
        fraction = max(0.0, min(1.0, (event.y - self.drag_offset) / travel))
        self.command("moveto", fraction)


def documentation_page_marker(
    page: DocumentationPage,
    completed_pages: set[str] | frozenset[str],
) -> str:
    if page.placeholder:
        return "+ "
    if page.title in completed_pages:
        return "[x] "
    return "[ ] "


class DocumentationPanel(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        close_command,
        insert_snippet_command=None,
        check_challenge_command=None,
        progress: DocumentationProgress | None = None,
        save_progress_command=None,
        load_lesson_state_command=None,
    ):
        super().__init__(master, bg=PANEL, width=390)
        self.grid_propagate(False)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        progress = progress or DocumentationProgress()
        self.current_page = self._initial_page_index(progress.last_open_lesson)
        self.completed_pages: set[str] = set(progress.completed_pages)
        self.completed_challenges: set[str] = set(progress.completed_challenges)
        self.last_open_lesson = progress.last_open_lesson
        self.insert_snippet_command = insert_snippet_command
        self.check_challenge_command = check_challenge_command
        self.save_progress_command = save_progress_command
        self.load_lesson_state_command = load_lesson_state_command
        self.snippet_buttons: list[tk.Widget] = []
        self.revealed_solutions: set[str] = set()

        header = tk.Frame(self, bg=PANEL)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        tk.Label(
            header, text="DOCUMENTATION", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")
        close = tk.Label(
            header, text="Close", bg=PANEL, fg=MUTED, cursor="hand2",
            font=("Segoe UI", 9),
        )
        close.pack(side="right")
        close.bind("<Button-1>", lambda _event: close_command())
        reset = tk.Label(
            header, text="Reset progress", bg=PANEL, fg=MUTED, cursor="hand2",
            font=("Segoe UI", 9),
        )
        reset.pack(side="right", padx=(0, 14))
        reset.bind("<Button-1>", lambda _event: self.reset_progress())

        navigation = tk.Frame(self, bg=PANEL)
        navigation.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        navigation.grid_columnconfigure(1, weight=1)
        self.previous_button = RoundedButton(
            navigation, "Back", lambda: self.show_page(self.current_page - 1),
            width=54, height=27,
        )
        self.previous_button.grid(row=0, column=0, sticky="w")
        self.page_status = tk.Label(
            navigation, bg=PANEL, fg=MUTED, font=("Segoe UI", 8),
        )
        self.page_status.grid(row=0, column=1)
        self.next_button = RoundedButton(
            navigation, "Next", lambda: self.show_page(self.current_page + 1),
            width=54, height=27,
        )
        self.next_button.grid(row=0, column=2, sticky="e")

        body_frame = tk.Frame(self, bg=PANEL)
        body_frame.grid(row=2, column=0, sticky="nsew", padx=(18, 8), pady=(0, 18))
        body_frame.grid_rowconfigure(1, weight=1)
        body_frame.grid_columnconfigure(1, weight=1)

        self.page_list = tk.Listbox(
            body_frame, width=18, bg="#252729", fg="#aeb3b7",
            selectbackground="#41515d", selectforeground="#ffffff",
            relief="flat", bd=0, highlightthickness=0, activestyle="none",
            font=("Segoe UI", 9), exportselection=False,
        )
        self.page_list.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 12))
        self._refresh_page_list()
        self.page_list.bind("<<ListboxSelect>>", self._select_page)

        self.lesson_meta = tk.Frame(body_frame, bg=PANEL)
        self.lesson_meta.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.lesson_meta.grid_columnconfigure(0, weight=1)
        self.lesson_status = tk.Label(
            self.lesson_meta, bg=PANEL, fg=MUTED, font=("Segoe UI", 8), anchor="w",
        )
        self.lesson_status.grid(row=0, column=0, sticky="ew")
        self.challenge_button = RoundedButton(
            self.lesson_meta, "Check challenge", self._check_challenge,
            width=114, height=27,
        )
        self.challenge_button.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.solution_button = RoundedButton(
            self.lesson_meta, "Show solution", self._reveal_sample_solution,
            width=104, height=27,
        )
        self.solution_button.grid(row=1, column=1, sticky="e", padx=(8, 0), pady=(6, 0))
        self.lesson_state_button = RoundedButton(
            self.lesson_meta, "Lesson state", self._load_lesson_state,
            width=104, height=27,
        )
        self.lesson_state_button.grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(6, 0))
        self.completion_button = RoundedButton(
            self.lesson_meta, "Mark complete", self._toggle_completion,
            width=104, height=27,
        )
        self.completion_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.body = tk.Text(
            body_frame, bg=PANEL, fg=TEXT, relief="flat", bd=0,
            padx=0, pady=0, wrap="word", cursor="arrow",
            font=("Segoe UI", 9), spacing1=1, spacing3=3,
        )
        self.body.grid(row=1, column=1, sticky="nsew")
        scroll = DarkScrollbar(body_frame, command=self.body.yview)
        scroll.grid(row=1, column=2, sticky="ns", padx=(8, 0))
        self.body.configure(yscrollcommand=scroll.set)
        self.body.tag_configure(
            "eyebrow", foreground="#7db6a6", font=("Segoe UI", 8, "bold"),
            spacing3=5,
        )
        self.body.tag_configure(
            "title", foreground="#eef0f2", font=("Segoe UI", 16, "bold"),
            spacing1=2, spacing3=8,
        )
        self.body.tag_configure(
            "summary", foreground="#c5c9cc", font=("Segoe UI", 10),
            spacing3=12,
        )
        self.body.tag_configure(
            "heading", foreground=ACCENT, font=("Segoe UI", 10, "bold"),
            spacing1=15, spacing3=5,
        )
        self.body.tag_configure(
            "body", foreground="#b9bdc1", font=("Segoe UI", 9),
            lmargin1=0, lmargin2=0, spacing3=2,
        )
        self.body.tag_configure(
            "code", foreground="#c7d5b1", background="#252729",
            font=("Cascadia Mono", 9), lmargin1=7, lmargin2=7,
            rmargin=7, spacing1=4, spacing3=4,
        )
        self.show_page(self.current_page)

    def _initial_page_index(self, last_open_lesson: str | None) -> int:
        if last_open_lesson:
            for index, page in enumerate(DOCUMENTATION_PAGES):
                if page.title == last_open_lesson:
                    return index
        return 0

    def _save_progress(self) -> None:
        if self.save_progress_command is None:
            return
        self.save_progress_command(
            DocumentationProgress(
                completed_pages=frozenset(self.completed_pages),
                completed_challenges=frozenset(self.completed_challenges),
                last_open_lesson=self.last_open_lesson,
            )
        )

    def _page_marker(self, page: DocumentationPage) -> str:
        return documentation_page_marker(page, self.completed_pages)

    def _refresh_page_list(self) -> None:
        selection = self.current_page
        self.page_list.delete(0, "end")
        for page in DOCUMENTATION_PAGES:
            self.page_list.insert("end", self._page_marker(page) + page.title)
        self.page_list.selection_set(selection)
        self.page_list.activate(selection)

    def _toggle_completion(self) -> None:
        page = DOCUMENTATION_PAGES[self.current_page]
        if page.title in self.completed_pages:
            self.completed_pages.remove(page.title)
        else:
            self.completed_pages.add(page.title)
        self._save_progress()
        self._refresh_page_list()
        self.show_page(self.current_page)

    def _check_challenge(self) -> None:
        if self.check_challenge_command is None:
            return
        self.check_challenge_command(DOCUMENTATION_PAGES[self.current_page])

    def _reveal_sample_solution(self) -> None:
        page = DOCUMENTATION_PAGES[self.current_page]
        if page.sample_solution is None:
            return
        self.revealed_solutions.add(page.title)
        self.show_page(self.current_page)

    def _load_lesson_state(self) -> None:
        if self.load_lesson_state_command is None:
            return
        self.load_lesson_state_command(DOCUMENTATION_PAGES[self.current_page])

    def mark_challenge_completed(self, page: DocumentationPage) -> None:
        if page.challenge_check is None:
            return
        self.completed_challenges.add(page.title)
        self._save_progress()
        self.show_page(self.current_page)

    def reset_progress(self) -> None:
        self.completed_pages.clear()
        self.completed_challenges.clear()
        self.last_open_lesson = None
        self.current_page = 0
        self._save_progress()
        self.show_page(self.current_page)

    def _select_page(self, _event: tk.Event) -> None:
        selection = self.page_list.curselection()
        if selection:
            self.show_page(selection[0])

    def show_page(self, index: int) -> None:
        index = max(0, min(len(DOCUMENTATION_PAGES) - 1, index))
        self.current_page = index
        page = DOCUMENTATION_PAGES[index]
        if page.is_lesson:
            self.last_open_lesson = page.title
            self._save_progress()
        self._refresh_page_list()
        self.page_list.selection_clear(0, "end")
        self.page_list.selection_set(index)
        self.page_list.activate(index)
        self.page_list.see(index)
        self.page_status.configure(text=f"{index + 1} / {len(DOCUMENTATION_PAGES)}")
        completed = page.title in self.completed_pages
        state_text = "Complete" if completed else "Incomplete"
        duration_text = (
            f"{page.estimated_duration_minutes} min"
            if page.estimated_duration_minutes is not None
            else "Reference"
        )
        challenge_text = (
            " - Challenge complete"
            if page.title in self.completed_challenges
            else ""
        )
        self.lesson_status.configure(text=f"{state_text} - {duration_text}{challenge_text}")
        self.completion_button.label = "Mark incomplete" if completed else "Mark complete"
        self.completion_button._draw()
        if page.challenge_check is not None and self.check_challenge_command is not None:
            self.challenge_button.grid()
        else:
            self.challenge_button.grid_remove()
        if page.sample_solution is not None:
            self.solution_button.grid()
        else:
            self.solution_button.grid_remove()
        if page.lesson_scenario_key is not None and self.load_lesson_state_command is not None:
            self.lesson_state_button.grid()
        else:
            self.lesson_state_button.grid_remove()

        self.body.configure(state="normal")
        for button in self.snippet_buttons:
            button.destroy()
        self.snippet_buttons.clear()
        self.body.delete("1.0", "end")
        self.body.insert("end", page.eyebrow + "\n", "eyebrow")
        self.body.insert("end", page.title + "\n", "title")
        self.body.insert("end", page.summary + "\n", "summary")
        path_complete, path_total = learning_path_completion_summary(self.completed_pages)
        if page.title == "Learning path":
            self.body.insert("end", "Path progress\n", "heading")
            self.body.insert(
                "end",
                f"{path_complete} of {path_total} milestone lessons complete\n\n",
                "body",
            )
        path_step = learning_path_step_for_page(page.title)
        if path_step is not None:
            self.body.insert("end", "Learning path\n", "heading")
            self.body.insert(
                "end",
                f"Step {path_step.sequence} of {len(LEARNING_PATH)}: {path_step.milestone}\n"
                f"{path_step.outcome}\n\n",
                "body",
            )
        if page.is_lesson:
            self.body.insert("end", "Estimated duration\n", "heading")
            self.body.insert("end", f"{page.estimated_duration_minutes} minutes\n\n", "body")
            self.body.insert("end", "Prerequisites\n", "heading")
            for prerequisite in page.prerequisites:
                self.body.insert("end", f"- {prerequisite}\n", "body")
            self.body.insert("end", "\nLearning objectives\n", "heading")
            for objective in page.objectives:
                self.body.insert("end", f"- {objective}\n", "body")
            self.body.insert("end", "\n", "body")
            if page.lesson_scenario_key is not None:
                example = get_example_scenario(page.lesson_scenario_key)
                self.body.insert("end", "Lesson state\n", "heading")
                self.body.insert(
                    "end",
                    f"Use Lesson state to reset the visualizer to {example.name}: "
                    f"{example.description}\n\n",
                    "body",
                )
        if page.snippets:
            self.body.insert("end", "Runnable snippets\n", "heading")
            for snippet in page.snippets:
                self.body.insert("end", snippet.title + "\n", "body")
                if self.insert_snippet_command is not None:
                    button = RoundedButton(
                        self.body,
                        "Insert snippet",
                        lambda snippet=snippet: self.insert_snippet_command(snippet),
                        width=102,
                        height=27,
                    )
                    self.snippet_buttons.append(button)
                    self.body.window_create("end", window=button)
                    self.body.insert("end", "\n", "body")
                for line in snippet.code.rstrip().splitlines():
                    self.body.insert("end", line + "\n", "code")
                self.body.insert("end", "\n", "body")
        for heading, content in page.sections:
            self.body.insert("end", heading + "\n", "heading")
            for line in content.splitlines():
                is_code = (
                    line.startswith("from ")
                    or line.startswith("import ")
                    or line.startswith("constellation.")
                    or line.startswith("dynamics.")
                    or line.startswith("ground_stations.")
                    or line.startswith("measurements.")
                    or line.startswith("positioning.")
                    or line.startswith("station =")
                    or line.startswith("states =")
                    or line.startswith("leader =")
                    or line.startswith("print(")
                    or line.startswith("for ")
                    or line.startswith("    ")
                )
                self.body.insert("end", line + "\n", "code" if is_code else "body")
            self.body.insert("end", "\n", "body")
        if page.sample_solution is not None:
            self.body.insert("end", "Sample solution\n", "heading")
            if page.title in self.revealed_solutions:
                for line in page.sample_solution.rstrip().splitlines():
                    self.body.insert("end", line + "\n", "code")
            else:
                self.body.insert(
                    "end",
                    "Try the challenge first, then use Show solution to compare structure and output.\n",
                    "body",
                )
            self.body.insert("end", "\n", "body")
        self.body.configure(state="disabled")
        self.body.yview_moveto(0)


@dataclass
class Satellite:
    sat_id: int
    radius_meters: float
    inclination: float
    node: float
    phase: float
    speed: float
    color: str


def satellite_from_parameters(
    parameters: SatelliteParameters,
    color: str,
) -> Satellite:
    return Satellite(
        sat_id=parameters.satellite_id,
        radius_meters=parameters.radius_meters,
        inclination=math.radians(parameters.inclination_degrees),
        node=math.radians(parameters.longitude_of_ascending_node_degrees),
        phase=math.radians(parameters.orbital_angle_degrees),
        speed=math.tau / parameters.orbital_period_seconds,
        color=color,
    )


class EarthVisualizer(tk.Canvas):
    def __init__(self, master: tk.Misc):
        super().__init__(
            master, bg=PANEL, highlightthickness=0, bd=0, cursor="crosshair"
        )
        self.clock = SimulationClock()
        self.earth_rotation = 0.0
        self.camera_yaw = 0.0
        self.camera_pitch = math.radians(18)
        self.drag_origin: tuple[int, int] | None = None
        self.earth_speed = 1.0
        self.last_frame_time = time.perf_counter()
        self._state_listeners: list[Callable[[], None]] = []
        self.projected_satellites: list[tuple[float, float, Satellite]] = []
        self.projected_stations: list[tuple[float, float, str]] = []
        self.accuracy_history: tuple[AccuracyHistoryPoint, ...] = ()
        self.accuracy_history_station: str | None = None
        self.hovered_id: int | None = None
        self.selected_station_name: str | None = None
        self.camera_dragged = False
        self.stars: list[tuple[float, float, float]] = []
        self.constellation_parameters = ConstellationParameters()
        self.receiver_parameters = ReceiverParameters()
        self.receiver_station_name = "Receiver"
        self.receiver_clock_bias_seconds = (
            self.receiver_parameters.clock_bias_seconds
        )
        self._apply_receiver_station(self.receiver_parameters)
        self.selected_station_name = self.receiver_station_name
        self.satellites = self._build_satellites(self.constellation_parameters)
        self.bind("<Configure>", self._make_stars)
        self.bind("<Motion>", self._on_motion)
        self.bind("<ButtonPress-1>", self._start_camera_drag)
        self.bind("<B1-Motion>", self._drag_camera)
        self.bind("<ButtonRelease-1>", self._stop_camera_drag)
        self.bind("<Leave>", lambda _event: self._clear_hover())
        self.after(33, self._animate)

    @staticmethod
    def _build_satellites(parameters: ConstellationParameters) -> list[Satellite]:
        return [
            satellite_from_parameters(
                satellite,
                SATELLITE_COLORS[index % len(SATELLITE_COLORS)],
            )
            for index, satellite in enumerate(build_satellite_parameters(parameters))
        ]

    def apply_scenario_parameters(
        self,
        constellation: ConstellationParameters,
        receiver: ReceiverParameters,
    ) -> None:
        self.constellation_parameters = constellation
        self.receiver_parameters = receiver
        self.receiver_clock_bias_seconds = receiver.clock_bias_seconds
        self._apply_receiver_station(receiver)
        self.selected_station_name = self.receiver_station_name
        self.satellites = self._build_satellites(constellation)
        self.accuracy_history = ()
        self.accuracy_history_station = None
        self._draw_scene()
        self._notify_state_listeners()

    def export_scenario(self) -> VersionedScenario:
        return VersionedScenario(
            constellation=self.constellation_parameters,
            receiver=self.receiver_parameters,
            simulation_time_seconds=self.clock.simulation_seconds,
            orbital_speed_multiplier=self.clock.speed_multiplier,
        )

    def load_scenario(self, scenario: VersionedScenario) -> None:
        self.apply_scenario_parameters(
            scenario.constellation,
            scenario.receiver,
        )
        wall_time = time.perf_counter()
        self.clock.set_time(scenario.simulation_time_seconds, wall_time)
        self.clock.set_speed(scenario.orbital_speed_multiplier, wall_time)
        self._draw_scene()
        self._notify_state_listeners()

    def _apply_receiver_station(self, receiver: ReceiverParameters) -> None:
        station_kwargs = {
            "latitude_degrees": receiver.latitude_degrees,
            "longitude_degrees": receiver.longitude_degrees,
            "altitude_meters": receiver.altitude_meters,
            "minimum_elevation_degrees": receiver.minimum_elevation_degrees,
        }
        if self.receiver_station_name in list_stations():
            update_station(self.receiver_station_name, **station_kwargs)
        else:
            create_station(self.receiver_station_name, **station_kwargs)

    def add_state_listener(self, listener: Callable[[], None]) -> None:
        self._state_listeners.append(listener)

    def _notify_state_listeners(self) -> None:
        for listener in self._state_listeners:
            listener()

    def get_simulation_time(self) -> float:
        return self.clock.state().simulation_seconds

    def play(self) -> None:
        self.clock.play()
        self._draw_scene()
        self._notify_state_listeners()

    def pause(self) -> None:
        self.clock.pause()
        self._draw_scene()
        self._notify_state_listeners()

    def toggle_playback(self) -> bool:
        is_playing = self.clock.toggle()
        self._draw_scene()
        self._notify_state_listeners()
        return is_playing

    def step(self, seconds: float) -> None:
        self.clock.step(seconds)
        self._draw_scene()
        self._notify_state_listeners()

    def set_simulation_time(self, seconds: float) -> None:
        self.clock.set_time(seconds)
        self._draw_scene()
        self._notify_state_listeners()

    def set_orbit_speed(self, multiplier: float) -> None:
        self.clock.set_speed(multiplier)
        self._notify_state_listeners()

    def set_earth_speed(self, multiplier: float) -> None:
        self.earth_speed = max(0.0, float(multiplier))

    def reset(self) -> None:
        self.clock.reset()
        self.earth_rotation = 0.0
        self.camera_yaw = 0.0
        self.camera_pitch = math.radians(18)
        self.earth_speed = 1.0
        self.accuracy_history = ()
        self.accuracy_history_station = None
        self._draw_scene()
        self._notify_state_listeners()

    def satellite_data(self) -> list[dict[str, float | int]]:
        elapsed = self.clock.state().simulation_seconds
        return [
            {
                "id": sat.sat_id,
                "inclination_degrees": round(math.degrees(sat.inclination), 2),
                "longitude_of_ascending_node_degrees": round(math.degrees(sat.node), 2),
                "orbital_angle_degrees": round(
                    math.degrees(sat.phase + elapsed * sat.speed) % 360, 2
                ),
            }
            for sat in self.satellites
        ]

    def _make_stars(self, event: tk.Event) -> None:
        rng = random.Random(7319)
        count = max(70, int(event.width * event.height / 5200))
        self.stars = [
            (rng.random() * event.width, rng.random() * event.height, rng.choice((0.6, 0.8, 1.0, 1.3)))
            for _ in range(count)
        ]

    @staticmethod
    def _rotate_y(point: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
        x, y, z = point
        ca, sa = math.cos(angle), math.sin(angle)
        return x * ca + z * sa, y, -x * sa + z * ca

    @staticmethod
    def _rotate_x(point: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
        x, y, z = point
        ca, sa = math.cos(angle), math.sin(angle)
        return x, y * ca - z * sa, y * sa + z * ca

    def _view_transform(self, point: tuple[float, float, float]) -> tuple[float, float, float]:
        point = self._rotate_y(point, self.earth_rotation + self.camera_yaw)
        return self._rotate_x(point, self.camera_pitch)

    def _project(self, point: tuple[float, float, float], radius: float) -> tuple[float, float, float]:
        x, y, z = self._view_transform(point)
        camera = 5.2
        scale = camera / (camera - z)
        return self.winfo_width() * 0.5 + x * radius * scale, \
            self.winfo_height() * 0.5 - y * radius * scale, z

    def _draw_curve(self, points: list[tuple[float, float, float]], radius: float,
                    color: str, width: float = 1.0, dash: tuple[int, int] | None = None) -> None:
        projected = [self._project(point, radius) for point in points]
        run: list[float] = []
        run_front: bool | None = None
        for first, second in zip(projected, projected[1:]):
            depth = (first[2] + second[2]) * 0.5
            front = depth >= -0.06
            if run_front is None or front != run_front:
                if len(run) >= 4:
                    self.create_line(
                        *run, fill=color if run_front else "#3b4c57",
                        width=width, dash=dash, smooth=True,
                    )
                run = [first[0], first[1], second[0], second[1]]
                run_front = front
            else:
                run.extend((second[0], second[1]))
        if len(run) >= 4:
            self.create_line(
                *run, fill=color if run_front else "#3b4c57",
                width=width, dash=dash, smooth=True,
            )

    def _orbit_point(self, sat: Satellite, angle: float) -> tuple[float, float, float]:
        position = orbital_to_eci(
            sat.radius_meters,
            math.degrees(sat.inclination),
            math.degrees(sat.node),
            math.degrees(angle),
        )
        return self._display_position(position, 1.58)

    @staticmethod
    def _display_position(
        position: CartesianPosition,
        scale: float,
    ) -> tuple[float, float, float]:
        magnitude = math.sqrt(
            position.x_meters ** 2
            + position.y_meters ** 2
            + position.z_meters ** 2
        )
        return (
            position.x_meters / magnitude * scale,
            position.z_meters / magnitude * scale,
            position.y_meters / magnitude * scale,
        )

    def _satellite_scene_states(
        self,
        elapsed: float,
    ) -> tuple[SatelliteSceneState, ...]:
        return tuple(
            SatelliteSceneState(
                satellite_id=sat.sat_id,
                radius_meters=sat.radius_meters,
                inclination_degrees=math.degrees(sat.inclination),
                longitude_of_ascending_node_degrees=math.degrees(sat.node),
                orbital_angle_degrees=math.degrees(
                    sat.phase + elapsed * sat.speed
                ),
            )
            for sat in self.satellites
        )

    def _draw_scene(self) -> None:
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 10 or height < 10:
            return
        for x, y, size in self.stars:
            shade = "#6f7478" if size < 1 else "#93999e"
            self.create_oval(x - size, y - size, x + size, y + size, fill=shade, outline="")

        radius = min(width, height) * 0.245
        cx, cy = width * 0.5, height * 0.5
        self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                         fill="#252c31", outline=EARTH, width=1.5)

        for latitude in range(-60, 61, 20):
            lat = math.radians(latitude)
            points = [
                (math.cos(lat) * math.cos(theta), math.sin(lat), math.cos(lat) * math.sin(theta))
                for theta in [index * math.pi / 48 for index in range(97)]
            ]
            self._draw_curve(points, radius, "#526d7e")
        for longitude in range(0, 180, 20):
            lon = math.radians(longitude)
            points = [
                (math.sin(theta) * math.cos(lon), math.cos(theta), math.sin(theta) * math.sin(lon))
                for theta in [index * math.tau / 96 for index in range(97)]
            ]
            self._draw_curve(points, radius, "#526d7e")

        elapsed = self.clock.state().simulation_seconds
        self.projected_satellites = []
        draw_order: list[tuple[float, float, float, Satellite]] = []
        projected_satellites_by_id: dict[int, tuple[float, float, float]] = {}
        for sat in self.satellites:
            orbit = [self._orbit_point(sat, index * math.pi / 64) for index in range(129)]
            self._draw_curve(orbit, radius, ORBIT, 1.0, (3, 5))
            angle = sat.phase + elapsed * sat.speed
            sx, sy, sz = self._project(self._orbit_point(sat, angle), radius)
            draw_order.append((sz, sx, sy, sat))
            projected_satellites_by_id[sat.sat_id] = (sx, sy, sz)

        earth_rotation_degrees = math.degrees(self.earth_rotation)
        station_scenes = build_ground_station_scenes(
            self._satellite_scene_states(elapsed),
            list_stations(),
            earth_rotation_degrees,
        )
        station_names = {scene.name for scene in station_scenes}
        if self.selected_station_name not in station_names:
            self.selected_station_name = (
                station_scenes[0].name if station_scenes else None
            )
        selected_station_scene = next(
            (
                scene
                for scene in station_scenes
                if scene.name == self.selected_station_name
            ),
            None,
        )
        self.projected_stations = []
        projected_stations = []
        for station_scene in station_scenes:
            station_point = self._display_position(station_scene.station_ecef, 1.0)
            station_x, station_y, station_depth = self._project(station_point, radius)
            projected_stations.append(
                (station_depth, station_x, station_y, station_scene)
            )
            if station_depth < 0.0:
                continue
            for link in station_scene.satellite_links:
                if not link.visibility.is_visible:
                    continue
                satellite_x, satellite_y, _ = projected_satellites_by_id[
                    link.satellite_id
                ]
                self.create_line(
                    station_x,
                    station_y,
                    satellite_x,
                    satellite_y,
                    fill=VISIBLE_LINK,
                    width=1.8,
                    dash=(4, 3),
                )

        if selected_station_scene is not None:
            self._draw_measurement_links(
                selected_station_scene,
                projected_stations,
                projected_satellites_by_id,
            )

        for depth, sx, sy, sat in sorted(draw_order):
            dot_radius = 5.5 if sat.sat_id == self.hovered_id else 4.0
            self.create_oval(
                sx - dot_radius, sy - dot_radius, sx + dot_radius, sy + dot_radius,
                fill=sat.color, outline="#e4e6e8", width=1,
            )
            self.projected_satellites.append((sx, sy, sat))
            if sat.sat_id == self.hovered_id:
                label = f"GLOBALSTAR {sat.sat_id}"
                text_id = self.create_text(
                    sx + 13, sy - 16, text=label, fill=TEXT,
                    font=("Segoe UI", 9, "bold"), anchor="w",
                )
                box = self.bbox(text_id)
                if box:
                    background = rounded_rectangle(
                        self, box[0] - 7, box[1] - 4, box[2] + 7, box[3] + 4, 6,
                        fill="#34383c", outline=BORDER, width=1,
                    )
                    self.tag_lower(background, text_id)

        for depth, station_x, station_y, station_scene in sorted(
            projected_stations,
            key=lambda projected_station: projected_station[0],
        ):
            if depth < 0.0:
                continue
            selected = station_scene.name == self.selected_station_name
            if selected:
                self.create_oval(
                    station_x - 8.0,
                    station_y - 8.0,
                    station_x + 8.0,
                    station_y + 8.0,
                    outline=ACCENT,
                    width=2,
                )
            self.create_oval(
                station_x - 4.5,
                station_y - 4.5,
                station_x + 4.5,
                station_y + 4.5,
                fill=STATION,
                outline="#fff1eb",
                width=1,
            )
            self.create_text(
                station_x + 8,
                station_y - 8,
                text=station_scene.name,
                fill=TEXT,
                font=("Segoe UI", 8, "bold"),
                anchor="sw",
            )
            self.projected_stations.append(
                (station_x, station_y, station_scene.name)
            )

        if selected_station_scene is not None:
            comparison = build_accuracy_comparison_display(
                selected_station_scene,
                receiver_clock_bias_seconds=self.receiver_clock_bias_seconds,
            )
            position_fix = comparison.baseline
            if self.accuracy_history_station != selected_station_scene.name:
                self.accuracy_history = ()
                self.accuracy_history_station = selected_station_scene.name
            self.accuracy_history = append_accuracy_history_point(
                self.accuracy_history,
                elapsed_seconds=elapsed,
                comparison=comparison,
            )
            self._draw_estimated_receiver_marker(position_fix, radius)
            next_panel_y = self._draw_visibility_table(selected_station_scene)
            next_panel_y = self._draw_position_fix_panel(position_fix, next_panel_y)
            self._draw_accuracy_panel(comparison, self.accuracy_history, next_panel_y)

        self.create_text(18, 18, text="ORBITAL VIEW", anchor="nw", fill=MUTED,
                         font=("Segoe UI", 9, "bold"))
        footer = (
            "CLICK STATION FOR POSITION FIX  |  "
            "AMBER LINKS ARE PSEUDORANGE MEASUREMENTS  |  DRAG TO ROTATE"
        )
        self.create_text(
            18,
            height - 18,
            text=footer,
            anchor="sw",
            fill="#686d72",
            font=("Segoe UI", 8),
        )

    def _draw_measurement_links(
        self,
        station_scene: GroundStationScene,
        projected_stations: list[tuple[float, float, float, GroundStationScene]],
        projected_satellites_by_id: dict[int, tuple[float, float, float]],
    ) -> None:
        station_projection = next(
            (
                (station_x, station_y, station_depth)
                for station_depth, station_x, station_y, projected_scene
                in projected_stations
                if projected_scene.name == station_scene.name
            ),
            None,
        )
        if station_projection is None:
            return
        station_x, station_y, station_depth = station_projection
        if station_depth < 0.0:
            return

        for measurement in build_receiver_measurement_links(
            station_scene,
            receiver_clock_bias_seconds=self.receiver_clock_bias_seconds,
        ):
            satellite_projection = projected_satellites_by_id.get(
                measurement.satellite_id
            )
            if satellite_projection is None:
                continue
            satellite_x, satellite_y, satellite_depth = satellite_projection
            if satellite_depth < 0.0:
                continue
            self.create_line(
                station_x,
                station_y,
                satellite_x,
                satellite_y,
                fill=MEASUREMENT_LINK if measurement.is_visible else "#77705d",
                width=2.2 if measurement.is_visible else 1.2,
                dash=(2, 3),
            )

    def _draw_estimated_receiver_marker(
        self,
        position_fix: ReceiverPositionFixDisplay,
        radius: float,
    ) -> None:
        if position_fix.estimated_receiver_ecef is None:
            return
        estimated_point = self._display_position(
            position_fix.estimated_receiver_ecef,
            1.0,
        )
        estimated_x, estimated_y, estimated_depth = self._project(
            estimated_point,
            radius,
        )
        if estimated_depth < 0.0:
            return
        self.create_oval(
            estimated_x - 10.0,
            estimated_y - 10.0,
            estimated_x + 10.0,
            estimated_y + 10.0,
            outline="#d6cc75",
            width=2,
            dash=(3, 3),
        )

    def _draw_visibility_table(
        self,
        station_scene: GroundStationScene,
    ) -> float:
        rows = build_station_visibility_rows(station_scene)
        width = self.winfo_width()
        panel_width = min(360, max(264, width - 36))
        x1 = width - panel_width - 18
        y1 = 42
        row_height = 22
        panel_height = 66 + len(rows) * row_height
        background = rounded_rectangle(
            self,
            x1,
            y1,
            x1 + panel_width,
            y1 + panel_height,
            9,
            fill="#25292c",
            outline=BORDER,
            width=1,
        )
        self.tag_raise(background)
        self.create_text(
            x1 + 12,
            y1 + 12,
            text=f"{station_scene.name.upper()} VISIBILITY",
            fill=TEXT,
            font=("Segoe UI", 9, "bold"),
            anchor="nw",
        )
        self.create_text(
            x1 + panel_width - 12,
            y1 + 12,
            text=f"MASK {station_scene.station.minimum_elevation_degrees:.1f}°",
            fill=MUTED,
            font=("Segoe UI", 8),
            anchor="ne",
        )
        columns = (
            ("SAT", 12, "w"),
            ("AZ", 0.30, "e"),
            ("EL", 0.48, "e"),
            ("RANGE", 0.72, "e"),
            ("STATUS", -12, "e"),
        )
        header_y = y1 + 42
        for label, offset, anchor in columns:
            column_x = (
                x1 + offset
                if isinstance(offset, int)
                else x1 + panel_width * offset
            )
            if offset == -12:
                column_x = x1 + panel_width - 12
            self.create_text(
                column_x,
                header_y,
                text=label,
                fill=MUTED,
                font=("Segoe UI", 7, "bold"),
                anchor=anchor,
            )
        self.create_line(
            x1 + 12,
            y1 + 54,
            x1 + panel_width - 12,
            y1 + 54,
            fill=BORDER,
        )
        for index, row in enumerate(rows):
            row_y = y1 + 66 + index * row_height
            status = "VISIBLE" if row.is_visible else "BELOW"
            status_color = VISIBLE_LINK if row.is_visible else MUTED
            values = (
                (f"G{row.satellite_id}", x1 + 12, "w", TEXT),
                (
                    f"{row.azimuth_degrees:5.1f}°",
                    x1 + panel_width * 0.30,
                    "e",
                    TEXT,
                ),
                (
                    f"{row.elevation_degrees:5.1f}°",
                    x1 + panel_width * 0.48,
                    "e",
                    TEXT,
                ),
                (
                    f"{row.range_meters / 1000.0:,.0f} km",
                    x1 + panel_width * 0.72,
                    "e",
                    TEXT,
                ),
                (
                    status,
                    x1 + panel_width - 12,
                    "e",
                    status_color,
                ),
            )
            for value, column_x, anchor, color in values:
                self.create_text(
                    column_x,
                    row_y,
                    text=value,
                    fill=color,
                    font=("Cascadia Mono", 8),
                    anchor=anchor,
                )
        return y1 + panel_height + 12

    def _draw_position_fix_panel(
        self,
        position_fix: ReceiverPositionFixDisplay,
        y1: float,
    ) -> float:
        width = self.winfo_width()
        height = self.winfo_height()
        panel_width = min(360, max(264, width - 36))
        x1 = width - panel_width - 18
        panel_height = 180 if position_fix.estimated_receiver_ecef is not None else 92
        if y1 + panel_height > height - 36:
            y1 = max(42, height - panel_height - 36)
        rounded_rectangle(
            self,
            x1,
            y1,
            x1 + panel_width,
            y1 + panel_height,
            9,
            fill="#25292c",
            outline=BORDER,
            width=1,
        )
        self.create_text(
            x1 + 12,
            y1 + 12,
            text="RECEIVER POSITION FIX",
            fill=TEXT,
            font=("Segoe UI", 9, "bold"),
            anchor="nw",
        )
        if position_fix.estimated_receiver_ecef is None:
            self.create_text(
                x1 + 12,
                y1 + 42,
                text="Solver diagnostic",
                fill=MUTED,
                font=("Segoe UI", 7, "bold"),
                anchor="nw",
            )
            self.create_text(
                x1 + 12,
                y1 + 62,
                text=position_fix.diagnostic or "Position fix unavailable",
                fill="#d6cc75",
                font=("Segoe UI", 8),
                anchor="nw",
                width=panel_width - 24,
            )
            return y1 + panel_height + 12

        estimated = position_fix.estimated_receiver_ecef
        residuals = position_fix.residuals_meters
        max_residual = position_fix.max_abs_residual_meters or 0.0
        rms_residual = position_fix.rms_residual_meters or 0.0
        horizontal_error = position_fix.horizontal_error_meters or 0.0
        vertical_error = position_fix.vertical_error_meters or 0.0
        status = "CONVERGED" if position_fix.converged else "NOT CONVERGED"
        rows = (
            ("TRUE XYZ", self._format_ecef(position_fix.true_receiver_ecef)),
            ("EST XYZ", self._format_ecef(estimated)),
            ("H/V ERROR", f"H {horizontal_error:.3f} m / V {vertical_error:.3f} m"),
            ("3D ERROR", f"{position_fix.position_error_meters or 0.0:.3f} m"),
            (
                "CLOCK",
                (
                    f"true {position_fix.true_clock_bias_seconds * 1_000_000:.3f} us / "
                    f"est {(position_fix.estimated_clock_bias_seconds or 0.0) * 1_000_000:.3f} us"
                ),
            ),
            ("RESIDUALS", f"max {max_residual:.3f} m / rms {rms_residual:.3f} m"),
            ("SAT COUNT", f"{len(residuals)} observations"),
            ("STATUS", status),
        )
        for index, (label, value) in enumerate(rows):
            row_y = y1 + 40 + index * 17
            self.create_text(
                x1 + 12,
                row_y,
                text=label,
                fill=MUTED,
                font=("Segoe UI", 7, "bold"),
                anchor="nw",
            )
            self.create_text(
                x1 + 96,
                row_y,
                text=value,
                fill=VISIBLE_LINK if label == "STATUS" and position_fix.converged else TEXT,
                font=("Cascadia Mono", 8),
                anchor="nw",
            )
        return y1 + panel_height + 12

    def _draw_accuracy_panel(
        self,
        comparison: AccuracyComparisonDisplay,
        history: tuple[AccuracyHistoryPoint, ...],
        y1: float,
    ) -> None:
        width = self.winfo_width()
        height = self.winfo_height()
        panel_width = min(360, max(264, width - 36))
        panel_height = 162
        x1 = width - panel_width - 18
        if y1 + panel_height > height - 36:
            x1 = 18
            y1 = max(42, height - panel_height - 36)
        rounded_rectangle(
            self,
            x1,
            y1,
            x1 + panel_width,
            y1 + panel_height,
            9,
            fill="#25292c",
            outline=BORDER,
            width=1,
        )
        self.create_text(
            x1 + 12,
            y1 + 12,
            text="ACCURACY COMPARISON",
            fill=TEXT,
            font=("Segoe UI", 9, "bold"),
            anchor="nw",
        )
        self.create_text(
            x1 + panel_width - 12,
            y1 + 12,
            text=f"SEED {comparison.error_model_seed}",
            fill=MUTED,
            font=("Segoe UI", 8),
            anchor="ne",
        )
        clean_error = comparison.baseline.position_error_meters
        modeled_error = comparison.with_errors.position_error_meters
        rows = (
            ("BEFORE", "clean pseudoranges", clean_error, VISIBLE_LINK),
            ("AFTER", "seeded errors", modeled_error, MEASUREMENT_LINK),
        )
        for index, (label, note, value, color) in enumerate(rows):
            row_y = y1 + 40 + index * 22
            self.create_text(
                x1 + 12,
                row_y,
                text=label,
                fill=MUTED,
                font=("Segoe UI", 7, "bold"),
                anchor="nw",
            )
            self.create_text(
                x1 + 74,
                row_y,
                text=note,
                fill=TEXT,
                font=("Segoe UI", 8),
                anchor="nw",
            )
            self.create_text(
                x1 + panel_width - 12,
                row_y,
                text=self._format_error_value(value),
                fill=color,
                font=("Cascadia Mono", 8),
                anchor="ne",
            )

        plot_x1 = x1 + 12
        plot_y1 = y1 + 91
        plot_x2 = x1 + panel_width - 12
        plot_y2 = y1 + panel_height - 18
        self.create_rectangle(
            plot_x1,
            plot_y1,
            plot_x2,
            plot_y2,
            fill="#202326",
            outline=BORDER,
            width=1,
        )
        self.create_text(
            plot_x1,
            plot_y1 - 8,
            text="3D ERROR HISTORY",
            fill=MUTED,
            font=("Segoe UI", 7, "bold"),
            anchor="sw",
        )
        values = [
            value
            for point in history
            for value in (
                point.baseline_position_error_meters,
                point.error_position_error_meters,
            )
            if value is not None
        ]
        max_value = max(values, default=1.0)
        max_value = max(1.0, max_value)
        self._draw_history_line(
            history,
            "baseline_position_error_meters",
            plot_x1,
            plot_y1,
            plot_x2,
            plot_y2,
            max_value,
            VISIBLE_LINK,
        )
        self._draw_history_line(
            history,
            "error_position_error_meters",
            plot_x1,
            plot_y1,
            plot_x2,
            plot_y2,
            max_value,
            MEASUREMENT_LINK,
        )
        self.create_text(
            plot_x2,
            plot_y1 - 8,
            text=f"max {max_value:.1f} m",
            fill=MUTED,
            font=("Cascadia Mono", 7),
            anchor="se",
        )

    def _draw_history_line(
        self,
        history: tuple[AccuracyHistoryPoint, ...],
        attribute: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        max_value: float,
        color: str,
    ) -> None:
        points = [
            (index, getattr(point, attribute))
            for index, point in enumerate(history)
            if getattr(point, attribute) is not None
        ]
        if len(points) < 2:
            return
        denominator = max(1, len(history) - 1)
        coordinates: list[float] = []
        for index, value in points:
            x = x1 + (x2 - x1) * index / denominator
            y = y2 - (y2 - y1) * min(float(value) / max_value, 1.0)
            coordinates.extend((x, y))
        self.create_line(*coordinates, fill=color, width=1.8, smooth=True)

    @staticmethod
    def _format_error_value(value: float | None) -> str:
        if value is None:
            return "unavailable"
        return f"{value:.3f} m"

    @staticmethod
    def _format_ecef(position: CartesianPosition) -> str:
        return (
            f"{position.x_meters / 1000.0:,.1f}, "
            f"{position.y_meters / 1000.0:,.1f}, "
            f"{position.z_meters / 1000.0:,.1f} km"
        )

    def _animate(self) -> None:
        now = time.perf_counter()
        elapsed = min(0.1, now - self.last_frame_time)
        self.last_frame_time = now
        clock_was_playing = self.clock.is_playing
        self.clock.tick(now)
        if clock_was_playing:
            self.earth_rotation += elapsed * (math.tau / 86164) * self.earth_speed
            self._draw_scene()
            self._notify_state_listeners()
        self.after(33, self._animate)

    def _on_motion(self, event: tk.Event) -> None:
        if self.drag_origin is not None:
            return
        nearest: tuple[float, int] | None = None
        for x, y, sat in self.projected_satellites:
            distance = math.hypot(event.x - x, event.y - y)
            if distance <= 13 and (nearest is None or distance < nearest[0]):
                nearest = (distance, sat.sat_id)
        self.hovered_id = nearest[1] if nearest else None

    def _start_camera_drag(self, event: tk.Event) -> None:
        self.drag_origin = (event.x, event.y)
        self.camera_dragged = False
        self.hovered_id = None
        self.configure(cursor="fleur")

    def _drag_camera(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        previous_x, previous_y = self.drag_origin
        if math.hypot(event.x - previous_x, event.y - previous_y) > 2:
            self.camera_dragged = True
        self.camera_yaw += (event.x - previous_x) * 0.009
        self.camera_pitch += (event.y - previous_y) * 0.009
        self.camera_pitch = max(math.radians(-85), min(math.radians(85), self.camera_pitch))
        self.drag_origin = (event.x, event.y)

    def _stop_camera_drag(self, event: tk.Event) -> None:
        if not self.camera_dragged:
            nearest: tuple[float, str] | None = None
            for x, y, station_name in self.projected_stations:
                distance = math.hypot(event.x - x, event.y - y)
                if distance <= 14 and (
                    nearest is None or distance < nearest[0]
                ):
                    nearest = (distance, station_name)
            if nearest is not None:
                self.selected_station_name = nearest[1]
        self.drag_origin = None
        self.camera_dragged = False
        self.configure(cursor="crosshair")

    def _clear_hover(self) -> None:
        self.hovered_id = None


class PythonHighlighter:
    def __init__(self, text: tk.Text):
        self.text = text
        self.pending: str | None = None
        self.patterns = [
            ("comment", re.compile(r"#[^\n]*")),
            ("string", re.compile(r"(?:'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")")),
            ("number", re.compile(r"\b(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?)\b")),
            ("keyword", re.compile(r"\b(?:" + "|".join(keyword.kwlist) + r")\b")),
            ("builtin", re.compile(r"\b(?:" + "|".join(map(re.escape, dir(builtins))) + r")\b")),
            ("sim_function", re.compile(
                r"\b(?:get_satellite_states|get_satellite_count|"
                r"set_orbital_time_scale|set_earth_rotation_scale|reset_simulation|"
                r"play_simulation|pause_simulation|step_simulation|"
                r"set_simulation_time|get_simulation_time|"
                r"orbital_to_eci|eci_to_ecef|ecef_to_eci|station_to_ecef|"
                r"ecef_to_local_horizon|local_horizon_to_ecef)\b"
            )),
        ]
        colors = {
            "comment": "#77827c",
            "string": "#b8c68b",
            "number": "#caa177",
            "keyword": "#8eb6d8",
            "builtin": "#c59bcf",
            "sim_function": "#7db6a6",
        }
        for tag, color in colors.items():
            text.tag_configure(tag, foreground=color)
        text.bind("<<Modified>>", self._changed)
        text.edit_modified(False)
        self.highlight()

    def _changed(self, _event: tk.Event) -> None:
        if self.text.edit_modified():
            self.text.edit_modified(False)
            if self.pending:
                self.text.after_cancel(self.pending)
            self.pending = self.text.after(80, self.highlight)

    def highlight(self) -> None:
        self.pending = None
        content = self.text.get("1.0", "end-1c")
        for tag, _pattern in self.patterns:
            self.text.tag_remove(tag, "1.0", "end")
        for tag, pattern in self.patterns:
            for match in pattern.finditer(content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text.tag_add(tag, start, end)


class EditorAutocomplete:
    def __init__(self, editor: tk.Text, parent: tk.Misc):
        self.editor = editor
        self.parent = parent
        self.matches: list[tuple[str, str, str]] = []
        self.token_start = "insert"
        self.pending_check: str | None = None
        self.popup = tk.Listbox(
            parent, bg="#303336", fg=TEXT, selectbackground="#506575",
            selectforeground="#ffffff", relief="solid", bd=1,
            highlightthickness=0, activestyle="none",
            font=("Cascadia Mono", 9), height=6, exportselection=False,
        )
        editor.bind("<KeyPress>", self._key_pressed, add="+")
        editor.bind("<Down>", self._move_down, add="+")
        editor.bind("<Up>", self._move_up, add="+")
        editor.bind("<KeyPress-Return>", self._accept, add="+")
        editor.bind("<KeyRelease-Return>", self._consume_accept_release, add="+")
        editor.bind("<Tab>", self._accept, add="+")
        editor.bind("<Escape>", self._dismiss, add="+")
        editor.bind("<Button-1>", self._dismiss, add="+")
        self.popup.bind("<Double-Button-1>", self._accept)

    def _current_token(self) -> tuple[str, str]:
        line_start = self.editor.index("insert linestart")
        prefix = self.editor.get(line_start, "insert")
        match = re.search(r"(?:import\s+)?[A-Za-z_][\w.]*$", prefix)
        if not match:
            return "", self.editor.index("insert")
        start = self.editor.index(f"{line_start}+{match.start()}c")
        return match.group(0), start

    def _key_pressed(self, event: tk.Event) -> None:
        if event.keysym in {
            "Up", "Down", "Return", "Tab", "Escape", "Shift_L", "Shift_R",
            "Control_L", "Control_R",
        }:
            return
        if self.pending_check:
            self.editor.after_cancel(self.pending_check)
        self.pending_check = self.editor.after_idle(self._show_for_current_token)

    def _show_for_current_token(self) -> None:
        self.pending_check = None
        token, _start = self._current_token()
        has_match = any(
            insertion.lower().startswith(token.lower())
            for _label, insertion, _color in SIMULATOR_COMPLETIONS
        )
        if token and has_match:
            self.show()
        else:
            self.hide()

    def show(self, force: bool = False) -> None:
        token, self.token_start = self._current_token()
        lowered = token.lower()
        self.matches = [
            item for item in SIMULATOR_COMPLETIONS
            if force or not token or item[1].lower().startswith(lowered)
        ]
        if not self.matches:
            self.hide()
            return

        self.popup.delete(0, "end")
        for index, (label, _insertion, color) in enumerate(self.matches):
            self.popup.insert("end", label)
            self.popup.itemconfigure(index, foreground=color)
        self.popup.selection_set(0)
        self.popup.activate(0)
        box = self.editor.bbox("insert")
        if box is None:
            self.hide()
            return
        x, y, _width, height = box
        popup_width = min(420, max(245, self.editor.winfo_width() - x - 8))
        row_count = min(6, len(self.matches))
        self.popup.configure(height=row_count)
        self.popup.update_idletasks()
        popup_height = self.popup.winfo_reqheight()
        popup_y = self.editor.winfo_y() + y - popup_height - 2
        if popup_y < self.editor.winfo_y():
            popup_y = self.editor.winfo_y() + y + height + 2
        self.popup.place(
            x=self.editor.winfo_x() + x,
            y=popup_y,
            width=popup_width,
        )
        self.popup.lift()

    def hide(self) -> None:
        self.popup.place_forget()

    def _move_down(self, _event: tk.Event) -> str | None:
        if not self.popup.winfo_ismapped():
            return None
        current = self.popup.curselection()
        index = min(len(self.matches) - 1, (current[0] if current else -1) + 1)
        self.popup.selection_clear(0, "end")
        self.popup.selection_set(index)
        self.popup.activate(index)
        self.popup.see(index)
        return "break"

    def _move_up(self, _event: tk.Event) -> str | None:
        if not self.popup.winfo_ismapped():
            return None
        current = self.popup.curselection()
        index = max(0, (current[0] if current else 1) - 1)
        self.popup.selection_clear(0, "end")
        self.popup.selection_set(index)
        self.popup.activate(index)
        self.popup.see(index)
        return "break"

    def _accept(self, _event: tk.Event) -> str | None:
        if not self.popup.winfo_ismapped() or not self.matches:
            return None
        selected = self.popup.curselection()
        index = selected[0] if selected else 0
        insertion = self.matches[index][1]
        self.editor.delete(self.token_start, "insert")
        self.editor.insert(self.token_start, insertion)
        if insertion.endswith("()"):
            self.editor.mark_set("insert", "insert-1c")
        intended_cursor = self.editor.index("insert")
        self.editor.after_idle(
            lambda index=intended_cursor: self.editor.mark_set("insert", index)
        )
        self.hide()
        return "break"

    def _consume_accept_release(self, _event: tk.Event) -> str | None:
        if self.popup.winfo_ismapped():
            return None
        return "break"

    def _dismiss(self, _event: tk.Event) -> str | None:
        if not self.popup.winfo_ismapped():
            return None
        self.hide()
        return "break"


class OrbitStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPS Learning Studio")
        self.geometry("1280x760")
        self.minsize(980, 620)
        self.configure(bg=BG)
        self.current_file: Path | None = None
        self.execution_namespace: dict[str, object] = {"__name__": "__main__"}
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.documentation_progress_path = default_documentation_progress_path()
        self.documentation_progress = load_documentation_progress(
            self.documentation_progress_path
        )
        self._match_windows_titlebar()
        if not list_stations():
            create_station(
                "Aberdeen",
                latitude_degrees=57.1497,
                longitude_degrees=-2.0943,
                altitude_meters=65.0,
                minimum_elevation_degrees=5.0,
            )
        self._build_ui()
        bind_visualizer(self.visualizer)
        self.after_idle(self._set_initial_split_positions)
        self.after(50, self._poll_output)
        self.after(1500, self.check_for_updates)

    def _build_ui(self) -> None:
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True, padx=(10, 18), pady=18)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(1, weight=1)

        rail = tk.Frame(shell, bg=BG, width=50)
        rail.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        rail.grid_propagate(False)
        self.documentation_button = SidebarIconButton(rail, self.toggle_documentation)
        self.documentation_button.pack(side="top", pady=(2, 0))
        tk.Label(
            rail, text="DOCS", bg=BG, fg="#73787d",
            font=("Segoe UI", 7, "bold"),
        ).pack(side="top", pady=(4, 0))
        self.update_button = RoundedButton(
            rail, text="Update", command=lambda: self.check_for_updates(manual=True),
            width=48, height=28,
        )
        self.update_button.pack(side="bottom", pady=(0, 3))
        tk.Label(
            rail, text=f"v{CURRENT_VERSION}", bg=BG, fg="#73787d",
            font=("Segoe UI", 7),
        ).pack(side="bottom", pady=(0, 5))

        self.workspace_split = tk.PanedWindow(
            shell, orient="horizontal", bg=BG, bd=0, relief="flat",
            sashwidth=8, sashrelief="flat", showhandle=False,
        )
        self.workspace_split.grid(row=0, column=1, sticky="nsew")
        self.documentation_panel = DocumentationPanel(
            self.workspace_split,
            self.toggle_documentation,
            self.insert_documentation_snippet,
            self.check_documentation_challenge,
            self.documentation_progress,
            self.save_documentation_progress,
            self.load_documentation_lesson_state,
        )
        self.documentation_open = False

        self.content_split = tk.PanedWindow(
            self.workspace_split, orient="horizontal", bg=BG, bd=0,
            relief="flat", sashwidth=12, sashrelief="flat", showhandle=False,
        )
        self.workspace_split.add(self.content_split, stretch="always", minsize=600)

        left = RoundedPanel(self.content_split)
        right = RoundedPanel(self.content_split)
        self.content_split.add(left, stretch="always", minsize=300)
        self.content_split.add(right, stretch="always", minsize=360)

        self.visualizer = EarthVisualizer(left.body)
        self.visualizer.pack(fill="both", expand=True)
        self._build_simulation_controls(left.body)
        self._build_scenario_controls(left.body)
        self.visualizer.add_state_listener(
            lambda: self._refresh_simulation_controls(reschedule=False)
        )

        right.body.grid_rowconfigure(1, weight=1)
        right.body.grid_columnconfigure(0, weight=1)

        toolbar = tk.Frame(right.body, bg=PANEL)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.file_label = tk.Label(
            toolbar, text="untitled.py", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9), anchor="w",
        )
        self.file_label.pack(side="left", padx=(4, 8), fill="x", expand=True)
        for label, command in (
            ("Open", self.open_script),
            ("Import", self.insert_import),
            ("Save", self.save_script),
            ("Run", self.run_code),
        ):
            RoundedButton(toolbar, text=label, command=command).pack(side="left", padx=3)

        self.ide_split = tk.PanedWindow(
            right.body, orient="vertical", bg=PANEL, bd=0, relief="flat",
            sashwidth=10, sashrelief="flat", showhandle=False,
        )
        self.ide_split.grid(row=1, column=0, sticky="nsew")

        editor_frame = tk.Frame(self.ide_split, bg="#202224")
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)
        self.editor = tk.Text(
            editor_frame, bg="#202224", fg=TEXT, insertbackground="#f0f0f0",
            selectbackground="#48535c", selectforeground="#ffffff",
            relief="flat", bd=0, padx=14, pady=14, undo=True,
            wrap="none", font=("Cascadia Mono", 10), tabs=("2c",),
        )
        self.editor.grid(row=0, column=0, sticky="nsew")
        self.editor.bind("<Control-BackSpace>", self._delete_previous_word)
        y_scroll = DarkScrollbar(editor_frame, command=self.editor.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=y_scroll.set)
        self.highlighter = PythonHighlighter(self.editor)
        self.editor.insert(
            "1.0",
            "# Live Python workspace\n"
            "# Import the simulator module you want to use.\n\n"
            "import gps_sim.constellation as constellation\n\n"
            "print(\"Globalstar satellite state:\")\n"
            "for satellite in constellation.get_satellite_states():\n"
            "    print(satellite)\n",
        )
        self.highlighter.highlight()
        self.autocomplete = EditorAutocomplete(self.editor, editor_frame)

        output_pane = tk.Frame(self.ide_split, bg=PANEL)
        output_pane.grid_rowconfigure(1, weight=1)
        output_pane.grid_columnconfigure(0, weight=1)
        output_header = tk.Label(
            output_pane, text="OUTPUT", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8, "bold"), anchor="w",
        )
        output_header.grid(row=0, column=0, sticky="ew", padx=4, pady=(2, 4))
        output_frame = tk.Frame(output_pane, bg="#202224")
        output_frame.grid(row=1, column=0, sticky="nsew")
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)
        self.output = tk.Text(
            output_frame, height=7, bg="#202224", fg="#bfc4c8",
            relief="flat", bd=0, padx=12, pady=9, state="disabled",
            wrap="word", font=("Cascadia Mono", 9),
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        output_scroll = DarkScrollbar(output_frame, command=self.output.yview)
        output_scroll.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=output_scroll.set)
        self.ide_split.add(editor_frame, stretch="always", minsize=160)
        self.ide_split.add(output_pane, stretch="always", minsize=80)
        self.editor.focus_set()
        self.bind("<Control-s>", lambda _event: self.save_script())
        self.bind("<Control-o>", lambda _event: self.open_script())
        self.bind("<F5>", lambda _event: self.run_code())
        self.after(250, self._refresh_simulation_controls)

    def _build_simulation_controls(self, parent: tk.Misc) -> None:
        controls = tk.Frame(parent, bg=PANEL)
        controls.pack(fill="x", padx=8, pady=(8, 6))

        self.play_pause_button = RoundedButton(
            controls,
            text="Pause",
            command=self.toggle_simulation_playback,
            width=64,
            height=28,
        )
        self.play_pause_button.pack(side="left", padx=(0, 6))
        RoundedButton(
            controls,
            text="Step",
            command=lambda: self.step_simulation(60.0),
            width=56,
            height=28,
        ).pack(side="left", padx=(0, 12))

        tk.Label(
            controls,
            text="Time",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 4))
        self.simulation_time_var = tk.StringVar(value="00:00:00")
        self.simulation_time_entry = tk.Entry(
            controls,
            textvariable=self.simulation_time_var,
            width=9,
            bg="#202224",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            justify="center",
            font=("Cascadia Mono", 9),
        )
        self.simulation_time_entry.pack(side="left", padx=(0, 10), ipady=4)
        self.simulation_time_entry.bind(
            "<Return>",
            lambda _event: self.apply_simulation_time_entry(),
        )
        self.simulation_time_entry.bind(
            "<FocusOut>",
            lambda _event: self.apply_simulation_time_entry(),
        )

        tk.Label(
            controls,
            text="Speed",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 4))
        self.simulation_speed_var = tk.StringVar(value="1")
        self.simulation_speed = tk.Spinbox(
            controls,
            from_=0.0,
            to=120.0,
            increment=0.5,
            width=5,
            textvariable=self.simulation_speed_var,
            command=self.apply_simulation_speed_entry,
            bg="#202224",
            fg=TEXT,
            insertbackground=TEXT,
            buttonbackground="#34383b",
            relief="flat",
            justify="center",
            font=("Cascadia Mono", 9),
        )
        self.simulation_speed.pack(side="left", ipady=4)
        tk.Label(
            controls,
            text="x",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(3, 0))
        self.simulation_speed.bind(
            "<Return>",
            lambda _event: self.apply_simulation_speed_entry(),
        )
        self.simulation_speed.bind(
            "<FocusOut>",
            lambda _event: self.apply_simulation_speed_entry(),
        )

    def _build_scenario_controls(self, parent: tk.Misc) -> None:
        controls = tk.Frame(parent, bg=PANEL)
        controls.pack(fill="x", padx=8, pady=(0, 8))
        self.constellation_count_var = tk.StringVar(
            value=str(self.visualizer.constellation_parameters.satellite_count)
        )
        self.constellation_inclination_var = tk.StringVar(
            value=self._format_speed(
                self.visualizer.constellation_parameters.inclination_degrees
            )
        )
        self.constellation_altitude_var = tk.StringVar(
            value=self._format_speed(
                self.visualizer.constellation_parameters.altitude_kilometers
            )
        )
        self.receiver_latitude_var = tk.StringVar(
            value=f"{self.visualizer.receiver_parameters.latitude_degrees:g}"
        )
        self.receiver_longitude_var = tk.StringVar(
            value=f"{self.visualizer.receiver_parameters.longitude_degrees:g}"
        )
        self.receiver_mask_var = tk.StringVar(
            value=f"{self.visualizer.receiver_parameters.minimum_elevation_degrees:g}"
        )
        self.receiver_clock_var = tk.StringVar(
            value=f"{self.visualizer.receiver_parameters.clock_bias_microseconds:g}"
        )
        for label, variable, width in (
            ("Sats", self.constellation_count_var, 4),
            ("Incl", self.constellation_inclination_var, 5),
            ("Alt km", self.constellation_altitude_var, 7),
            ("Lat", self.receiver_latitude_var, 8),
            ("Lon", self.receiver_longitude_var, 8),
            ("Mask", self.receiver_mask_var, 5),
            ("Clock us", self.receiver_clock_var, 7),
        ):
            self._add_scenario_entry(controls, label, variable, width)
        RoundedButton(
            controls,
            text="Apply",
            command=self.apply_scenario_entries,
            width=58,
            height=28,
        ).pack(side="left", padx=(4, 8))
        examples = list_example_scenarios()
        self.example_scenario_by_name = {
            example.name: example for example in examples
        }
        self.example_scenario_var = tk.StringVar(value=examples[0].name)
        example_menu = tk.OptionMenu(
            controls,
            self.example_scenario_var,
            *(example.name for example in examples),
        )
        example_menu.configure(
            bg="#202224",
            fg=TEXT,
            activebackground="#34383b",
            activeforeground=TEXT,
            highlightthickness=0,
            relief="flat",
            width=15,
            font=("Segoe UI", 8),
        )
        example_menu["menu"].configure(
            bg="#202224",
            fg=TEXT,
            activebackground="#34383b",
            activeforeground=TEXT,
            relief="flat",
        )
        example_menu.pack(side="left", padx=(0, 4))
        RoundedButton(
            controls,
            text="Example",
            command=self.load_example_scenario,
            width=70,
            height=28,
        ).pack(side="left", padx=(0, 8))
        RoundedButton(
            controls,
            text="Save",
            command=self.save_scenario,
            width=54,
            height=28,
        ).pack(side="left", padx=(0, 4))
        RoundedButton(
            controls,
            text="Load",
            command=self.load_scenario_from_file,
            width=54,
            height=28,
        ).pack(side="left", padx=(0, 8))
        self.scenario_status_var = tk.StringVar(value="")
        tk.Label(
            controls,
            textvariable=self.scenario_status_var,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

    def _add_scenario_entry(
        self,
        parent: tk.Misc,
        label: str,
        variable: tk.StringVar,
        width: int,
    ) -> None:
        tk.Label(
            parent,
            text=label,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 3))
        entry = tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            bg="#202224",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            justify="center",
            font=("Cascadia Mono", 9),
        )
        entry.pack(side="left", padx=(0, 7), ipady=4)
        entry.bind(
            "<Return>",
            lambda _event: self.apply_scenario_entries(),
        )

    def apply_scenario_entries(self) -> None:
        try:
            constellation = ConstellationParameters(
                satellite_count=int(self.constellation_count_var.get()),
                inclination_degrees=float(self.constellation_inclination_var.get()),
                altitude_kilometers=float(self.constellation_altitude_var.get()),
            )
            receiver = ReceiverParameters(
                latitude_degrees=float(self.receiver_latitude_var.get()),
                longitude_degrees=float(self.receiver_longitude_var.get()),
                altitude_meters=self.visualizer.receiver_parameters.altitude_meters,
                minimum_elevation_degrees=float(self.receiver_mask_var.get()),
                clock_bias_microseconds=float(self.receiver_clock_var.get()),
            )
        except ValueError as error:
            self.scenario_status_var.set(str(error))
            return
        self.visualizer.apply_scenario_parameters(constellation, receiver)
        self.scenario_status_var.set(
            f"{constellation.satellite_count} satellites, receiver {receiver.latitude_degrees:g}/{receiver.longitude_degrees:g}"
        )

    def load_example_scenario(self) -> None:
        name = self.example_scenario_var.get()
        example = self.example_scenario_by_name.get(name)
        if example is None:
            self.scenario_status_var.set(f"Unknown example {name}")
            return
        loaded = get_example_scenario(example.key)
        self.visualizer.load_scenario(loaded.scenario)
        self._sync_scenario_entry_vars()
        self._refresh_simulation_controls(reschedule=False)
        self.scenario_status_var.set(f"Loaded example: {loaded.name}")

    def save_scenario(self) -> None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".gps-scenario.json",
            filetypes=[
                ("GPS scenario", "*.gps-scenario.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not filename:
            return
        try:
            save_scenario_file(Path(filename), self.visualizer.export_scenario())
        except (OSError, ValueError) as error:
            messagebox.showerror("Save scenario", str(error))
            return
        self.scenario_status_var.set(f"Saved {Path(filename).name}")

    def load_scenario_from_file(self) -> None:
        filename = filedialog.askopenfilename(
            filetypes=[
                ("GPS scenario", "*.gps-scenario.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not filename:
            return
        try:
            scenario = load_scenario_file(Path(filename))
        except ValueError as error:
            messagebox.showerror("Load scenario", str(error))
            return
        self.visualizer.load_scenario(scenario)
        self._sync_scenario_entry_vars()
        self._refresh_simulation_controls(reschedule=False)
        self.scenario_status_var.set(f"Loaded {Path(filename).name}")

    def _sync_scenario_entry_vars(self) -> None:
        constellation = self.visualizer.constellation_parameters
        receiver = self.visualizer.receiver_parameters
        self.constellation_count_var.set(str(constellation.satellite_count))
        self.constellation_inclination_var.set(
            self._format_speed(constellation.inclination_degrees)
        )
        self.constellation_altitude_var.set(
            self._format_speed(constellation.altitude_kilometers)
        )
        self.receiver_latitude_var.set(f"{receiver.latitude_degrees:g}")
        self.receiver_longitude_var.set(f"{receiver.longitude_degrees:g}")
        self.receiver_mask_var.set(f"{receiver.minimum_elevation_degrees:g}")
        self.receiver_clock_var.set(f"{receiver.clock_bias_microseconds:g}")

    def toggle_simulation_playback(self) -> None:
        self.visualizer.toggle_playback()
        self._refresh_simulation_controls(reschedule=False)

    def step_simulation(self, seconds: float) -> None:
        self.visualizer.step(seconds)
        self._refresh_simulation_controls(reschedule=False)

    def apply_simulation_time_entry(self) -> None:
        try:
            seconds = self._parse_simulation_time(self.simulation_time_var.get())
        except ValueError:
            self._refresh_simulation_controls(reschedule=False)
            return
        self.visualizer.set_simulation_time(seconds)
        self._refresh_simulation_controls(reschedule=False)

    def apply_simulation_speed_entry(self) -> None:
        raw = self.simulation_speed_var.get().strip().lower().removesuffix("x")
        try:
            multiplier = float(raw)
        except ValueError:
            self._refresh_simulation_controls(reschedule=False)
            return
        if multiplier < 0.0:
            self._refresh_simulation_controls(reschedule=False)
            return
        self.visualizer.set_orbit_speed(multiplier)
        self._refresh_simulation_controls(reschedule=False)

    def _refresh_simulation_controls(self, reschedule: bool = True) -> None:
        if not hasattr(self, "simulation_time_var"):
            return
        if self.focus_get() is not self.simulation_time_entry:
            self.simulation_time_var.set(
                self._format_simulation_time(self.visualizer.clock.simulation_seconds)
            )
        if self.focus_get() is not self.simulation_speed:
            self.simulation_speed_var.set(
                self._format_speed(self.visualizer.clock.speed_multiplier)
            )
        self.play_pause_button.set_text(
            "Pause" if self.visualizer.clock.is_playing else "Play"
        )
        if reschedule:
            self.after(250, self._refresh_simulation_controls)

    @staticmethod
    def _format_simulation_time(seconds: float) -> str:
        total_seconds = max(0, int(round(seconds)))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _format_speed(multiplier: float) -> str:
        if multiplier.is_integer():
            return f"{int(multiplier)}"
        return f"{multiplier:g}"

    @staticmethod
    def _parse_simulation_time(value: str) -> float:
        value = value.strip()
        if not value:
            raise ValueError("simulation time is required")
        if ":" not in value:
            seconds = float(value)
            if seconds < 0.0:
                raise ValueError("simulation time must be non-negative")
            return seconds
        parts = value.split(":")
        if len(parts) > 3:
            raise ValueError("simulation time must be seconds, MM:SS, or HH:MM:SS")
        numbers = [int(part) for part in parts]
        if any(number < 0 for number in numbers):
            raise ValueError("simulation time must be non-negative")
        while len(numbers) < 3:
            numbers.insert(0, 0)
        hours, minutes, seconds = numbers
        if minutes >= 60 or seconds >= 60:
            raise ValueError("minutes and seconds must be below 60")
        return float(hours * 3600 + minutes * 60 + seconds)

    def _delete_previous_word(self, _event: tk.Event) -> str:
        if self.editor.tag_ranges("sel"):
            self.editor.delete("sel.first", "sel.last")
            return "break"
        line_start = self.editor.index("insert linestart")
        prefix = self.editor.get(line_start, "insert")
        if not prefix:
            if self.editor.compare("insert", ">", "1.0"):
                self.editor.delete("insert-1c", "insert")
            return "break"
        match = re.search(r"(?:\s+|[A-Za-z_]\w*|[^A-Za-z_\s]+)$", prefix)
        if match:
            start = self.editor.index(f"{line_start}+{match.start()}c")
            self.editor.delete(start, "insert")
        return "break"

    def _set_initial_split_positions(self) -> None:
        self.update_idletasks()
        content_width = self.content_split.winfo_width()
        ide_height = self.ide_split.winfo_height()
        if content_width > 0:
            self.content_split.sash_place(0, content_width // 2, 0)
        if ide_height > 0:
            self.ide_split.sash_place(0, 0, max(160, ide_height - 145))

    def toggle_documentation(self) -> None:
        self.documentation_open = not self.documentation_open
        self.documentation_button.set_active(self.documentation_open)
        if self.documentation_open:
            self.workspace_split.add(
                self.documentation_panel, before=self.content_split,
                width=390, minsize=330, stretch="never",
            )
        else:
            self.workspace_split.forget(self.documentation_panel)

    def _match_windows_titlebar(self) -> None:
        if not hasattr(self, "wm_frame"):
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            dark = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
            color = ctypes.c_int(0x00282624)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), 4)
        except (AttributeError, OSError):
            pass

    def check_for_updates(self, manual: bool = False) -> None:
        if manual and not is_packaged():
            messagebox.showinfo(
                "Updates",
                "Automatic updates are enabled in the packaged Windows application.",
                parent=self,
            )
            return

        def worker() -> None:
            try:
                release = find_update()
            except Exception as error:
                if manual:
                    self.after(
                        0,
                        lambda error=error: messagebox.showerror(
                            "Update check failed", str(error), parent=self
                        ),
                    )
                return
            self.after(0, lambda: self._handle_update_result(release, manual))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_update_result(self, release, manual: bool) -> None:
        if release is None:
            if manual:
                messagebox.showinfo(
                    "Updates",
                    f"GPS Learning Studio v{CURRENT_VERSION} is up to date.",
                    parent=self,
                )
            return
        install = messagebox.askyesno(
            "Update available",
            f"GPS Learning Studio v{release.version} is available.\n\n"
            "Download, install, and restart now?",
            parent=self,
        )
        if not install:
            return
        self._set_output(f"Downloading GPS Learning Studio v{release.version}...\n")

        def install_worker() -> None:
            try:
                download_and_install(release)
            except Exception as error:
                self.after(
                    0,
                    lambda error=error: messagebox.showerror(
                        "Update failed", str(error), parent=self
                    ),
                )

        threading.Thread(target=install_worker, daemon=True).start()

    def insert_import(self) -> None:
        module = simpledialog.askstring("Import module", "Python module name:", parent=self)
        if not module:
            return
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module):
            messagebox.showerror("Invalid module", "Enter a valid dotted Python module name.")
            return
        self.editor.insert("insert", f"import {module}\n")
        self.editor.focus_set()

    def insert_documentation_snippet(self, snippet: DocumentationSnippet) -> None:
        code = snippet.code.strip("\n")
        if self.editor.tag_ranges("sel"):
            self.editor.delete("sel.first", "sel.last")
        elif self.editor.compare("insert", ">", "1.0"):
            before_cursor = self.editor.get("insert-2c", "insert")
            if before_cursor and not before_cursor.endswith("\n\n"):
                self.editor.insert("insert", "\n" if before_cursor.endswith("\n") else "\n\n")
        self.editor.insert("insert", code + "\n")
        self.highlighter.highlight()
        self.editor.focus_set()

    def check_documentation_challenge(self, page: DocumentationPage) -> None:
        source = self.editor.get("1.0", "end-1c")
        feedback = evaluate_documentation_challenge(page, source)
        status = "Ready" if feedback.passed else "Needs work"
        lines = [f"Challenge check: {page.title}", status]
        lines.extend(f"- {message}" for message in feedback.messages)
        self._set_output("\n".join(lines) + "\n")
        if feedback.passed:
            self.documentation_panel.mark_challenge_completed(page)
        self.editor.focus_set()

    def load_documentation_lesson_state(self, page: DocumentationPage) -> None:
        scenario = lesson_scenario_for_page(page)
        if scenario is None:
            self._set_output(f"{page.title} does not define a lesson scenario.\n")
            return
        self.visualizer.load_scenario(scenario)
        self._sync_scenario_entry_vars()
        self._refresh_simulation_controls(reschedule=False)
        example = get_example_scenario(page.lesson_scenario_key or "")
        self.scenario_status_var.set(f"Loaded lesson state: {page.title}")
        self._set_output(
            f"Loaded {page.title} lesson state from {example.name}.\n"
        )
        self.editor.focus_set()

    def save_documentation_progress(self, progress: DocumentationProgress) -> None:
        self.documentation_progress = progress
        try:
            save_documentation_progress(progress, self.documentation_progress_path)
        except OSError as error:
            self._set_output(f"Could not save lesson progress: {error}\n")

    def open_script(self) -> None:
        filename = filedialog.askopenfilename(
            parent=self, title="Open Python script",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            content = Path(filename).read_text(encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Open failed", str(error))
            return
        self.current_file = Path(filename)
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self.file_label.configure(text=self.current_file.name)
        self.highlighter.highlight()

    def save_script(self) -> None:
        filename = str(self.current_file) if self.current_file else filedialog.asksaveasfilename(
            parent=self, title="Save Python script", defaultextension=".py",
            initialfile="orbit_script.py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            Path(filename).write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Save failed", str(error))
            return
        self.current_file = Path(filename)
        self.file_label.configure(text=self.current_file.name)

    def run_code(self) -> None:
        source = self.editor.get("1.0", "end-1c")
        self._set_output("Running...\n")
        thread = threading.Thread(target=self._execute, args=(source,), daemon=True)
        thread.start()

    def _execute(self, source: str) -> None:
        stream = io.StringIO()
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                exec(compile(source, str(self.current_file or "<orbit-studio>"), "exec"),
                     self.execution_namespace, self.execution_namespace)
        except BaseException:
            traceback.print_exc(file=stream)
        result = stream.getvalue() or "Finished with no output.\n"
        self.output_queue.put(result)

    def _poll_output(self) -> None:
        try:
            while True:
                self._set_output(self.output_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(50, self._poll_output)

    def _set_output(self, content: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", content)
        self.output.configure(state="disabled")


def main() -> None:
    app = OrbitStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
