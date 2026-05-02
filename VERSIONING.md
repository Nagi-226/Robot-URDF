# Versioning Plan

## Versioning scheme

We use semantic-style product versions for the desktop workbench.

- `v0.0.x` — prototype bootstrap and launchability
- `v0.1.x` — stable desktop shell, layout, and basic robot viewport
- `v0.2.x` — robot model abstraction, URDF pipeline, viewport backend architecture
- `v0.2.1-alpha` to `v0.2.4-alpha` — CAD-layer skeleton and migration runway toward `v0.3.0`
- `v0.3.x` — CAD scripting layer, feature handles, and multi-format export foundation
- `v0.4.x` — CAD runway and UI integration, with stable overview, bridge, and edit/export entry points
- `v0.5.x` — CAD editing workflow maturity, robot/CAD interop, and device-console polish
- `v1.0.0` — integrated, packageable, production-ready workbench

## Current version

Current product version should be treated as `v0.7.0`.

Reasoning:

- The app already has a runnable Windows desktop shell
- URDF import, parsing, and robot model abstractions are in place
- True 3D forward kinematics with Rodrigues rotation and tree-structured DFS solver
- Multi-mesh 3D rendering with per-part model matrices driven by FK world transforms
- GLB/GLTF + STL format loaders via trimesh, plus URDF primitive mesh builder
- 3D picking system with Möller-Trumbore ray-triangle intersection and face/edge/vertex priority
- Joint animation engine with quintic easing and EMA follow
- Interactive editing bridge with undo/redo stack and pick-to-handle mapping
- Camera presets (isometric, front/back, top/bottom, left/right)
- Unified mesh data contract (MeshData/MeshPart) across all format loaders
- Dual-scale viewport system (SceneScale) for CAD vs URDF modes
- Scene lighting preset with key/fill/rim/ambient/hemisphere
- Centralised i18n system with en/zh language switching
- Dynamic joint panel rebuilt from parsed URDF data
- v0.6.7 is implemented as a verified URDF mesh viewport slice.
- v0.6.8-v0.7.0 production paths are now in place: pose tween timer, viewport reset/preset/wireframe/screenshot APIs, CAD sample preview mesh bridge, cone/capsule primitive support, same-scene CAD+Robot rendering, tree/detail/viewport selection sync, undo/redo viewport refresh, viewport state persistence, and screenshot export command path.
- All 103 tests pass, with a PySide6 offscreen MainWindow smoke test verified in the project `.venv`.

## v0.5.x overall goals

The `v0.5.x` line is a stabilization and productization band. The focus is not to add broad new features, but to harden the current workflow so the app feels coherent in windowed use, maximized use, and future packaging use.

### Main goals

- Keep the main workspace visually primary and readable at all sizes
- Keep CAD controls as lightweight command surfaces, not oversized content panels
- Keep telemetry and device-console state aligned through a shared snapshot model
- Keep CAD-to-robot linkage lightweight and inspectable
- Reduce layout debt before broadening functionality again
- Improve documentation and memory so future changes do not reintroduce the same UI problems

### Known problem clusters to finish before `v0.5.3`

1. **Top navigation clarity**
   - The command bar should stay compact and horizontal
   - Menu labels should remain predictable and not crowd the workspace
   - The nav should feel like a control strip, not a second dashboard

2. **Workspace responsiveness**
   - The main center workspace must remain the visual anchor
   - The app should hold up in both windowed and maximized modes
   - Side panels and top bars should not squeeze the viewport into an awkward narrow column

3. **CAD foldout behavior**
   - CAD overview and workflow entries should stay lightweight by default
   - Expanded details should remain optional and non-invasive
   - Foldouts should preserve readability and not consume too much vertical space

4. **Telemetry snapshot quality**
   - Connection state should remain clear and explicit
   - Telemetry health should be derived from the snapshot model, not ad hoc UI text
   - Delta updates should stay useful and not become noisy

5. **Documentation consistency**
   - `README.md` should remain bilingual and current
   - `CLAUDE.md` should reflect the actual release line and the latest guardrails
   - Version notes should match implementation reality, not wishful planning

## Milestones

### v0.0.1
- Initial runnable prototype
- Basic entry point and window launch

