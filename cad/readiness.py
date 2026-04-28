from __future__ import annotations

from dataclasses import dataclass, field

from .pipeline import CadRunwayPipeline
from .writer_registry import WriterRegistry


@dataclass(frozen=True)
class ReadinessItem:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CadReadinessReport:
    items: list[ReadinessItem] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.items.append(ReadinessItem(name=name, passed=passed, detail=detail))

    def is_ready(self) -> bool:
        return all(item.passed for item in self.items)

    def render(self) -> str:
        lines = ["[v0.4.3-dev-readiness]"]
        for item in self.items:
            marker = "PASS" if item.passed else "FAIL"
            suffix = f" - {item.detail}" if item.detail else ""
            lines.append(f"{marker}: {item.name}{suffix}")
        lines.append(f"ready={self.is_ready()}")
        return "\n".join(lines) + "\n"


def check_v043_readiness() -> CadReadinessReport:
    registry = WriterRegistry()
    pipeline = CadRunwayPipeline(writer=registry.get("placeholder"), write_placeholders=True)
    result = pipeline.run()
    report = CadReadinessReport()
    report.add("pipeline report generated", bool(result.report.strip()))
    report.add("scripts generated", bool(result.scripts), f"count={len(result.scripts)}")
    report.add("artifacts planned", bool(result.artifacts), f"count={len(result.artifacts)}")
    report.add("placeholder writer available", "placeholder" in registry.writers)
    report.add("pipeline report contains writer", "writer=" in result.report)
    report.add("payload types captured", bool(result.payload_types), f"count={len(result.payload_types)}")
    report.add("topology generated", bool(result.topology_summary.strip()), result.topology_summary)
    report.add("demo parts available", len(result.scripts) >= 2)
    report.add("written artifacts optional", isinstance(result.written_artifacts, list))
    report.add("edit summary present", bool(result.edit_summary.strip()))
    report.add("artifact descriptors present", bool(result.artifact_descriptors), f"count={len(result.artifact_descriptors)}")
    return report
