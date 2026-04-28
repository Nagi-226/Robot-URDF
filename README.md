# Robot URDF Studio

A Windows 11 desktop workspace for robot-arm development, CAD script generation, and embedded-device tooling.

## Current product direction

The product now unifies three layers:

1. **CAD generation and incremental editing**
   - Each part can be represented by its own Python script
   - AI can edit the script directly instead of rewriting original files
   - The `@cad` handle system tags geometric features so fine-grained edits can target holes, faces, fillets, slots, and mounting regions
   - Export targets include STEP, STL, DXF, GLB, topology data, and URDF

2. **Robot structure and visualization**
   - URDF import and parsing
   - Robot link/joint structure viewing
   - 2D skeleton preview as the current fallback viewport
   - 3D viewport backend abstraction ready for a future real renderer

3. **Operator workflow and device tools**
   - Joint sliders and pose presets
   - Workspace navigation and selection details
   - Serial/network/device console scaffolding
   - Telemetry, logs, and packaging-ready Windows launcher scripts

The long-term goal is to make the system feel like a professional engineering workbench where CAD generation, robot assembly, and model operation all stay connected.

## Run

Preferred launchers on Windows:

```powershell
.\run.ps1
```

or double-click:

```bat
start.bat
```

Fallback:

```bash
py -3.12 main.py
```

## Current product version

- Current tracked line: `v0.4.1`
- The CAD overview panel now surfaces stable version, readiness, writer, artifact count, written artifact count, edit summary, and topology node count
- The CAD overview remains read-only and overview-only by design

## What this prototype includes

- Dark Codex-style desktop shell
- 2D skeleton viewport with auto-centering and joint-driven kinematics
- 3D placeholder viewport ready for a real backend swap-in
- Pluggable rendering backend architecture
- Joint sliders and pose presets (`Home`, `Reach`, `Inspect`)
- Workspace browser scaffold
- Project tree, URDF structure tree, selection details panel, and resource summary panel
- Unified robot model layer (`robot_model.py`)
- Viewport render protocol (`rendering.py`)
- Kinematic chain builder and FK solver
- Serial/network/task panel placeholders
- Modular layout prepared for telemetry and embedded workflows

## CAD workflow vision

The CAD layer is designed around per-part Python scripts under `models/<robot>/`.

Example concept:

```python
from cad import workspace

with workspace("wrist_link") as w:
    body = w.box(60, 50, 30)
    body = body.edges("|Z").fillet(2)      # @cad: edge_rounding
    body = body.faces(">Y").workplane()     # @cad: shaft_mount
    body = body.circle(15).extrude(20)
    w.export("wrist_link", ["step", "stl", "dxf", "glb"])
```

The important product rule is that AI should be able to:
- identify the feature through a stable handle
- edit only the relevant part of the script
- re-export without regenerating the entire model from scratch
- carry the result into URDF and robot-view workflows

## Project memory

- `CLAUDE.md` stores the long-context working contract for future development
- Keep changes stability-first and preserve launchability

## Dependencies

```bash
pip install -r requirements.txt
```

Planned CAD dependencies not yet committed to runtime requirements:

```bash
pip install cadquery trimesh ezdxf
```

## Windows packaging direction

Build a desktop executable with:

```powershell
.\build.ps1
```

The output exe will be created by PyInstaller in the `dist` folder.