### v0.0.2
- Desktop shell scaffolding
- Basic panels and window styling

### v0.0.3
- Joint controls and simple pose presets

### v0.0.4
- URDF import, validation, and basic parsing

### v0.0.5
- Project tree, resource summary, and selection details

### v0.1.0
- Stable desktop shell with robot viewport and URDF workflow
- Package/launch scripts in place

### v0.2.0
- Unified robot model layer
- Backend-agnostic viewport architecture
- 2D skeleton fallback plus 3D placeholder route
- Current working baseline before CAD runway work

### v0.2.1-alpha
- Introduce the `cad/` package boundary
- Define handles, part scripts, and export-plan abstractions
- No heavy backend dependency yet

### v0.2.2-alpha
- Add a minimal CAD part script example
- Add stable handles on sample parts
- Keep everything runnable and easy to inspect

### v0.2.3-alpha
- Add a script-to-artifact planning flow
- Expand export metadata for STEP/STL/DXF/GLB/URDF targets

### v0.2.4-alpha
- Add `@cad` feature-editing conventions and handle-driven mutation scaffolding
- Prepare the jump to full `v0.3.0`

### v0.3.0
- CAD runway reaches a usable first release
- Per-part Python script generation
- Feature handles via `@cad`
- STEP/STL/DXF/GLB/topology/URDF export pipeline

### v0.3.1-dev
- Artifact writer protocol and placeholder writer
- Pipeline CLI with writer selection
- Readiness checks for the runway

### v0.3.2-dev
- Writer registry and writer-name reporting
- More explicit pipeline result metadata
- More stable CLI output for verification

### v0.3.3-dev
- Artifact payload typing and content-type reporting
- Stronger report structure for downstream consumers

### v0.3.4-dev
- Pipeline summary and UI-friendly report shaping
- More stable overview fields for UI consumption

### v0.3.5-dev
- Summary structured rendering and dictionary output
- More robust demo reporting

### v0.3.6-dev
- Edit summary surfaced in pipeline result and summary
- More complete runway report visibility

### v0.3.7-dev
- Readiness and summary alignment tightened
- Stable runway status reporting

### v0.3.8-dev
- UI bridge introduced for safe downstream consumption
- Checklist object introduced for runway gating

### v0.3.9-dev
- CAD overview panel introduced in the main UI
- Overview-only scope established to prevent the CAD panel from becoming a second workspace

### v0.4.0
- CAD runway is visible inside the main desktop app
- Read-only CAD overview is integrated into the UI
- Scope is locked to overview-only, with no control actions
- This version is the stable handoff point before CAD editor actions are introduced

### v0.4.1
- Enrich CAD overview with stable version, readiness, writer, artifact, edit, and topology metadata
- Improve the top-level UI visibility of CAD runway state

### v0.4.2
- Introduce a minimal `@cad` editing demo flow
- Show handle-driven local edits with before/after output
- Keep edits isolated from the main robot workspace

### v0.4.3
- Improve export-chain reporting and artifact metadata
- Differentiate placeholder exports from future backend exports

### v0.4.4
- Add light CAD-to-robot workflow linkage
- Surface upstream CAD state in robot/URDF context panels
- Keep dependencies one-way and avoid coupling the CAD editor into the viewport shell

### v0.4.5
- Consolidate UI/bridge/report behavior
- Finalize v0.4.x stability before entering the next capability band

### v0.5.0
- Establish the horizontal top navigation and compact command surface
- Keep the CAD/workflow surfaces lightweight and non-invasive
- Finalize the shared telemetry/device snapshot model
- Keep the main workspace readable in both windowed and maximized layouts

### v0.5.1 planned
- Refine top navigation spacing, labels, and menu behavior
- Reduce visual compression in the side panels
- Tighten foldout behavior for CAD overview/workflow entries
- Audit the app for layout regressions at narrower window sizes

### v0.5.2 planned
- Improve telemetry presentation and snapshot clarity
- Reduce noisy state transitions and make device status more legible
- Ensure CAD/telemetry commands feel coherent under repeated use
- Finish documentation alignment and remove outdated version wording

### v0.5.3 planned
- Final stabilization pass for the `v0.5.x` line
- Close the remaining UI debt identified in the `v0.5.0` to `v0.5.2` band
- Confirm the app is stable enough for the next capability cycle

