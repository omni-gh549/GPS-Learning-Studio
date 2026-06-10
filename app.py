from __future__ import annotations

import builtins
import contextlib
import io
import keyword
import math
import queue
import random
import re
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from gps_sim.runtime import bind_visualizer
from gps_sim.updater import CURRENT_VERSION, download_and_install, find_update, is_packaged


BG = "#242628"
PANEL = "#2b2e31"
BORDER = "#4a4e52"
TEXT = "#d7d9dc"
MUTED = "#92979c"
ACCENT = "#9bb7cc"
EARTH = "#6f91a8"
ORBIT = "#555f67"
SATELLITE_COLORS = ("#d7a86e", "#7db6a6", "#b58dc7", "#d6cc75")

SIMULATOR_COMPLETIONS = (
    ("import gps_sim.constellation as constellation", "import gps_sim.constellation as constellation", "#8eb6d8"),
    ("import gps_sim.dynamics as dynamics", "import gps_sim.dynamics as dynamics", "#8eb6d8"),
    ("import gps_sim.ground_stations as ground_stations", "import gps_sim.ground_stations as ground_stations", "#8eb6d8"),
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
class DocumentationPage:
    title: str
    eyebrow: str
    summary: str
    sections: tuple[tuple[str, str], ...]
    placeholder: bool = False


DOCUMENTATION_PAGES = (
    DocumentationPage(
        "Welcome",
        "START HERE",
        "Learn Python by changing a live orbital simulation and reading its telemetry.",
        (
            ("Your workspace", "The left pane is a rotatable model of Earth and the active satellite constellation. The right pane is a Python editor with output below it."),
            ("First run", "Press F5 or choose Run. The starter script imports the constellation module, reads every satellite state, and prints the result."),
            ("A good next experiment", "Change the script so it prints only each satellite ID and orbital angle. Run it several times and watch the angles advance."),
        ),
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
        "Control orbital propagation, Earth rotation, and simulation reset.",
        (
            ("Import", "import gps_sim.dynamics as dynamics"),
            ("set_orbital_time_scale(multiplier)", "dynamics.set_orbital_time_scale(2.0)\n\nSets orbital speed. Use 1.0 for real time, a larger number to accelerate, or 0.0 to pause the satellites."),
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
            ("Time", "The four satellites use 113-116 minute orbital periods. Increase the orbital time scale to make changes easier to observe during a lesson."),
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
        "COMING SOON",
        "Model station coordinates, elevation masks, and satellite visibility windows.",
        (("Planned page", "This lesson will introduce latitude and longitude, line of sight, elevation angle, and simple pass prediction."),),
        placeholder=True,
    ),
    DocumentationPage(
        "Position fixes",
        "COMING SOON",
        "Estimate a receiver position from simulated pseudorange measurements.",
        (("Planned page", "This lesson will cover range measurements, clock bias, trilateration, and the geometry needed for a four-satellite fix."),),
        placeholder=True,
    ),
    DocumentationPage(
        "Error and accuracy",
        "COMING SOON",
        "Explore timing error, atmospheric delay, multipath, and dilution of precision.",
        (("Planned page", "This lesson will turn common GPS error sources on and off, then compare their effect on the calculated position."),),
        placeholder=True,
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


class DocumentationPanel(tk.Frame):
    def __init__(self, master: tk.Misc, close_command):
        super().__init__(master, bg=PANEL, width=390)
        self.grid_propagate(False)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.current_page = 0

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
        for page in DOCUMENTATION_PAGES:
            marker = "  " if not page.placeholder else "+ "
            self.page_list.insert("end", marker + page.title)
        self.page_list.bind("<<ListboxSelect>>", self._select_page)

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
        self.show_page(0)

    def _select_page(self, _event: tk.Event) -> None:
        selection = self.page_list.curselection()
        if selection:
            self.show_page(selection[0])

    def show_page(self, index: int) -> None:
        index = max(0, min(len(DOCUMENTATION_PAGES) - 1, index))
        self.current_page = index
        page = DOCUMENTATION_PAGES[index]
        self.page_list.selection_clear(0, "end")
        self.page_list.selection_set(index)
        self.page_list.activate(index)
        self.page_list.see(index)
        self.page_status.configure(text=f"{index + 1} / {len(DOCUMENTATION_PAGES)}")

        self.body.configure(state="normal")
        self.body.delete("1.0", "end")
        self.body.insert("end", page.eyebrow + "\n", "eyebrow")
        self.body.insert("end", page.title + "\n", "title")
        self.body.insert("end", page.summary + "\n", "summary")
        for heading, content in page.sections:
            self.body.insert("end", heading + "\n", "heading")
            for line in content.splitlines():
                is_code = (
                    line.startswith("import ")
                    or line.startswith("constellation.")
                    or line.startswith("dynamics.")
                    or line.startswith("ground_stations.")
                    or line.startswith("station =")
                    or line.startswith("states =")
                    or line.startswith("leader =")
                    or line.startswith("print(")
                    or line.startswith("for ")
                    or line.startswith("    ")
                )
                self.body.insert("end", line + "\n", "code" if is_code else "body")
            self.body.insert("end", "\n", "body")
        self.body.configure(state="disabled")
        self.body.yview_moveto(0)


@dataclass
class Satellite:
    sat_id: int
    inclination: float
    node: float
    phase: float
    speed: float
    color: str


class EarthVisualizer(tk.Canvas):
    def __init__(self, master: tk.Misc):
        super().__init__(
            master, bg=PANEL, highlightthickness=0, bd=0, cursor="crosshair"
        )
        self.start_time = time.perf_counter()
        self.earth_rotation = 0.0
        self.camera_yaw = 0.0
        self.camera_pitch = math.radians(-18)
        self.drag_origin: tuple[int, int] | None = None
        self.orbit_speed = 1.0
        self.earth_speed = 1.0
        self.last_frame_time = time.perf_counter()
        self.running = True
        self.projected_satellites: list[tuple[float, float, Satellite]] = []
        self.hovered_id: int | None = None
        self.stars: list[tuple[float, float, float]] = []
        self.satellites = [
            Satellite(1, math.radians(52), math.radians(12), 0.0, math.tau / (114 * 60), SATELLITE_COLORS[0]),
            Satellite(2, math.radians(52), math.radians(102), 1.45, math.tau / (115 * 60), SATELLITE_COLORS[1]),
            Satellite(3, math.radians(70), math.radians(202), 2.85, math.tau / (113 * 60), SATELLITE_COLORS[2]),
            Satellite(4, math.radians(35), math.radians(292), 4.35, math.tau / (116 * 60), SATELLITE_COLORS[3]),
        ]
        self.bind("<Configure>", self._make_stars)
        self.bind("<Motion>", self._on_motion)
        self.bind("<ButtonPress-1>", self._start_camera_drag)
        self.bind("<B1-Motion>", self._drag_camera)
        self.bind("<ButtonRelease-1>", self._stop_camera_drag)
        self.bind("<Leave>", lambda _event: self._clear_hover())
        self.after(33, self._animate)

    def set_orbit_speed(self, multiplier: float) -> None:
        self.orbit_speed = max(0.0, float(multiplier))

    def set_earth_speed(self, multiplier: float) -> None:
        self.earth_speed = max(0.0, float(multiplier))

    def reset(self) -> None:
        self.start_time = time.perf_counter()
        self.earth_rotation = 0.0
        self.camera_yaw = 0.0
        self.camera_pitch = math.radians(-18)
        self.orbit_speed = 1.0
        self.earth_speed = 1.0

    def satellite_data(self) -> list[dict[str, float | int]]:
        elapsed = time.perf_counter() - self.start_time
        return [
            {
                "id": sat.sat_id,
                "inclination_degrees": round(math.degrees(sat.inclination), 2),
                "longitude_of_ascending_node_degrees": round(math.degrees(sat.node), 2),
                "orbital_angle_degrees": round(
                    math.degrees(sat.phase + elapsed * sat.speed * self.orbit_speed) % 360, 2
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
        point = (math.cos(angle) * 1.58, 0.0, math.sin(angle) * 1.58)
        point = self._rotate_x(point, sat.inclination)
        return self._rotate_y(point, sat.node)

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

        elapsed = time.perf_counter() - self.start_time
        self.projected_satellites = []
        draw_order: list[tuple[float, float, float, Satellite]] = []
        for sat in self.satellites:
            orbit = [self._orbit_point(sat, index * math.pi / 64) for index in range(129)]
            self._draw_curve(orbit, radius, ORBIT, 1.0, (3, 5))
            angle = sat.phase + elapsed * sat.speed * self.orbit_speed
            sx, sy, sz = self._project(self._orbit_point(sat, angle), radius)
            draw_order.append((sz, sx, sy, sat))

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

        self.create_text(18, 18, text="ORBITAL VIEW", anchor="nw", fill=MUTED,
                         font=("Segoe UI", 9, "bold"))
        self.create_text(18, height - 18, text="DRAG TO ROTATE  |  HOVER SATELLITES FOR ID", anchor="sw",
                         fill="#686d72", font=("Segoe UI", 8))

    def _animate(self) -> None:
        now = time.perf_counter()
        elapsed = min(0.1, now - self.last_frame_time)
        self.last_frame_time = now
        if self.running:
            self.earth_rotation += elapsed * (math.tau / 86164) * self.earth_speed
            self._draw_scene()
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
        self.hovered_id = None
        self.configure(cursor="fleur")

    def _drag_camera(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        previous_x, previous_y = self.drag_origin
        self.camera_yaw += (event.x - previous_x) * 0.009
        self.camera_pitch += (event.y - previous_y) * 0.009
        self.camera_pitch = max(math.radians(-85), min(math.radians(85), self.camera_pitch))
        self.drag_origin = (event.x, event.y)

    def _stop_camera_drag(self, _event: tk.Event) -> None:
        self.drag_origin = None
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
                r"set_orbital_time_scale|set_earth_rotation_scale|reset_simulation)\b"
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
        self._match_windows_titlebar()
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
            self.workspace_split, self.toggle_documentation
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
