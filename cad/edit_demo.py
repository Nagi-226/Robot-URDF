from __future__ import annotations

from dataclasses import dataclass

from .editors import CadEditInstruction, CadFeatureEditor
from .generator import CadScriptGenerator
from .sample_parts import build_wrist_link_part


@dataclass(frozen=True)
class CadEditDemoResult:
    part_name: str
    handle_name: str
    before_summary: str
    after_summary: str
    before_script: str
    after_script: str
    applied: bool


def run_edit_demo() -> CadEditDemoResult:
    generator = CadScriptGenerator()
    editor = CadFeatureEditor()
    part, _ = build_wrist_link_part()
    before_summary = part.summary()
    before_script = generator.render(part)
    applied = editor.apply(
        part,
        CadEditInstruction(
            handle_name="shaft_mount",
            field="radius",
            value=18,
            reason="Widen shaft opening for a revised fit",
        ),
    )
    after_summary = part.summary()
    after_script = generator.render(part)
    return CadEditDemoResult(
        part_name=part.part_name,
        handle_name="shaft_mount",
        before_summary=before_summary,
        after_summary=after_summary,
        before_script=before_script,
        after_script=after_script,
        applied=applied,
    )