### v0.5.4 – v0.5.5
- Incremental stabilization, bug fixes, and telemetry snapshot refinement.

### v0.5.6
- Fix Mesh3DWidget __init__ indentation bug (camera/mouse/GL fields were dead code).
- De-duplicate URDF parsing: shell.py delegates to studio_io/urdf_io.py.
- Fix version declaration and align VERSIONING.md / CLAUDE.md.
- Dynamic joint slider panel: rebuilt from parsed URDF joint data instead of hardcoded 6-DOF default.
- Decouple chain.py bone lengths from JOINT_SPECS: lengths now derived from URDF joint origins.
- Enhance parse_urdf_file to extract joint type, limits, axis, and origin data.

### v0.5.7
- Implement true 3D forward kinematics using URDF joint axis/origin data.
  - Rodrigues rotation formula for axis-angle transforms in 3D.
  - Per-link world transforms accumulated through the joint chain.
  - Added `origin_rpy` and `axis_xyz` fields to `RobotJoint`.
- Support tree-structured URDF kinematics (DFS solver for non-serial chains).
  - `compute_3d_tree_fk()` walks the joint tree from root.
  - Delta_bot test verified (8 links, 7 unique joints).
- Extract bone lengths from URDF joint origins (Euclidean distance from origin).
- `KinematicChain` auto-detects 3D data and tree structure.

### v0.5.8
- Adopted text-to-cad unified mesh data contract pattern.
  - `MeshData` / `MeshPart` dataclasses for format-agnostic geometry.
  - Canonical fields: vertices, indices, normals, colors, edge_indices, bounds, parts.
- STL format loader via trimesh (fallback: numpy-stl).
- Optional CadQuery-to-MeshData bridge (`studio_io/cad_mesh_bridge.py`).
- URDF export writer (`studio_io/urdf_writer.py`) with `model_to_urdf_dict()`.
- `MeshViewportBackend` updated to use unified mesh loader.

### v0.5.9
- Per-part display records (`DisplayRecord` dataclass) for individual link/part tracking.
- Dual-scale system (`SceneScale`) for CAD vs robot viewport modes.
- Scene lighting preset (`LightingPreset`) with key/fill/rim/ambient/hemisphere.
- Per-link mesh positioning via FK transforms in `set_robot_scene()`.
- `MeshViewportBackend._build_display_records()` computes FK transforms per-frame.
- All 87 tests pass; 40 modules import-clean.

### v0.6.0
- Multi-mesh 3D rendering: Mesh3DWidget refactored from single monolithic draw
  to per-part draw calls via `_part_draw_infos` + individual model matrices.
- GLB/GLTF format loader (`load_glb_mesh`) via trimesh scene graph traversal.
- Per-link mesh positioning: FK world transforms drive per-part model matrices.
- URDF primitive mesh generator (`build_primitive_mesh`) for box/cylinder/sphere.

### v0.6.1
- 3D picking system foundation (`studio_io/picking.py`):
  - Möller-Trumbore ray-triangle intersection for face picking.
  - Pre-built `FacePickProxy` from canonical MeshData for GPU-free raycasting.
  - `MeshPicker` class with multi-tier priority (vertex > edge > face).
  - World-space ray from screen coordinates utility.

### v0.6.2
- URDF mesh geometry builder (`studio_io/urdf_mesh_builder.py`):
  - `build_urdf_mesh_data()` resolves URDF visual elements (mesh files + primitives).
  - `pose_urdf_mesh_parts()` applies FK world transforms to per-link mesh parts.
  - Adopted from text-to-cad's buildUrdfMeshGeometry/poseUrdfMeshData.

### v0.6.3
- Joint animation engine (`robot/animation.py`):
  - Quintic easing (smootherstep) for fixed-duration joint tweens.
  - Exponential moving average follow for real-time slider response.
  - Angular wrap-around for continuous/revolute joints.
  - Joint value map comparison within epsilon.

### v0.6.4
- Interactive editing bridge (`cad/edit_bridge.py`):
  - `EditHistory` undo/redo stack (max depth 64).
  - `PickToHandleMapping` resolves 3D face picks to @cad feature handles.
  - `EditAction` records parameter changes for replay.

