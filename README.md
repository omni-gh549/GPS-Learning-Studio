# GPS Learning Studio

A dependency-free Python desktop application with:

- An animated 3D wireframe Earth, ground stations, and visible satellite links
- Four orbiting Globalstar satellites with hover IDs and realistic 113-116 minute periods
- A syntax-highlighted Python editor
- Named simulator modules with explicit imports
- Function suggestions and autocomplete
- Multi-page in-app documentation with lessons, API references, and placeholders
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

Visualizer controls:

- Hold the left mouse button and drag to rotate the camera
- Hover a satellite dot to show its Globalstar ID
- Orange markers show named ground stations
- Green dashed links show satellites above each station's elevation mask

The Earth and satellites animate at real-time orbital rates. Use
`dynamics.set_orbital_time_scale(...)` in the editor when a faster classroom
demonstration is useful.

## Simulator modules

Import the module required by the functions you use:

```python
import gps_sim.constellation as constellation
import gps_sim.coordinates as coordinates
import gps_sim.dynamics as dynamics
import gps_sim.ground_stations as ground_stations
import gps_sim.visibility as visibility

print(constellation.get_satellite_states())
print(constellation.get_satellite_count())

dynamics.set_orbital_time_scale(2.0)
dynamics.set_earth_rotation_scale(0.5)
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
The visualizer starts with an Aberdeen station using a 5-degree elevation mask
and automatically redraws markers and links when stations are created, updated,
or removed in the editor.

Click the documentation icon in the left sidebar for descriptions of the
simulator, editor, file controls, and every public simulator function.
