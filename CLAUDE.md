# CLAUDE.md

This file is the project memory and working contract for long-context development in this repository.

## Product mission

Build a Windows 11 engineering workbench for robot and CAD workflows. The product should unify:

- CAD generation and incremental editing through Python scripts
- Robot model loading, URDF parsing, and structure visualization
- Joint control and pose presets
- Device/operator workflow tools such as serial, TCP, logs, telemetry, and packaging

The product should feel like a professional engineering application rather than a generic admin shell.

## Unified product architecture

Treat the system as three connected layers:

### 1. CAD generation and incremental editing layer

- Each part can live as its own Python script, ideally CadQuery-based
- AI edits the script directly instead of modifying the original source model file
- The `@cad` handle system marks meaningful geometric features so AI can target holes, faces, fillets, slots, and mounting areas
- The layer should support export to STEP, STL, DXF, GLB, topology data, and URDF
- The CAD layer is the upstream source of geometry truth for later robot assembly and visualization workflows

### 2. Robot structure and visualization layer

- URDF loading and parsing
- Robot links, joints, warnings, and model summaries
- Unified robot model representation shared by UI and future rendering backends
- 2D skeleton viewport as the current fallback rendering path
- Real 3D rendering backend as the next major target
- The viewport should evolve into a stage where CAD-driven geometry and robot assembly can be viewed together

### 3. Operator workflow and device tooling layer

- Joint sliders and pose presets
- Selection details and resource inspection
- Serial/TCP/device console scaffolding
- Logs and telemetry views
- Windows packaging and direct exe delivery

## North-star GUI target

The long-term visual and interaction goal is to approach a polished engineering workspace similar to the reference screenshot shared in the conversation, but aligned to the combined CAD + robot mission:

- A dark, premium desktop shell with a clear app chrome and dock-like layout
- A central model viewport that feels like the primary stage, not a decorative preview
- A right-side joint control panel with sliders, numeric values, presets, copy/reset actions, and immediate model feedback
- A left-side context area for workspace, model, selection, CAD handles, and engineering metadata
- Clear top-level modes for summary, CAD editing, robot exploration, and task-focused workflows
- Dense but readable information architecture suitable for robot, CAD, and device workflows
- High visual polish through spacing, hierarchy, status chips, subtle gradients, and controlled contrast
- Real selection/link/joint/model-state synchronization across tree, details, viewport, and controls
- The eventual implementation should feel like a professional robotic CAD/workbench tool, not a generic form app

## Versioning

Treat the product as evolving from `v0.0.1` upward using a milestone-based version plan.

### Current tracked version

- **Current version:** `v0.5.0`
- **Reason:** the app has a stable desktop shell, URDF import/parsing, unified robot model abstractions, a viewport backend protocol, the CAD runway is visible in the main UI, the CAD editing demo and export/report bridge are in place, CAD-to-robot workflow linkage is established, and telemetry/device snapshot linkage has been validated in the live workflow path
- **Reference:** detailed milestone mapping lives in `VERSIONING.md`

## Current implementation state

- Entry point: `main.py`
- Application bootstrap: `app/main.py`
- Main window shell: `app/window.py`
- Workspace UI: `ui/shell.py`
- CAD overview panel: `ui/cad_panel.py` (overview-only integration into the main window)
- CAD workflow link panel: `ui/cad_workspace.py`
- Rendering backend protocol: `rendering.py` with pluggable backend architecture
- Robot domain model: `robot_model.py` with RobotModel, JointSpec, ViewState
- Kinematics & chain builder: `robot/` package
- Build helper: `build.ps1` / `run.ps1` / `start.bat`
- PySide6-based desktop UI
- Dark engineering visual language
- URDF import, validation, parsing, and resource summary panel
- Project tree, URDF structure tree, selection details panel, and joint controls
- 2D skeleton viewport fallback with auto-centering
- 3D placeholder viewport path via backend abstraction
- Backend-agnostic viewport architecture: RobotViewport is the chrome host, renderers supply the active render frame
- Toggle-ready backend structure for future 2D/3D switching
- Serial connection scaffold and command send field
- Workflow snapshot bridge for device-console and telemetry state
- CAD layer with full runway stack: handles, part scripts, export plans, topology, script generation, @cad conventions, feature editors, demo pipeline, report/summary, UI bridge, checklist, readiness checks, pipeline CLI, overview-only UI integration, edit demo, artifact descriptors, CAD-to-robot interop snapshot, and workflow link panel

