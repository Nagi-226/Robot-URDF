from __future__ import annotations

from dataclasses import dataclass, field

from .handles import CadFeature, CadHandle


@dataclass
class CadPartScript:
    part_name: str
    source: str = ""
    handles: list[CadHandle] = field(default_factory=list)
    features: list[CadFeature] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)

    def add_handle(self, name: str, selector: str, notes: str = "") -> CadHandle:
        handle = CadHandle(name=name, selector=selector, notes=notes)
        self.handles.append(handle)
        return handle

    def add_feature(self, name: str, operation: str, handle: CadHandle | None = None, parameters: dict[str, object] | None = None) -> CadFeature:
        feature = CadFeature(name=name, operation=operation, handle=handle, parameters=parameters or {})
        self.features.append(feature)
        return feature

    def set_source(self, source: str) -> None:
        self.source = source

    def add_export(self, export_format: str) -> None:
        if export_format not in self.exports:
            self.exports.append(export_format)

    def summary(self) -> str:
        lines = [f"Part: {self.part_name}"]
        lines.append(f"Handles: {len(self.handles)}")
        lines.append(f"Features: {len(self.features)}")
        lines.append(f"Exports: {', '.join(self.exports) if self.exports else 'none'}")
        return "\n".join(lines)
