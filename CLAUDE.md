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

- **Current version:** `v0.7.5-dev` (v0.7.0 features complete; v0.7.1-v0.7.5 polish, HUD, packaging, onboarding, signing scaffold, and 3D reliability hardening active)
- **Reason:** v0.7.0 delivers integrated 3D workspace with CAD+Robot same-scene rendering, full selection sync across viewport/detail-panel/trees, CPU raycast picking (face/edge/vertex → @cad handle → undo/redo), OpenGL screenshot export, camera presets/wireframe/reset wired to View menu, and viewport state persistence. The v0.7.1–v0.7.9 band is now active, covering UI polish (theme system, typography hierarchy, icon set), PyInstaller exe packaging, performance optimisation, test coverage expansion, and release candidate preparation. See VERSIONING.md for the full v0.7.x detailed development plan.
- **Reference:** detailed milestone mapping lives in `VERSIONING.md`
- **Reference:** detailed milestone mapping lives in `VERSIONING.md`

## Current implementation state

- Entry point: `main.py`
- Application bootstrap: `app/main.py`
- Main window shell: `app/window.py`
- Top navigation / command surface: `ui/top_nav.py`
- Workspace UI: `ui/shell.py`
- CAD overview panel: `ui/cad_panel.py` (overview-only integration into the main window)
- CAD workflow link panel: `ui/cad_workspace.py`
- Rendering backend protocol: `rendering.py` with pluggable backend architecture
- Robot domain model: `robot_model.py` with RobotModel, JointSpec, ViewState
- Kinematics & chain builder: `robot/` package (2D legacy + 3D FK with axis/origin/tree support)
- I/O layer: `studio_io/` package (URDF parse/write, mesh load/export, CAD bridge)
- Unified mesh data contract: `studio_io/mesh_data.py` (MeshData, MeshPart)
- Format loaders: `studio_io/mesh_loader.py` (STL via trimesh/numpy-stl)
- CAD-to-mesh bridge: `studio_io/cad_mesh_bridge.py` (optional CadQuery integration)
- URDF export writer: `studio_io/urdf_writer.py`
- Build helper: `build.ps1` / `run.ps1` / `start.bat`
- **Launch note:** Win11 上 Windows Store 版 Python 沙箱限制无法启动 GUI（退出码 49），需使用标准安装的 Python312: `C:\Users\FJL03\AppData\Local\Programs\Python\Python312\python.exe`
- PySide6 6.9.2-based desktop UI
- Dark engineering visual language
- URDF import, validation, parsing, and resource summary panel
- Project tree, URDF structure tree, selection details panel, and joint controls
- 2D skeleton viewport fallback with auto-centering
- 3D viewport via Mesh3DWidget with OpenGL shaders, orbit camera, and mesh loading
- Backend-agnostic viewport architecture: RobotViewport is the chrome host, renderers supply the active render frame
- Per-link display records and FK-based mesh positioning for 3D robot visualization
- Dual-scale viewport system (SceneScale for CAD vs URDF modes)
- Scene lighting preset with key/fill/rim/ambient/hemisphere
- Dynamic joint slider panel rebuilt from parsed URDF joint data
- Serial connection scaffold and command send field
- Workflow snapshot bridge for device-console and telemetry state
- CAD layer with full runway stack: handles, part scripts, export plans, topology, script generation, @cad conventions, feature editors, demo pipeline, report/summary, UI bridge, checklist, readiness checks, pipeline CLI, overview-only UI integration, edit demo, artifact descriptors, CAD-to-robot interop snapshot, and workflow link panel
- Horizontal top navigation for grouped commands and layered menus
- Responsive layout safeguards to keep the workspace usable when not maximized

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
- `studio_io/` for serial, CAN, TCP, file import/export, and device adapters (renamed from `io/` to avoid stdlib collision)
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

## v0.5.x execution summary

The `v0.5.x` line is now the stabilization and productization band for the app.

### Completed and active v0.5.x outcomes
- CAD overview remains stable and read-only in the main UI
- CAD edit demo, artifact descriptors, and UI bridge/report layering are in place
- CAD-to-robot workflow linkage is represented through a lightweight interop snapshot
- Device-console and telemetry state are driven through a shared workflow snapshot model
- Snapshot delta updates have been validated for connection and telemetry transitions
- The top navigation is now a horizontal, non-invasive command surface
- The workspace remains launchable and readable in windowed and maximized states
- The current focus is to finish the known UI/layout/documentation issues before `v0.5.3`

### Current `v0.5.1-v0.5.3` working policy
- Keep the top navigation cleaner and more product-like, but preserve fast access to the real commands
- Prefer concise labels, grouped menus, and layered entry points over wider control strips
- Move non-critical explanatory content out of the main workspace when it can live in menus
- Keep foldouts and cards compact, but never so compact that they become harder to use
- Optimize for the “thin slice” approach: each pass should improve clarity without sacrificing operability
- Treat `v0.5.3` as the stabilization checkpoint for layout, naming, and workflow polish in this band

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

## AI coding behavioral guidelines

These guidelines complement the `karpathy-guidelines` plugin (from `andrej-karpathy-skills`). The plugin provides the canonical behavioral rules; this section adapts them to the project's specific engineering context.

### 1. Think before coding

- If a request is ambiguous, surface the ambiguity — don't silently pick an interpretation
- When touching CAD geometry, robot kinematics, or URDF parsing, state assumptions about units, coordinate frames, and joint conventions before writing code
- If a proposed change could affect the app's ability to launch, flag it before implementing

### 2. Simplicity first

- This is already encoded in the Stability-first development strategy — prefer the smallest change that moves the product forward
- No new abstractions without a concrete use case in the current task
- If a change starts to exceed the scope of a thin vertical slice, pause and ask whether it can be split

### 3. Surgical changes

- Don't reformat, restyle, or "improve" code adjacent to the change you're making
- Match the existing style of each file, even if it differs from other files in the project
- Remove imports/variables/functions that YOUR changes made unused, but don't remove pre-existing dead code unless asked
- If you notice an unrelated issue, mention it — don't fix it without asking

### 4. Goal-driven execution

- Before implementing, confirm what "done" looks like with verifiable criteria
- For bugs: reproduce first, then fix — never fix without confirming the bug exists
- For features: define acceptance criteria before writing code
- Keep the app launchable at every intermediate step

## UI direction

The target UI should feel like a professional engineering cockpit:

- Dark, high-contrast panels
- Dense but readable layout
- Dock-like work areas
- Clear status indicators
- Fast access to robot controls, logs, and CAD/model tools
- Win11-friendly sizing and window behavior
- A central viewport that can evolve into a real CAD/robot 3D stage
- Horizontal top command bar with layered menus instead of stacked control strips
- Popover-style command groups that keep the main workspace clear

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

The safest next step after `v0.7.5-dev` is release-grade validation: clean Win11 exe verification, release certificate signing, visual QA for icon/HUD/theme polish, large-scene picking performance, part visibility/opacity UI, and v0.7.6 profiling.
