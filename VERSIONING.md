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

Current product version should be treated as `v0.5.0`.

Reasoning:

- The app already has a runnable Windows desktop shell
- URDF import, parsing, and robot model abstractions are in place
- The viewport backend architecture is stable
- The CAD runway is integrated into the main UI as a read-only overview panel
- The CAD UI bridge surfaces stable overview fields for version, readiness, writer, artifact count, written artifact count, edit summary, topology nodes, and artifact descriptor count
- The project now has a CAD-to-robot interop snapshot layer, and the workflow surface now shows telemetry and device-console state, with the snapshot linkage validated in basic command/connection transitions
- The product remains stable and launchable while preserving the robot workspace as the primary interactive area

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
- CAD editing workflow maturity
- Robot/CAD interop polish
- Device-console and telemetry refinement
- Interop snapshot validation in UI and workflow terms
- Current release line is considered complete and stable enough to begin the next planning cycle

### v1.0.0 planned
- Production-ready Windows desktop release
- Repeatable build, packaging, and direct exe delivery

## v0.4.x execution guardrails

- The CAD overview in the main UI stays overview-only until a dedicated editor surface is intentionally introduced.
- Pipeline, summary, readiness, and bridge responsibilities stay separate.
- Any new CAD editing surface must be a separate UI area, not an expansion of the overview panel.
- Robot workspace remains the primary interactive area until the CAD editor is explicitly promoted.
- If a proposed change blurs these boundaries, stop and review before implementation.

## v0.5.0 prerequisite guardrails

- Do not declare v0.5.0 complete until the device-console and telemetry refinements are implemented and validated.
- The CAD-to-robot interop layer should remain a lightweight snapshot/adapter until the workflow proves stable.
- UI changes in this phase should prefer incremental surface additions over refactors of the workspace shell.
- If workflow signals or connectivity state are surfaced, ensure they are derived from a consistent snapshot model rather than ad hoc UI state.
- Telemetry updates must preserve connection state clarity and not silently rewrite the robot workspace into a control application.
- Validation evidence should come from the real app behavior, not only from static structure or successful imports.

## v0.5.0-pre closure

- The telemetry/device snapshot chain has been validated with delta updates and interop snapshots.
- The project has entered a stable closed state for this release line.
- Avoid broad refactors until the next major capability need is clearly identified.