### v0.6.5
- Camera presets: isometric, front/back, top/bottom, left/right (Mesh3DWidget).
- All 87 tests pass; new modules: 4 in studio_io, 1 in robot, 1 in cad.

### v0.6.6
- Complete edge and vertex picking in `MeshPicker`.
  - Populate `MeshData.edge_indices` in STL/GLB/primitive/URDF mesh paths.
  - Implement ray-to-edge and ray-to-vertex proximity checks.
  - Preserve priority order: vertex > edge > face.
- Selection highlighting in Mesh3DWidget:
  - Add emissive shader feedback for picked faces.
  - Add hover preselection state and click selection state.
  - Keep part-level emissive feedback ready for future per-link mesh records.
- Pick result display in DetailPanel with face, edge, and vertex indices.

### v0.6.7 complete — URDF mesh integration + lighting upgrade
- Wire `build_urdf_mesh_data()` into `MeshViewportBackend`:
  - When a URDF is imported, build visual geometry from `<visual>` elements.
  - Use URDF-derived mesh data in the 3D backend, with `sample_bracket.stl` retained only as a no-model fallback.
  - Handle mesh-file references and primitive geometries; primitives have a pure-numpy fallback for box/cylinder/sphere.
- Integrate `pose_urdf_mesh_parts()` with FK world transforms per frame.
- Upgrade shader to use `LightingPreset` dataclass:
  - Multi-light: key + fill + rim + ambient + hemisphere.
  - Per-light uniforms passed to shader.
- Per-part color from `MeshPart.color` or a link-color palette.

### v0.6.8 complete - Animation wiring + viewport chrome
- `robot/animation.py` is connected to pose presets through a `QTimer` tween path in `WorkspaceShell`.
- Viewport control APIs are exposed and wired from the View menu:
  - Camera preset application through `RobotViewport.set_camera_preset()`.
  - Reset camera through `RobotViewport.reset_camera()`.
  - Wireframe/solid state through `RobotViewport.set_wireframe()`.
- `Mesh3DWidget` now draws projected grid and XYZ axis chrome over the OpenGL viewport.
- Camera state no longer auto-resets on every scene refresh after user camera changes.

### v0.6.9 complete - CAD geometry pipeline
- CAD sample parts produce preview `MeshData` through `cad_part_to_mesh_data()` without executing arbitrary CAD code.
- CAD preview records are injected into `MeshViewportBackend` and render alongside URDF robot records.
- `build_primitive_mesh()` covers `cone` and `capsule` in addition to box/cylinder/sphere.
- Per-part `DisplayRecord` data carries visibility, opacity-ready metadata, colors, transforms, and stable part ids.
- CAD preview meshes participate in the same CPU raycast picking path as URDF meshes.

### v0.7.0 complete — Integrated 3D workspace
- CAD + Robot same-scene rendering is active in `MeshViewportBackend`.
- Selection synchronization is wired across viewport, detail panel, and project/URDF trees.
- CAD pick integration: `PickToHandleMapping` → `@cad` handles → `EditHistory` undo/redo.
- Screenshot export via OpenGL framebuffer (`Mesh3DWidget.export_screenshot()`).
- View menu: camera presets, wireframe/solid toggle, reset view wired to real APIs.
- Viewport camera/display state persistence through `studio_io.viewport_state`.
- All 95 tests pass. CPU raycast picking is the production pick path.

---
## v0.7.x detailed development plan — Polish, Packaging, Product

The v0.7.x band transforms the prototype into a polished, packageable Windows 11 desktop product.
This plan is inspired by the design philosophy skills from Anthropic's **theme-factory** (10 professional
curated themes), **frontend-design** (BOLD aesthetic direction methodology), **brand-guidelines**
(cohesive visual identity system), and **canvas-design** (design philosophy → visual expression pipeline).

Each sub-version targets one thin vertical slice and must keep the app launchable with all tests passing.

### 🎨 v0.7.1 — Design philosophy & theme system

**Design philosophy: "Dark Industrial Precision"**
- Manifesto: A robotic workbench should feel like you could operate it with gloves on.
  Every pixel communicates intent. No decoration without function.
  Dark background is not just "dark mode" — it's the natural state of an industrial
  control surface. Colours are signal, not style.

