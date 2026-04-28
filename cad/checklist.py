from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChecklistItem:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CadRunwayChecklist:
    items: list[ChecklistItem] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.items.append(ChecklistItem(name=name, passed=passed, detail=detail))

    def all_passed(self) -> bool:
        return all(item.passed for item in self.items)

    def count_passed(self) -> int:
        return sum(1 for item in self.items if item.passed)

    def render(self) -> str:
        lines = ["[cad-runway-checklist]"]
        for item in self.items:
            state = "PASS" if item.passed else "FAIL"
            suffix = f" - {item.detail}" if item.detail else ""
            lines.append(f"{state}: {item.name}{suffix}")
        lines.append(f"passed={self.count_passed()}/{len(self.items)}")
        lines.append(f"all_passed={self.all_passed()}")
        return "\n".join(lines) + "\n"
