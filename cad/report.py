from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReportSection:
    title: str
    lines: list[str] = field(default_factory=list)

    def render(self) -> str:
        body = "\n".join(self.lines).rstrip()
        return f"[{self.title}]\n{body}" if body else f"[{self.title}]"


@dataclass
class CadRunwayReport:
    sections: list[ReportSection] = field(default_factory=list)

    def add_section(self, title: str, *lines: str) -> None:
        normalized_lines: list[str] = []
        for line in lines:
            normalized_lines.extend(line.splitlines() if line else [""])
        self.sections.append(ReportSection(title=title, lines=normalized_lines))

    def extend(self, sections: list[ReportSection]) -> None:
        self.sections.extend(sections)

    def section_titles(self) -> list[str]:
        return [section.title for section in self.sections]

    def render(self) -> str:
        return "\n\n".join(section.render() for section in self.sections).rstrip() + "\n"
