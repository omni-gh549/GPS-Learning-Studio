# GPS Learning Studio

A dependency-free Python desktop application with:

- An animated 3D wireframe Earth and starfield
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

The Earth and satellites animate at real-time orbital rates. Use
`dynamics.set_orbital_time_scale(...)` in the editor when a faster classroom
demonstration is useful.

## Simulator modules

Import the module required by the functions you use:

```python
import gps_sim.constellation as constellation
import gps_sim.dynamics as dynamics

print(constellation.get_satellite_states())
print(constellation.get_satellite_count())

dynamics.set_orbital_time_scale(2.0)
dynamics.set_earth_rotation_scale(0.5)
dynamics.reset_simulation()
```

Click the documentation icon in the left sidebar for descriptions of the
simulator, editor, file controls, and every public simulator function.
