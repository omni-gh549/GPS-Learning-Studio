# GPS Learning Studio

A dependency-free Python desktop application with:

- An animated 3D wireframe Earth, ground stations, and visible satellite links
- Four orbiting Globalstar satellites with hover IDs and realistic 113-116 minute periods
- A syntax-highlighted Python editor
- Named simulator modules with explicit imports
- Function suggestions and autocomplete
- Multi-page in-app documentation with lesson objectives, prerequisites,
  a learning path, saved completion state, runnable snippets, API references, and coding challenges
- Open, save, and run controls

See [ROADMAP.md](ROADMAP.md) for the prioritized feature plan.

## Run

Double-click `launch.bat`, or run:

```powershell
python app.py
```

## Windows executable and updates

Build the portable executable with:

```powershell
python -m pip install pyinstaller
pyinstaller --clean GPS-Learning-Studio.spec
```

The result is `dist\GPS-Learning-Studio.exe`. Packaged builds check the latest
GitHub Release shortly after startup and can download, replace, and restart
themselves when a newer version is available.

Run the updater integration test with:

```powershell
python -m unittest tests.test_updater -v
```

To publish a new version:

1. Update `CURRENT_VERSION` in `gps_sim\updater.py`.
2. Commit and push the feature.
3. Tag the commit with the matching version, such as `v1.1.0`, and push the tag.

The GitHub Actions release workflow builds the Windows executable and attaches
it to the release automatically.

Editor shortcuts:

- `F5`: run code
- `Ctrl+S`: save script
- `Ctrl+O`: open script
- Function suggestions appear automatically as you type
- Lesson pages include runnable snippets that can be inserted into the editor
- The Learning path page sequences orbit telemetry, visibility, positioning,
  and accuracy into one course track
- Challenge lesson pages include a lightweight checker that reviews the editor
  script for syntax and the key APIs needed by the exercise, then reports
  focused feedback in the output pane

Visualizer controls:

- Use Pause/Play to stop or resume simulation time without resetting the scene
- Use Step to advance the paused simulation by 60 seconds
- Edit the Time field with seconds, `MM:SS`, or `HH:MM:SS` to jump to a specific
  simulation timestamp
- Edit Speed to change the orbital time-scale multiplier, such as `0x`, `1x`,
  `2x`, or `20x`
- Edit Sats, Incl, and Alt km to regenerate the active classroom constellation
- Edit Lat, Lon, Mask, and Clock us to move the receiver and change its
  pseudorange clock bias
- Use Save and Load in the scenario controls to write or restore a versioned
  `.gps-scenario.json` file with constellation, receiver, simulation time, and
  orbital speed
- Hold the left mouse button and drag to rotate the camera
- Hover a satellite dot to show its Globalstar ID
- Orange markers show named ground stations
- Click a ground station to inspect its live azimuth, elevation, range, and visibility table
- The selected station also displays a simulated receiver position fix with true
  ECEF position, estimated ECEF position, residuals, clock bias, horizontal error, vertical error, and 3D error
- The accuracy comparison panel shows a clean before fix beside a seeded-error
  after fix, with a rolling 3D position-error history plot
- Green dashed links show satellites above each station's elevation mask
- Amber dashed links show the selected receiver's simplified pseudorange
  measurements, with brighter links for satellites above the elevation mask

The Earth and satellites animate at real-time orbital rates by default. Use the
visual controls or `gps_sim.dynamics` functions when a faster classroom
demonstration, paused inspection, or repeatable timestamp is useful.

## Simulator modules

Import the module required by the functions you use:

```python
import gps_sim.constellation as constellation
import gps_sim.coordinates as coordinates
import gps_sim.dynamics as dynamics
import gps_sim.errors as errors
import gps_sim.ground_stations as ground_stations
import gps_sim.measurements as measurements
import gps_sim.positioning as positioning
import gps_sim.scenario_parameters as scenario_parameters
import gps_sim.scenarios as scenarios
import gps_sim.visibility as visibility

print(constellation.get_satellite_states())
print(constellation.get_satellite_count())

dynamics.set_orbital_time_scale(2.0)
dynamics.set_earth_rotation_scale(0.5)
dynamics.pause_simulation()
dynamics.step_simulation(60.0)
dynamics.set_simulation_time(3600.0)
print(dynamics.get_simulation_time())
dynamics.play_simulation()
dynamics.reset_simulation()

station = ground_stations.create_station(
    "Aberdeen",
    latitude_degrees=57.1497,
    longitude_degrees=-2.0943,
    altitude_meters=65.0,
    minimum_elevation_degrees=10.0,
)
ground_stations.update_station("Aberdeen", minimum_elevation_degrees=15.0)
print(ground_stations.list_stations())
ground_stations.remove_station("Aberdeen")

eci = coordinates.orbital_to_eci(
    radius_meters=26_560_000.0,
    inclination_degrees=55.0,
    longitude_of_ascending_node_degrees=30.0,
    orbital_angle_degrees=120.0,
)
ecef = coordinates.eci_to_ecef(eci, earth_rotation_degrees=15.0)
local = coordinates.ecef_to_local_horizon(ecef, station)
print(local)
look = visibility.calculate_visibility(ecef, station)
print(look.azimuth_degrees, look.elevation_degrees)
print(look.range_meters, look.is_visible)
station_ecef = coordinates.station_to_ecef(station)
clock_bias = measurements.ReceiverClockBias(seconds=0.000001)
reading = measurements.calculate_pseudorange(
    receiver_ecef=station_ecef,
    satellite_ecef=ecef,
    receiver_clock_bias=clock_bias,
)
print(clock_bias.range_error_meters())
print(reading.geometric_range_meters, reading.pseudorange_meters)
error_model = errors.classroom_error_model(seed=42)
error = error_model.sample("Aberdeen-SV01")
print(error.by_source())
ionosphere_lab = error_model.with_source_settings("ionospheric_delay", scale=2.0)
no_multipath = error_model.with_source_settings("multipath", enabled=False)
print(ionosphere_lab.sample("Aberdeen-SV01").by_source()["ionospheric_delay"])
print(no_multipath.sample("Aberdeen-SV01").by_source()["multipath"])
print(error_model.apply_to_pseudorange(reading.pseudorange_meters, "Aberdeen-SV01"))
observation = positioning.PseudorangeObservation(
    satellite_ecef=ecef,
    pseudorange_meters=reading.pseudorange_meters,
)
observations = [
    observation,
    # Add three or more observations from other satellite ECEF positions
    # before solving.
]
if len(observations) >= 4:
    fix = positioning.solve_position(observations)
    report = positioning.calculate_position_error(fix, station_ecef, station)
    dop = positioning.calculate_dilution_of_precision(
        observations,
        receiver_ecef=station_ecef,
        reference_station=station,
    )
    print(fix.receiver_ecef, fix.receiver_clock_bias_seconds)
    print(report.max_abs_residual_meters)
    print(report.horizontal_error_meters, report.vertical_error_meters)
    print(report.position_error_meters)
    print(dop.gdop, dop.pdop, dop.hdop, dop.vdop)
```

