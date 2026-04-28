from __future__ import annotations

from dataclasses import dataclass

from .handles import CadFeature, CadHandle
from .part import CadPartScript


@dataclass
class CadEditInstruction:
    handle_name: str
    field: str
    value: object
    reason: str = ""


@dataclass
class CadFeatureEditor:
    def find_handle(self, part: CadPartScript, handle_name: str) -> CadHandle | None:
        for handle in part.handles:
            if handle.name == handle_name:
                return handle
        return None

    def apply(self, part: CadPartScript, instruction: CadEditInstruction) -> bool:
        handle = self.find_handle(part, instruction.handle_name)
        if handle is None:
            return False

        for feature in part.features:
            if feature.handle == handle:
                feature.parameters[instruction.field] = instruction.value
                return True
        return False

    def annotate_handle(self, handle: CadHandle, note: str) -> CadHandle:
        combined = note if not handle.notes else f"{handle.notes}; {note}"
        return CadHandle(name=handle.name, selector=handle.selector, notes=combined)
