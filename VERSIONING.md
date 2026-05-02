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

### v0.7.0 complete - Integrated 3D workspace
- CAD + Robot same-scene rendering is active in `MeshViewportBackend`.
- Selection synchronization is wired across viewport, detail panel, and project/URDF trees:
  - 3D picks update the detail panel.
  - Tree selections call into the 3D widget highlight hook.
  - 3D picks try to select the matching tree item when a corresponding link/part exists.
- CAD pick integration is active:
  - `PickToHandleMapping` resolves CAD preview face picks to `@cad` handles.
  - Picked CAD handles are recorded through `EditHistory`.
  - Undo/redo menu actions refresh the viewport after edit stack changes.
- Screenshot/export has a real OpenGL framebuffer path through `Mesh3DWidget.export_screenshot()`.
- Top navigation Export State routes to viewport screenshot export.
- Reset View, camera presets, and wireframe/solid mode route to real viewport APIs.
- Viewport camera/display state persists through `studio_io.viewport_state`.
- Picking production note: v0.7.0 ships the deterministic CPU raycast path for face/edge/vertex/CAD-handle picking; a dedicated GPU color-ID pass remains an optional acceleration layer, not a blocker for the v0.7.0 workbench.

### v1.0.0 planned
- Production-ready Windows desktop release
- Repeatable build, packaging, and direct exe delivery

## 3D readiness assessment (v0.6.5 baseline)

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