**Technical deliverables:**
- Extract QSS into a theme factory module (`assets/themes/`):
  - `industrial_dark.qss` — current theme, refined
  - `high_contrast.qss` — accessibility-optimised variant
  - `compact.qss` — maximised workspace density for power users
- Theme switching in View menu (alongside language switching)
- `ThemeManager` class: load, hot-swap, persist preference via `StudioConfig`
- Font stack: Primary monospace for data (Cascadia Code / JetBrains Mono), Secondary sans-serif for labels (Segoe UI)
- Accent colour system adapted from brand-guidelines pattern: 3 accent colours cycling through functional zones
  - Blue accent: robot/model state
  - Green accent: device/connection state
  - Orange accent: CAD/editing state
- All hex colours extracted to named CSS variables in QSS

### 🖌 v0.7.2 — Typography, spacing & visual hierarchy

**Design philosophy applied from frontend-design skill:**
- **Typography**: Distinctive type hierarchy. Headers in semi-bold uppercase tracking.
  Data fields in monospace. Labels in condensed sans-serif. Nothing uses default Qt font sizes.
- **Spatial composition**: Generous negative space around the viewport (the "stage").
  Tight, dense information in side panels (the "instruments"). Clear visual separation
  between chrome and content.
- **Motion**: Staggered panel reveal on first launch. Smooth opacity transitions on
  tab switches. Subtle hover lift on interactive elements.

**Technical deliverables:**
- Unified spacing scale (4px grid): `xs=4, sm=8, md=12, lg=16, xl=24, 2xl=32, 3xl=48`
- Typography scale: `caption=9pt, body=10pt, label=11pt, subtitle=12pt, title=14pt, heading=16pt, hero=20pt`
- All QSS `padding`, `margin`, `border-radius` migrated to spacing-scale variables
- All QSS `font-size` migrated to typography-scale variables
- Panel resize behaviour: smooth QSplitter with minimum size enforcement, no layout jumps
- Status bar styling: subtle gradient, version chip on the right
- Tooltip styling: dark glass-morphism with accent-coloured border
- Scrollbar width, handle colour, and hover states consistent across all scroll areas

### 🧩 v0.7.3 — Icon system & visual chrome

**Technical deliverables:**
- SVG icon set for all toolbar actions (16px/24px/32px):
  - File: open, save, export
  - View: 2d, 3d, reset, zoom-in, zoom-out, wireframe, solid
  - Device: connect, disconnect, send
  - Robot: home-pose, play, pause
- Icon colour inheritance from QSS palette (no hardcoded icon colours)
- TopNav buttons: icon + text or icon-only with tooltip (configurable)
- Viewport overlay: semi-transparent HUD in corners showing:
  - Top-left: model name + joint count
  - Top-right: FPS counter (toggleable)
  - Bottom-left: camera mode indicator (orbit/free)
  - Bottom-right: scale reference
- Splash screen on cold start (simple logo + version, fades out after 1.5s)
- Application icon (.ico) for Windows taskbar and title bar

### 📦 v0.7.4 — PyInstaller packaging pipeline

**Goal: single `RobotURDFStudio.exe` that launches directly on Win11 without Python installed.**

**Technical deliverables:**
- `build.ps1` overhaul:
  - PyInstaller with `--onefile --windowed --icon=assets/icon.ico`
  - Hidden imports manifest for PySide6, trimesh, numpy, CadQuery
  - Data-file collection: `assets/`, `models/`, `i18n.py` translations
  - UPX compression for smaller binary
- `.spec` file committed to repo for reproducible builds
- CI/CD workflow (GitHub Actions) for automated builds on tag push:
  - Windows runner
  - Python 3.12 + dependencies
  - PyInstaller build
  - Upload exe as release artifact
- Post-build smoke test script: launch exe, verify window title, exit
- Version stamp embedded in exe metadata (FileVersion, ProductVersion)
- `dist/` directory with release checklist: exe + README + sample models + LICENSE

### 📦 v0.7.5 — Packaging refinements & self-test

- Handle PyInstaller edge cases:
  - OpenGL DLL bundling (PySide6 OpenGL modules)
  - trimesh binary dependencies (scipy, rtree, shapely — optional, graceful fallback)
  - CadQuery optional: exe works without it, enables CAD features when present
