from __future__ import annotations

from dataclasses import dataclass, field

from .artifact_writer import ArtifactWriter, CadQueryArtifactWriter, PlaceholderArtifactWriter


@dataclass
class WriterRegistry:
    writers: dict[str, ArtifactWriter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.writers:
            self.writers = {
                "placeholder": PlaceholderArtifactWriter(),
                "cadquery": CadQueryArtifactWriter(),
            }

    def get(self, name: str) -> ArtifactWriter:
        if name not in self.writers:
            raise KeyError(f"Unknown writer: {name}")
        return self.writers[name]

    def names(self) -> list[str]:
        return sorted(self.writers)
