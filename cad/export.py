from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .part import CadPartScript


class ExportFormat(str, Enum):
    STEP = "step"
    STL = "stl"
    DXF = "dxf"
    GLB = "glb"
    TOPOLOGY = "topology"
    URDF = "urdf"


@dataclass(frozen=True)
class ExportArtifact:
    part_name: str
    format: ExportFormat
    path: str


@dataclass
class ExportPlan:
    part: CadPartScript
    formats: list[ExportFormat] = field(default_factory=list)

    def add(self, export_format: ExportFormat) -> None:
        if export_format not in self.formats:
            self.formats.append(export_format)

    def build_artifacts(self, base_path: str) -> list[ExportArtifact]:
        artifacts: list[ExportArtifact] = []
        for export_format in self.formats:
            artifacts.append(
                ExportArtifact(
                    part_name=self.part.part_name,
                    format=export_format,
                    path=f"{base_path}/{self.part.part_name}.{export_format.value}",
                )
            )
        return artifacts
