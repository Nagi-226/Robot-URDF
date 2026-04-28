from __future__ import annotations

import warnings
from dataclasses import dataclass, field

from .export import ExportArtifact, ExportFormat, ExportPlan
from .part import CadPartScript


def _plan_from_part_exports(part: CadPartScript) -> ExportPlan:
    """Build an ExportPlan from a part's declared export strings."""
    plan = ExportPlan(part=part)
    for export_str in part.exports:
        try:
            plan.add(ExportFormat(export_str))
        except ValueError:
            warnings.warn(
                f"Unknown export format '{export_str}' in part '{part.part_name}'. "
                f"Valid formats: {[f.value for f in ExportFormat]}"
            )
    return plan


@dataclass
class CadManifest:
    robot_name: str
    parts: list[CadPartScript] = field(default_factory=list)
    plans: list[ExportPlan] = field(default_factory=list)

    def add_part(self, part: CadPartScript, plan: ExportPlan | None = None) -> None:
        self.parts.append(part)
        if plan is not None:
            self.plans.append(plan)
        elif part.exports:
            self.plans.append(_plan_from_part_exports(part))

    def summary(self) -> str:
        return f"CadManifest(robot={self.robot_name}, parts={len(self.parts)}, plans={len(self.plans)})"

    def build_artifacts(self, base_path: str) -> list[ExportArtifact]:
        artifacts: list[ExportArtifact] = []
        for plan in self.plans:
            artifacts.extend(plan.build_artifacts(base_path))
        return artifacts