## Stability-first development strategy

When extending the app, prefer the safest and most maintainable route:

1. Keep the application runnable at every step
2. Build features in thin vertical slices instead of broad refactors
3. Prefer small modular files over one growing monolith
4. Avoid speculative abstractions until a real use case exists
5. Keep Windows 11 usability and packaging in mind from the beginning

## Recommended architecture

Use a layered structure:

- `app/` for application bootstrap, window composition, and theme setup
- `ui/` for panels, widgets, dialogs, and reusable controls
- `robot/` for URDF parsing, kinematics, joint mapping, and pose logic
- `rendering.py` and future backend modules for viewport rendering
- `cad/` for CadQuery-based script generation, feature handles, export pipelines, and URDF/CAD interop
- `io/` for serial, CAN, TCP, file import/export, and device adapters
- `models/` for robot assets, URDFs, meshes, CAD scripts, and sample data
- `assets/` for icons, themes, and static UI resources
- `tests/` for behavior checks and regression coverage

Keep dependencies pointing inward. UI can depend on robot logic, rendering abstractions, CAD engine, and I/O adapters, but not the other way around.

## Near-term roadmap

1. Preserve the runnable prototype while tightening the main product direction around CAD + robot workflows
2. Keep the viewport abstraction ready for a real 3D renderer
3. Implement the `cad/` package: script generation, feature handles, and export pipeline
4. Add URDF exporter and CAD/robot interop helpers
5. Add `@cad` feature handles for incremental geometry edits without full regeneration
6. Expand the robot model data flow so CAD-generated parts can feed the assembly workflow
7. Add DXF, GLB, and topology data export formats
8. Add an embeddable device console for serial and network links
9. Add telemetry/log viewer and task-oriented panels
10. Prepare Windows packaging and launcher assets
11. Produce a desktop `exe` with a repeatable build script for Win11

## v0.5.0 execution summary

The `v0.5.0` line is now the first version where the CAD runway and the workflow surface are both meaningfully integrated into the product.

### Completed v0.5.0 outcomes
- CAD overview remains stable and read-only in the main UI
- CAD edit demo, artifact descriptors, and UI bridge/report layering are in place
- CAD-to-robot workflow linkage is represented through a lightweight interop snapshot
- Device-console and telemetry state are driven through a shared workflow snapshot model
- Snapshot delta updates have been validated for connection and telemetry transitions
- The product remains stable and launchable while preserving the robot workspace as the primary interactive area

## Development rules

- Keep changes minimal unless the user explicitly asks for a broader refactor
- Prefer preserving existing behavior while adding capabilities
- Use clear names for robot joints, axes, CAD handles, and devices
- Match the existing dark, professional visual style
- When adding new UI, optimize for readability, density, and power-user efficiency
- For embedded workflows, design for real operator use: connection state, error feedback, timestamps, and copyable logs
- For any parsing or file-loading feature, handle missing files and invalid input gracefully
- Keep a build path toward a direct-launch Windows executable on the desktop
- Keep the visual target aligned with the reference-style engineering workspace rather than a generic app shell
- The CAD layer should be treated as a core upstream capability, not a side feature
- The CAD overview in the main UI is overview-only unless a separate editor surface is intentionally introduced later
- If a proposed change blurs the boundary between overview, bridge, readiness, pipeline, and editor responsibilities, stop and review before implementation

## UI direction

The target UI should feel like a professional engineering cockpit:

- Dark, high-contrast panels
- Dense but readable layout
- Dock-like work areas
- Clear status indicators
- Fast access to robot controls, logs, and CAD/model tools
- Win11-friendly sizing and window behavior
- A central viewport that can evolve into a real CAD/robot 3D stage

## Code quality expectations

- Keep code cross-platform where possible, but prioritize Windows 11 first
- Prefer type hints and small, testable functions
- Avoid hard-coded magic numbers when they can be named constants
- Keep paint and rendering code isolated in dedicated widgets
- Use simple state objects for UI-to-model synchronization

## Working memory reminder for future sessions

Before making larger changes, first ask:

- What is the smallest safe change that moves the product forward?
- Does this preserve the app's ability to launch and operate?
- Does this help the eventual Windows desktop product direction?
- Does this reduce future context loss by clarifying structure or intent?

## Next best steps

The safest next step after v0.5.0 is to keep stabilizing the product with small verification-oriented changes only when a real issue or concrete gap appears. Avoid broad refactors until the next major capability need is explicit.
