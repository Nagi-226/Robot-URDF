from __future__ import annotations

from dataclasses import dataclass

from .conventions import CadConvention
from .export import ExportArtifact, ExportPlan
from .part import CadPartScript


def _strip_workspace_wrapper(source: str) -> str:
    """Remove leading ``from cad import workspace`` and ``with workspace(…):``
    wrappers so the generator can supply its own clean script skeleton."""
    import re

    stripped = source.strip()
    stripped = re.sub(r"^from\s+cad\s+import\s+workspace\s*\n?", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r'^with\s+workspace\([^)]*\)[^:]*:', "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


@dataclass
class CadScriptGenerator:
    convention: CadConvention = CadConvention()

    def render(self, part: CadPartScript) -> str:
        lines = [
            f"# Auto-generated CAD script for {part.part_name}",
            "from cad import workspace",
            "",
            f'with workspace("{part.part_name}") as w:',
        ]

        source = _strip_workspace_wrapper(part.source)
        if source:
            for line in source.splitlines():
                lines.append(f"    {line}")

        if part.handles:
            lines.append("")
            lines.append("# @cad handles")
            for handle in part.handles:
                lines.append(self.convention.format_handle_comment(handle.name, handle.selector, handle.notes))

        if part.features:
            lines.append("")
            lines.append("# Features")
            for feature in part.features:
                handle_text = f" [{feature.handle.name}]" if feature.handle else ""
                lines.append(f"# - {feature.name}: {feature.operation}{handle_text} {feature.parameters}".rstrip())

        if part.exports:
            lines.append("")
            lines.append("# Exports")
            lines.append(f"# {', '.join(part.exports)}")

        return "\n".join(lines).rstrip() + "\n"

    def plan_exports(self, plan: ExportPlan, base_path: str) -> list[ExportArtifact]:
        """Render every export format in *plan* into artifact metadata."""
        return plan.build_artifacts(base_path)
