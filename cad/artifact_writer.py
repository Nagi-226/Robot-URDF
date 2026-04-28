from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from xml.sax.saxutils import escape as xml_escape

from .export import ExportArtifact, ExportFormat
from .part import CadPartScript
from .topology import TopologyGraph


@dataclass(frozen=True)
class ArtifactWriteResult:
    path: Path
    written: bool
    note: str = ""


class ArtifactWriter(Protocol):
    name: str

    def write(self, artifact: ExportArtifact, part: CadPartScript, output_root: Path) -> ArtifactWriteResult:
        ...


@dataclass(frozen=True)
class ArtifactPayload:
    artifact: ExportArtifact
    content: str
    content_type: str


@dataclass(frozen=True)
class ArtifactDescriptor:
    part_name: str
    format: str
    path: str
    writer: str
    content_type: str
    placeholder: bool


@dataclass
class PlaceholderArtifactWriter:
    name: str = "placeholder"

    def write(self, artifact: ExportArtifact, part: CadPartScript, output_root: Path) -> ArtifactWriteResult:
        target = output_root / Path(artifact.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self.payload_for(artifact, part)
        target.write_text(payload.content, encoding="utf-8")
        return ArtifactWriteResult(path=target, written=True, note=f"placeholder artifact ({payload.content_type})")

    def payload_for(self, artifact: ExportArtifact, part: CadPartScript) -> ArtifactPayload:
        if artifact.format == ExportFormat.TOPOLOGY:
            graph = TopologyGraph(robot_name=part.part_name)
            graph.from_part(part)
            content = json.dumps(
                {
                    "part": part.part_name,
                    "nodes": [node.__dict__ for node in graph.nodes],
                    "format": artifact.format.value,
                },
                indent=2,
            )
            return ArtifactPayload(artifact=artifact, content=content, content_type="application/json")
        if artifact.format == ExportFormat.URDF:
            safe_name = xml_escape(part.part_name)
            content = f'<robot name="{safe_name}">\n  <link name="{safe_name}" />\n</robot>\n'
            return ArtifactPayload(artifact=artifact, content=content, content_type="application/xml")
        content = f"Placeholder {artifact.format.value.upper()} artifact for {part.part_name}\n"
        return ArtifactPayload(artifact=artifact, content=content, content_type="text/plain")


@dataclass
class CadQueryArtifactWriter:
    name: str = "cadquery"

    def write(self, artifact: ExportArtifact, part: CadPartScript, output_root: Path) -> ArtifactWriteResult:
        target = output_root / Path(artifact.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"CadQuery export placeholder for {part.part_name} -> {artifact.format.value}\n",
            encoding="utf-8",
        )
        return ArtifactWriteResult(path=target, written=True, note="cadquery writer placeholder")
