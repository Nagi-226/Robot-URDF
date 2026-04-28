from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CadHandle:
    name: str
    selector: str
    notes: str = ""


@dataclass
class CadFeature:
    name: str
    operation: str
    handle: CadHandle | None = None
    parameters: dict[str, object] = field(default_factory=dict)

    def describe(self) -> str:
        handle_text = f" [{self.handle.name}]" if self.handle else ""
        return f"{self.name}: {self.operation}{handle_text}"
