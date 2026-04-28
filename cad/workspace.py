from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkspaceShape:
    name: str
    operations: list[str] = field(default_factory=list)

    def edges(self, selector: str) -> "WorkspaceShape":
        self.operations.append(f'edges({selector!r})')
        return self

    def faces(self, selector: str) -> "WorkspaceShape":
        self.operations.append(f'faces({selector!r})')
        return self

    def workplane(self) -> "WorkspaceShape":
        self.operations.append("workplane()")
        return self

    def fillet(self, radius: float) -> "WorkspaceShape":
        self.operations.append(f"fillet({radius})")
        return self

    def circle(self, radius: float) -> "WorkspaceShape":
        self.operations.append(f"circle({radius})")
        return self

    def extrude(self, depth: float) -> "WorkspaceShape":
        self.operations.append(f"extrude({depth})")
        return self

    def rarray(self, x_spacing: float, y_spacing: float, x_count: int, y_count: int) -> "WorkspaceShape":
        self.operations.append(f"rarray({x_spacing}, {y_spacing}, {x_count}, {y_count})")
        return self

    def hole(self, diameter: float) -> "WorkspaceShape":
        self.operations.append(f"hole({diameter})")
        return self


@dataclass
class workspace:
    name: str
    shapes: list[WorkspaceShape] = field(default_factory=list)

    def __enter__(self) -> "workspace":
        self.shapes.clear()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def box(self, width: float, height: float, depth: float) -> WorkspaceShape:
        shape = WorkspaceShape(name="box")
        shape.operations.append(f"box({width}, {height}, {depth})")
        self.shapes.append(shape)
        return shape

    def export(self, part_name: str, formats: list[str]) -> list[str]:
        return [f"{part_name}.{fmt}" for fmt in formats]
