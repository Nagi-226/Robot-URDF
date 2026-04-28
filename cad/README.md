# cad package

This package is the CAD runway for Robot URDF Studio.

## Purpose

The CAD layer is intended to support:

- one Python script per part
- stable geometry feature handles via `@cad`
- incremental edits without regenerating the whole model
- export planning for STEP, STL, DXF, GLB, topology data, and URDF
- future integration with robot assembly and viewport workflows

## Current stage

This package is intentionally small and skeletal while the project moves through the `v0.2.1-alpha` to `v0.4.0` runway.

The current goal is to establish a stable architecture before wiring in a heavy CAD backend.

## Current sample parts

- `wrist_link`
- `base_mount`

## Current supporting abstractions

- `CadHandle` and `CadFeature`
- `CadPartScript`
- `CadScriptGenerator`
- `CadConvention`
- `CadEditInstruction` and `CadFeatureEditor`
- `ExportPlan` and `ExportArtifact`
- `CadManifest`
- `TopologyGraph`
- `CadRunwayReport`
- `CadRunwayPipeline`
- `WriterRegistry`
- `ArtifactWriter`
- `PlaceholderArtifactWriter`
- `CadQueryArtifactWriter`
- `ArtifactPayload`
- `CadRunwaySummary`
- `CadUiBridge`
- `CadRunwayChecklist`
- `cad.demo` and `cad.demo_cli`
- `cad.pipeline_cli`
- `cad.readiness_cli`

## Current runway rule

Prefer small, inspectable edits.
If a change creates a split in philosophy or model ownership, report it early before both product lines drift apart.

## Scope rule

The CAD overview in the main UI is overview-only.
It should not become a control surface or second workspace.

## Demo entry

Run the CAD runway demo with:

```bash
python -m cad.demo_cli
```

The demo prints a manifest summary, topology summary, pipeline summary, generated scripts, a pipeline edit summary, and a before/after feature edit report.

Run the pipeline demo and optionally write placeholder artifacts with:

```bash
python -m cad.pipeline_cli --write --writer placeholder
```

Run the readiness check with:

```bash
python -m cad.readiness_cli
```
