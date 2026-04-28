from __future__ import annotations

from dataclasses import dataclass

from .demo import build_demo_manifest
from .pipeline import CadRunwayPipeline
from .summary import CadRunwaySummary, summarize_pipeline_result
from .writer_registry import WriterRegistry


@dataclass(frozen=True)
class CadUiBridge:
    summary: CadRunwaySummary
    report: str

    @property
    def version(self) -> str:
        return "v0.4.5"

    @property
    def ready(self) -> bool:
        return self.summary.as_dict().get("readiness") == "ready"

    @property
    def readiness(self) -> str:
        return self.summary.as_dict().get("readiness", "not_ready")

    @property
    def writer(self) -> str:
        return self.summary.as_dict().get("writer", "none")

    @property
    def artifact_count(self) -> str:
        return self.summary.as_dict().get("artifacts", "0")

    @property
    def written_artifact_count(self) -> str:
        return self.summary.as_dict().get("written_artifacts", "0")

    @property
    def edit_summary(self) -> str:
        return self.summary.as_dict().get("edit_summary", "n/a")

    @property
    def topology_nodes(self) -> str:
        return self.summary.as_dict().get("topology_nodes", "0")

    @property
    def artifact_descriptor_count(self) -> str:
        return self.summary.as_dict().get("artifact_descriptor_count", "0")

    @property
    def summary_fields(self) -> dict[str, str]:
        return self.summary.as_dict()

    def as_lines(self) -> list[str]:
        ordered_keys = [
            "writer",
            "readiness",
            "artifacts",
            "written_artifacts",
            "edit_summary",
            "topology_nodes",
            "artifact_descriptor_count",
        ]
        fields = self.summary.as_dict()
        lines = [f"version: {self.version}"]
        for key in ordered_keys:
            if key in fields:
                lines.append(f"{key}: {fields[key]}")
        return lines


def build_ui_bridge() -> CadUiBridge:
    manifest = build_demo_manifest()
    pipeline = CadRunwayPipeline(writer=WriterRegistry().get("placeholder"), write_placeholders=True)
    result = pipeline.run(manifest)
    summary = summarize_pipeline_result(result)
    return CadUiBridge(summary=summary, report=result.report)


_bridge_cache: CadUiBridge | None = None


def get_ui_bridge() -> CadUiBridge:
    global _bridge_cache
    if _bridge_cache is None:
        _bridge_cache = build_ui_bridge()
    return _bridge_cache