- `--onedir` variant for debugging (easier to inspect bundled files)
- Auto-update check on launch (compare local VERSION with GitHub latest release)
- Crash reporter: unhandled exception → log file + optional telemetry opt-in dialog
- First-launch experience: minimal onboarding wizard (language select + sample model load)
- Sign the exe with self-signed certificate (dev) / code signing cert (release)
- Windows SmartScreen compatibility: proper PE metadata, no false positive triggers

### 🔬 v0.7.6 — Performance & memory optimisation

- `rendering.py` per-frame hot-path audit:
  - Cache per-part mesh data in `_ensure_urdf_mesh()` — extract once, reuse across frames
  - De-duplicate `_build_part_draw_infos()` vertex merging when geometry hasn't changed
  - Replace `np.vstack` + flatten per-frame with pre-built flat VBOs
  - Profile: target <8ms render time for 50K triangle scenes
- `studio_io/picking.py`: add BVH (bounding volume hierarchy) for scenes >10K triangles
  - Fall back to brute-force for small meshes
- Qt widget lifecycle: verify no leaked QObjects after 100+ viewport toggle cycles
- Memory baseline measurement: <200MB private bytes with a loaded URDF + CAD scene
- `QTimer` interval tuning: 16ms default, adaptive to actual frame time

### 🧪 v0.7.7 — Test coverage expansion

- Bring test count from 95 to 130+:
  - `robot/animation.py`: 8 tests (quintic easing boundary cases, EMA convergence, wrap-around)
  - `studio_io/urdf_io.py`: 6 tests (parse valid/invalid URDF, validate, convert to model)
  - `studio_io/urdf_mesh_builder.py`: 4 tests (pose_urdf_mesh_parts, partially overlapping meshes)
  - `studio_io/mesh_loader.py`: 4 tests (load_glb_mesh, load_mesh_auto format detection)
  - `i18n.py`: 4 tests (tr() with/without fmt_args, set_language roundtrip, missing key fallback)
  - `rendering.py`: 6 tests (DisplayRecord, SceneScale, LightingPreset, multi-mesh draw info)
  - `ui/top_nav.py`: 4 tests (menu rebuild on language change, signal emission)
- Integration test: launch MainWindow → import simple_arm.urdf → toggle to 3D → capture screenshot → verify non-black pixels
- Benchmark tests: FK compute time for 6-joint chain <1ms, mesh load time for 50K tri STL <500ms

### 📚 v0.7.8 — Documentation & project polish

- `README.md`: add real screenshot (not just ASCII diagram)
- `CLAUDE.md`: update implementation state to v0.7.x detail level
- `VERSIONING.md`: mark v0.7.1–v0.7.7 items as complete/done
- API reference docstrings for all public functions in `robot/`, `studio_io/`, `rendering.py`
- Architecture Decision Record (ADR) for:
  - Why CPU raycasting over GPU color-ID picking for v0.7.x
  - Why QSS variables over programmatic style setting
  - Why single-file exe over installer
- Changelog (`CHANGELOG.md`) auto-generated from git history since v0.5.0

### 🚀 v0.7.9 — Release candidate

- Full comprehensive-audit pass (12-dimension checklist, all green)
- All 130+ tests passing on clean Windows 11 machine
- Exe build verified: launches, loads URDF, renders 3D, exports screenshot
- README screenshot updated to show v0.7.9 UI
- Git tag `v0.7.9` pushed, GitHub Release created with exe attached
- User acceptance checklist:
  - [ ] Launch from exe (no console window)
  - [ ] Import URDF (simple_arm.urdf, delta_bot.urdf)
  - [ ] Toggle 2D ↔ 3D
  - [ ] Drag joints, apply poses
  - [ ] Pick faces in 3D, see detail panel update
  - [ ] Export screenshot
  - [ ] Switch language (English ↔ 中文)
  - [ ] Switch theme (Industrial Dark / High Contrast / Compact)
  - [ ] Resize window, verify layout stays usable
  - [ ] Close and relaunch, verify viewport state persists

### 🎯 v1.0.0 — Production release
- All v0.7.x items complete
- Code-signed Windows exe
- GitHub Release with tagged version, exe download, changelog
- One-page quick-start guide (PDF in repo)
- Submit to relevant OSS directories (GitHub trending, PyPI if applicable)