`GroundStation` validates latitude, longitude, altitude, and elevation-mask
inputs without starting the Tkinter application. Named stations can be created,
updated, listed, and removed through the same headless module. The coordinate
module converts circular-orbit positions through standard ECI and ECEF frames
to station-centred east-north-up coordinates. Station conversion uses WGS84;
the inertial-to-fixed conversion takes an explicit Earth-rotation angle so
classroom scenarios remain deterministic. Visibility calculations are tracked
in a headless module that reports azimuth clockwise from north, elevation,
slant range, and whether the station's minimum elevation mask is met.
The measurements module calculates straight-line geometric range and
pseudorange, using a configurable receiver clock bias so timing-error examples
remain deterministic. Clock bias can be set directly in seconds or created from
an equivalent range error in meters.
The errors module provides deterministic, seedable pseudorange error models for
satellite clock, receiver clock, ionospheric delay, tropospheric delay,
multipath, and measurement noise. A seed plus measurement key reproduces the
same per-source offsets, which makes accuracy experiments repeatable while
still letting students compare different satellites or scenarios. Each standard
source can be enabled, disabled, and scaled independently, so a lesson can
isolate one component without changing the other sampled offsets.
The positioning module estimates receiver Earth-fixed x, y, z and receiver
clock bias from four or more pseudorange observations. It uses a dependency-free
iterative least-squares solver and raises clear diagnostics for insufficient or
singular satellite geometry. Its accuracy report calculates residual statistics
and splits position error into local horizontal, vertical, and 3D components.
It also calculates GDOP, PDOP, HDOP, and VDOP from the satellite geometry,
using a reference station to split position geometry into local horizontal and
vertical components.
Four satellites are normally required because the receiver must solve four
unknowns at once: three Earth-fixed position coordinates plus receiver clock
bias. Each pseudorange contributes one distance equation, so a fourth
independent satellite lets the solver estimate clock bias instead of pretending
the receiver clock is already synchronized.
The scenarios module saves and loads versioned `.gps-scenario.json` files.
Each file stores the editable constellation, receiver, simulation timestamp,
and orbital speed multiplier. Loading a file validates every value before it
changes the visualizer, so unsupported schema versions, missing sections, and
out-of-range classroom inputs produce actionable messages instead of partial
state changes.
The visualizer starts with an Aberdeen station using a 5-degree elevation mask
and automatically redraws markers and links when stations are created, updated,
or removed in the editor. Click any front-facing station marker to select it;
the live table reports every satellite's look angles, range, and elevation-mask
status using the same visibility results that drive the green links. The
receiver fix panel uses the selected station as the true receiver, generates
pseudoranges to the current constellation model, and reports the estimated
position, residuals, receiver clock bias, horizontal error, vertical error, and
3D position error. The accuracy comparison panel keeps the clean pseudorange
solution visible as a before case, applies the deterministic classroom error
model as the after case, and plots both 3D position errors over time. Amber
dashed measurement links connect the selected receiver to the satellites used
by that pseudorange display, while muted amber keeps below-mask observations
easy to compare with visible links.

Click the documentation icon in the left sidebar for descriptions of the
simulator, editor, file controls, and every public simulator function. Lesson
pages show estimated duration, prerequisites, objectives, and a session
completion toggle so a student can track what they have finished across app
restarts. The Learning path page ties the course together as four milestones:
orbit telemetry in Quick start, visibility in Ground stations, positioning in
Position fixes, and accuracy experiments in Error and accuracy. Each milestone
lesson also shows its path step and outcome. The app saves completed lessons,
passed challenge checks, and the last open lesson to local application data.
Lesson pages also provide runnable snippets that insert directly into the editor,
giving each lab a ready-to-run starting point. Challenge pages add a Check
challenge action that catches syntax errors and missing required APIs before the
student compares the script output with the lesson success check. Students can
reset saved lesson progress from the documentation panel and reveal sample
solutions after attempting a challenge.
The Ground stations lesson is a guided 15-minute lab covering
latitude/longitude, look angles, elevation masks, pass visibility, and an
editor-ready coding challenge.
The Position fixes lesson is a worked trilateration lab covering pseudorange
generation, receiver clock bias, solver setup, residual checks, and a solver
challenge.
The Error and accuracy lesson is a controlled-experiments lab covering seeded
measurement errors, one-source-at-a-time comparisons, residuals, horizontal and
vertical position error, 3D error, DOP, and an accuracy challenge.
