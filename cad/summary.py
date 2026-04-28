from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import CadPipelineResult


@dataclass(frozen=True)
class SummaryLine:
    label: str
    value: str


@dataclass
class CadRunwaySummary:
    lines: list[SummaryLine] = field(default_factory=list)

    def add(self, label: str, value: str) -> None:
        self.lines.append(SummaryLine(label=label, value=value))

    def render(self) -> str:
        return "\n".join(f"{line.label}: {line.value}" for line in self.lines) + ("\n" if self.lines else "")

    def as_dict(self) -> dict[str, str]:
        return {line.label: line.value for line in self.lines}


def summarize_pipeline_result(result: "CadPipelineResult") -> CadRunwaySummary:
    summary = CadRunwaySummary()
    summary.add("writer", result.writer_name)
    summary.add("parts", str(len(result.scripts)))
    summary.add("artifacts", str(len(result.artifacts)))
    summary.add("written_artifacts", str(len(result.written_artifacts)))
    summary.add("payload_types", str(len(result.payload_types)))
    summary.add("topology", result.topology_summary)
    summary.add("topology_nodes", str(result.topology_node_count))
    summary.add("edit_summary", result.edit_summary)
    summary.add("readiness", "ready" if result.written_artifacts or result.writer_name != "none" else "not_ready")
    summary.add("artifact_descriptor_count", str(len(result.artifact_descriptors)))
    return summary
