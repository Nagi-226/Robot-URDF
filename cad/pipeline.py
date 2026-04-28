from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .artifact_writer import ArtifactDescriptor, ArtifactWriter, ArtifactWriteResult, PlaceholderArtifactWriter
from .demo import build_demo_manifest
from .editors import CadEditInstruction, CadFeatureEditor
from .generator import CadScriptGenerator
from .manifest import CadManifest
from .report import CadRunwayReport
from .topology import TopologyGraph


@dataclass(frozen=True)
class CadPipelineResult:
    report: str
    scripts: dict[str, str]
    artifacts: list[str]
    topology_summary: str
    written_artifacts: list[str]
    writer_name: str
    payload_types: dict[str, str]
    edit_summary: str
    topology_node_count: int
    artifact_descriptors: list[ArtifactDescriptor]


@dataclass
class CadRunwayPipeline:
    export_base_path: str = "exports"
    output_root: Path = Path(".")
    write_placeholders: bool = False
    writer: ArtifactWriter | None = None

    def run(self, manifest: CadManifest | None = None) -> CadPipelineResult:
        manifest = manifest or build_demo_manifest()
        generator = CadScriptGenerator()
        editor = CadFeatureEditor()
        graph = TopologyGraph(robot_name=manifest.robot_name)

        scripts: dict[str, str] = {}
        for part in manifest.parts:
            graph.from_part(part)
            scripts[part.part_name] = generator.render(part)

        export_artifacts = manifest.build_artifacts(self.export_base_path)
        artifacts = [artifact.path for artifact in export_artifacts]
        written_results: list[ArtifactWriteResult] = []
        payload_types: dict[str, str] = {}
        artifact_descriptors: list[ArtifactDescriptor] = []
        writer = self.writer or (PlaceholderArtifactWriter() if self.write_placeholders else None)
        writer_name = writer.name if writer is not None else "none"
        parts_by_name = {part.part_name: part for part in manifest.parts}
        for artifact in export_artifacts:
            part = parts_by_name.get(artifact.part_name)
            if part is None:
                continue
            descriptor = ArtifactDescriptor(
                part_name=artifact.part_name,
                format=artifact.format.value,
                path=artifact.path,
                writer=writer_name,
                content_type="unknown",
                placeholder=writer_name == "placeholder",
            )
            if writer is not None:
                if isinstance(writer, PlaceholderArtifactWriter):
                    payload = writer.payload_for(artifact, part)
                    payload_types[artifact.path] = payload.content_type
                    descriptor = ArtifactDescriptor(
                        part_name=artifact.part_name,
                        format=artifact.format.value,
                        path=artifact.path,
                        writer=writer_name,
                        content_type=payload.content_type,
                        placeholder=True,
                    )
                else:
                    descriptor = ArtifactDescriptor(
                        part_name=artifact.part_name,
                        format=artifact.format.value,
                        path=artifact.path,
                        writer=writer_name,
                        content_type="application/octet-stream",
                        placeholder=False,
                    )
                written_results.append(writer.write(artifact, part, self.output_root))
            artifact_descriptors.append(descriptor)

        edit_summary = "No editable part found"
        if manifest.parts:
            target = manifest.parts[0]
            if target.handles:
                editor.apply(
                    target,
                    CadEditInstruction(
                        handle_name=target.handles[0].name,
                        field="demo_value",
                        value="edited",
                        reason="Pipeline edit smoke test",
                    ),
                )
                edit_summary = target.summary()

        report = CadRunwayReport()
        report.add_section("pipeline", f"robot={manifest.robot_name}", f"parts={len(manifest.parts)}", f"artifacts={len(artifacts)}", f"writer={writer_name}")
        report.add_section("topology", graph.summary())
        report.add_section("artifacts", *artifacts)
        report.add_section("artifact-descriptors", *[f"{d.path} | {d.format} | {d.writer} | {d.content_type} | placeholder={d.placeholder}" for d in artifact_descriptors])
        if payload_types:
            report.add_section("payload-types", *[f"{path} -> {ctype}" for path, ctype in payload_types.items()])
        if written_results:
            report.add_section("written-artifacts", *[str(result.path) for result in written_results])
        report.add_section("edit-smoke-test", edit_summary)
        for part_name, script in scripts.items():
            report.add_section(f"script:{part_name}", script.strip())

        return CadPipelineResult(
            report=report.render(),
            scripts=scripts,
            artifacts=artifacts,
            topology_summary=graph.summary(),
            written_artifacts=[str(result.path) for result in written_results],
            writer_name=writer_name,
            payload_types=payload_types,
            edit_summary=edit_summary,
            topology_node_count=len(graph.nodes),
            artifact_descriptors=artifact_descriptors,
        )
