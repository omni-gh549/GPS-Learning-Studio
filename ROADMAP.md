# GPS Learning Studio Roadmap

This roadmap advances the application from an orbit visualizer with a Python
workspace into a guided, technically credible GPS learning environment.

## Product principles

- Every simulator feature should support an observable learning outcome.
- New physics should be exposed through a small, documented Python API.
- Visual changes, telemetry, and lesson content should reinforce one another.
- Models should state their assumptions instead of implying operational-grade
  GPS accuracy.
- Core simulation logic should remain testable without starting Tkinter.

## Phase 1: Ground stations and visibility

**Priority:** Next

Build the geometry needed to answer: "Which satellites can a receiver see?"

### Features

- [x] Add a `gps_sim.ground_stations` module.
- [x] Create, update, list, and remove stations using latitude, longitude, altitude,
  and minimum elevation angle.
- [x] Convert satellite and station positions between orbital, Earth-centred, and
  local horizon coordinate systems.
- [x] Calculate azimuth, elevation, range, and line-of-sight visibility.
- [x] Draw stations on Earth and highlight visible satellite links.
- [x] Let users select a station and inspect its live visibility table.
- [x] Replace the Ground stations placeholder with a guided lesson and coding
  challenge.

### Acceptance criteria

- A station at a known coordinate produces deterministic visibility results.
- The visualizer and Python API report the same visible satellites.
- Geometry calculations have unit tests covering horizon and overhead cases.
- The lesson teaches latitude/longitude, elevation masks, and pass visibility.

## Phase 2: Receiver measurements and position fixes

**Priority:** High

Build the measurement and solver pipeline needed to answer: "How does a GPS
receiver calculate its position?"

### Features

- [x] Add a `gps_sim.measurements` module for geometric range and pseudorange.
- [x] Add a configurable receiver clock bias.
- [x] Add a `gps_sim.positioning` module with an iterative four-unknown solver for
  receiver position and clock bias.
- [x] Display the true receiver position, estimated position, residuals, and error.
- [x] Visualize range spheres or simplified measurement links.
- [x] Explain why four satellites are normally required for a 3D fix.
- [x] Replace the Position fixes placeholder with a worked trilateration lesson and
  a solver challenge.

### Acceptance criteria

- A noise-free four-satellite scenario converges within a documented tolerance.
- Insufficient or poor geometry produces a clear diagnostic instead of a crash.
- Solver tests cover convergence, clock bias, and invalid input.
- Students can generate pseudoranges and recover the simulated receiver state
  through the public API.

## Phase 3: Error and accuracy laboratory

**Priority:** High

Turn positioning into an experiment where students can isolate each major error
source.

### Features

- [x] Add deterministic, seedable models for satellite clock, receiver clock,
  ionospheric delay, tropospheric delay, multipath, and measurement noise.
- [x] Allow each error source to be enabled, disabled, and scaled independently.
- [x] Calculate residuals, horizontal error, vertical error, and 3D position error.
- [x] Calculate satellite geometry metrics including GDOP, PDOP, HDOP, and VDOP.
- [x] Add a before/after comparison view and time-series error plot.
- [ ] Replace the Error and accuracy placeholder with controlled experiments.

### Acceptance criteria

- Seeded scenarios are reproducible.
- Enabling one error source changes only the intended measurement component.
- DOP calculations are verified against known geometry fixtures.
- The lesson distinguishes measurement error from poor satellite geometry.

## Phase 4: Guided learning system

**Priority:** Medium

Make the documentation pages behave like a coherent course rather than a static
reference.

### Features

- [ ] Add lesson objectives, prerequisites, estimated duration, and completion
  state.
- [ ] Add runnable code snippets that can be inserted into the editor.
- [ ] Add lightweight checks for challenges and show focused feedback.
- [ ] Save progress, completed challenges, and the last open lesson locally.
- [ ] Add a reset-progress option and sample solution reveal.
- [ ] Add a learning path covering orbit telemetry, visibility, positioning, and
  accuracy.

### Acceptance criteria

- Progress survives an application restart.
- Challenge checks accept equivalent valid solutions where practical.
- Every simulator module has an API page, lesson, and at least one exercise.
- Users can resume from the last lesson without finding files manually.

## Phase 5: Simulation controls and scenario management

**Priority:** Medium

Make experiments easier to set up, repeat, and share.

### Features

- [ ] Add play, pause, step, simulation-time, and speed controls.
- [ ] Allow constellation and receiver parameters to be edited in the UI.
- [ ] Save and load versioned scenario files.
- [ ] Ship example scenarios for strong geometry, poor geometry, clock bias,
  atmospheric delay, and multipath.
- [ ] Add a reset-to-lesson-state action.
- [ ] Export telemetry and experiment results as CSV or JSON.

### Acceptance criteria

- Loading a saved scenario reproduces the same initial state.
- Invalid scenario files produce actionable validation messages.
- A lesson can open its required scenario with one action.
- Exported data includes units and simulation timestamps.

## Phase 6: Architecture, testing, and release quality

**Priority:** Continuous, complete before a stable 1.0 release

### Features

- [ ] Move orbital and coordinate calculations out of `app.py` into headless model
  modules.
- [ ] Separate simulation state from Tkinter rendering.
- [ ] Add unit tests for dynamics, coordinates, visibility, measurements, solvers,
  errors, and scenario serialization.
- [ ] Add integration tests for the editor-facing API.
- [ ] Make standard test discovery run the full suite.
- [ ] Run tests and executable smoke checks in GitHub Actions before publishing.
- [ ] Add updater integrity verification using release checksums.
- [ ] Add structured release notes and migration handling for saved scenarios.

### Acceptance criteria

- Simulation tests run without creating a window.
- `python -m unittest discover -v` executes the complete suite.
- A release is not published when tests or the packaged smoke check fail.
- Update downloads are verified before the current executable is replaced.

## Recommended release sequence

| Release | Theme | Main outcome |
| --- | --- | --- |
| `v0.2` | Ground stations | Live satellite visibility from a chosen location |
| `v0.3` | Position fixes | Pseudorange generation and a working receiver solver |
| `v0.4` | Accuracy lab | Error toggles, DOP, and position-error experiments |
| `v0.5` | Guided course | Saved progress, runnable examples, and challenge checks |
| `v0.6` | Scenarios | Repeatable experiments, controls, and data export |
| `v1.0` | Stable studio | Tested architecture, secure updates, and complete core course |

## Deliberately deferred

- Real broadcast ephemeris, RINEX, or live GNSS data ingestion.
- Full multi-constellation support for Galileo, GLONASS, and BeiDou.
- Carrier-phase positioning, RTK, PPP, and ambiguity resolution.
- High-fidelity atmospheric or relativistic corrections.
- Accounts, cloud sync, classroom management, or online collaboration.

These are valuable extensions after the core learning loop is complete and the
underlying coordinate, measurement, and solver models are well tested.