### 🛠 v0.7.x execution policy

- Each sub-version MUST keep the app launchable and all existing tests passing
- No speculative features — every PR maps to a specific v0.7.x line item
- Theme/visual changes must be verified by actual screen rendering, not just QSS linting
- Packaging changes must be verified by actually running the produced exe
- Performance changes must be backed by before/after measurements
- Design decisions should reference the specific skill that inspired them (theme-factory, frontend-design, etc.)

## v0.5.x guardrails

### 3D infrastructure already built

| Module | Capability | Status |
|--------|-----------|--------|
| `robot/fk.py` | Rodrigues rotation FK + tree DFS solver | **Complete** |
| `studio_io/mesh_data.py` | MeshData/MeshPart canonical contract | **Complete** |
| `studio_io/mesh_loader.py` | STL + GLB/GLTF + primitives + auto-detect | **Complete** |
| `studio_io/urdf_mesh_builder.py` | URDF visual → MeshData + FK posing | **Complete** |
| `rendering.py` Mesh3DWidget | OpenGL 2.1 multi-mesh rendering + orbit camera + pick feedback | **Complete** |
| `rendering.py` DisplayRecord | Per-part tracking with transforms | **Complete** |
| `rendering.py` SceneScale | CAD vs URDF dual-scale | **Complete** |
| `rendering.py` LightingPreset | 5-light preset dataclass wired to shader uniforms | **Active** |
| `studio_io/picking.py` | Möller-Trumbore ray-triangle + face/edge/vertex picking | **Complete CPU picking** |
| `robot/animation.py` | Quintic easing + EMA follow + angular wrap | **Complete, wired to pose presets** |
| `cad/edit_bridge.py` | Undo/redo + pick-to-handle mapping | **Complete, wired to viewport/detail path** |
| `config.py` | Centralised StudioConfig | **Complete** |
| `i18n.py` | en/zh language switching (140+ keys) | **Complete** |

### Current v0.7.x hardening backlog

The v0.7.0 production path is usable and covered by automated tests. Remaining items are hardening and fidelity work:

1. **URDF package URI resolution** - primitive and local mesh paths work; package URI search roots should be expanded for ROS-style projects.
2. **Material fidelity** - per-part colors are wired, but URDF material parity and alpha blending need viewport QA.
3. **GPU picking acceleration** - CPU raycast picking is the production path; a color-ID GPU pass can be added later for very large scenes.
4. **Part visibility/opacity UI** - `DisplayRecord` has the metadata; tree/detail controls need a dedicated interaction surface.
5. **Windows packaging validation** - the app is launchable in `.venv`; exe packaging remains the next release band.

### Verdict

**v0.7.0 is implemented as a usable integrated 3D workbench slice.**

The OpenGL renderer handles same-scene CAD preview and URDF robot records with FK transforms. The mesh data contract unifies the loader, URDF builder, CAD preview bridge, renderer, and CPU picking path. Selection now flows across viewport, detail panel, and tree surfaces, while CAD picks resolve into edit-history actions. The remaining work is hardening, performance, material fidelity, and packaging rather than core v0.7.0 feature wiring.

## v0.5.x guardrails

- The top navigation must remain a horizontal, non-invasive command surface.
- CAD/workflow controls should not compete with the main workspace for vertical space.
- The workspace must remain resizable and readable at non-maximized window sizes.
- Typography, spacing, and panel sizing must remain legible on full-screen and windowed layouts.
- Prefer layered popovers and menus over stacking extra control panels into the center of the app.
- Validation evidence should come from the real app behavior, not only from static structure or successful imports.
- If a change improves one surface but clearly harms the main viewport, treat it as incomplete until the layout is rebalanced.
- Favor concise labels and grouped menus, but do not remove direct access to common actions.
- Keep product-like naming clear enough for operators without becoming cryptic.

## v0.5.0 closure

- The telemetry/device snapshot chain has been validated with delta updates and interop snapshots.
- The project has entered a stable release band, but the `v0.5.x` line still has explicit refinement targets before `v0.5.3`.
- Avoid broad refactors until the next major capability need is clearly identified.
