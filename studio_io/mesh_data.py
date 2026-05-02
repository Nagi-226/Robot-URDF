"""Unified mesh data contract — format-agnostic geometry interchange.

Pattern adopted from text-to-cad's canonical mesh data structure.
Every format loader produces this structure so the renderer never
touches format-specific code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class MeshPart:
    """One sub-part within a mesh (e.g. a link in an assembly)."""

    id: str
    name: str
    vertex_offset: int
    vertex_count: int
    triangle_offset: int
    triangle_count: int
    color: tuple[float, float, float] | None = None
    bounds_min: tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_max: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # 16-element flat row-major transform (for URDF assembly posing)
    transform: list[float] | None = None
    link_name: str = ""
    edge_index_offset: int = 0
    edge_index_count: int = 0


@dataclass
class MeshData:
    """Canonical mesh data consumed by renderers.

    All arrays use float32 for vertices/normals/colors and uint32 for indices.
    """

    vertices: np.ndarray  # N×3 float32
    indices: np.ndarray   # M×3 uint32 (flat: M*3)
    normals: np.ndarray   # N×3 float32
    colors: np.ndarray | None = None  # N×3 float32, optional
    edge_indices: np.ndarray | None = None  # E×2 uint32, optional
    parts: list[MeshPart] = field(default_factory=list)
    bounds_min: tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_max: tuple[float, float, float] = (0.0, 0.0, 0.0)
    source_format: str = ""

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        return len(self.indices)

    @property
    def bounds_center(self) -> tuple[float, float, float]:
        return tuple(
            (self.bounds_min[i] + self.bounds_max[i]) / 2.0 for i in range(3)
        )

    @property
    def bounds_extent(self) -> float:
        return max(
            self.bounds_max[i] - self.bounds_min[i] for i in range(3)
        )
