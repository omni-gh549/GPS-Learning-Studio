# GPS Learning Studio

A dependency-free Python desktop application with:

- An animated 3D wireframe Earth and starfield
- Four orbiting Globalstar satellites with hover IDs and realistic 113-116 minute periods
- A syntax-highlighted Python editor
- Named simulator modules with explicit imports
- Function suggestions and autocomplete
- Expandable in-app documentation
- Open, save, and run controls

## Run

Double-click `launch.bat`, or run:

```powershell
python app.py
```

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
