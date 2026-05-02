"""Interactive editing bridge connecting 3D picks to CAD handles."""

from __future__ import annotations

from dataclasses import dataclass, field

from cad.handles import CadHandle


@dataclass
class EditAction:
    """One recorded editing action for undo/redo."""

    handle_name: str
    parameter: str
    old_value: float
    new_value: float
    timestamp: float = 0.0


@dataclass
class EditHistory:
    """Undo/redo stack for editing actions."""

    undo_stack: list[EditAction] = field(default_factory=list)
    redo_stack: list[EditAction] = field(default_factory=list)
    max_depth: int = 64

    def push(self, action: EditAction) -> None:
        self.undo_stack.append(action)
        self.redo_stack.clear()
        if len(self.undo_stack) > self.max_depth:
            self.undo_stack.pop(0)

    def undo(self) -> EditAction | None:
        if not self.undo_stack:
            return None
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        return action

    def redo(self) -> EditAction | None:
        if not self.redo_stack:
            return None
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        return action

    @property
    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_stack)


@dataclass
class PickToHandleMapping:
    """Maps a 3D pick result to a CAD feature handle."""

    pick_part_id: str
    handle: CadHandle
    editable_parameters: list[str]

    @classmethod
    def resolve(
        cls,
        pick_part_id: str,
        pick_face_index: int,
        handles: list[CadHandle],
    ) -> "PickToHandleMapping | None":
        """Resolve a face pick to a stable @cad handle.

        Real topology adjacency can refine this later. For the v0.7.0 desktop
        workbench, CAD preview parts resolve deterministically so pick, details,
        and edit history stay synchronized.
        """
        if not handles:
            return None
        part_stem = pick_part_id
        for prefix in ("cad_", "link_"):
            if part_stem.startswith(prefix):
                part_stem = part_stem[len(prefix):]
        part_stem = part_stem.rsplit("_", 1)[0] if "_" in part_stem else part_stem
        for handle in handles:
            if handle.name.startswith(part_stem) or part_stem.startswith(handle.name):
                return cls(pick_part_id=pick_part_id, handle=handle, editable_parameters=[])
        handle = handles[pick_face_index % len(handles)]
        return cls(pick_part_id=pick_part_id, handle=handle, editable_parameters=[])
