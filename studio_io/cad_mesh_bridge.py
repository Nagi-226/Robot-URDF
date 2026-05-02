"""Optional CadQuery-to-MeshData bridge.

When CadQuery is installed, this module converts CadQuery shapes
to the canonical MeshData format.  Falls back gracefully when
CadQuery is not available.
"""

from __future__ import annotations

import numpy as np

from cad.part import CadPartScript
from studio_io.mesh_data import MeshData, MeshPart
from studio_io.mesh_loader import build_edge_indices, build_primitive_mesh


_HAS_CADQUERY = False
try:
    import cadquery as cq  # noqa: F401
    _HAS_CADQUERY = True
except ImportError:
    pass


def cadquery_available() -> bool:
    """Return True when CadQuery is importable."""
    return _HAS_CADQUERY


def _compute_normals(vertices: np.ndarray, indices: np.ndarray) -> np.ndarray:
    v0 = vertices[indices[:, 0]]
    v1 = vertices[indices[:, 1]]
    v2 = vertices[indices[:, 2]]
    fn = np.cross(v1 - v0, v2 - v1)
    length = np.linalg.norm(fn, axis=1, keepdims=True)
    length[length == 0] = 1.0
    fn = fn / length
    vn = np.zeros_like(vertices)
    for i in range(3):
        np.add.at(vn, indices[:, i], fn)
    vn_len = np.linalg.norm(vn, axis=1, keepdims=True)
    vn_len[vn_len == 0] = 1.0
    return (vn / vn_len).astype(np.float32)


def shape_to_mesh_data(shape, name: str = "cad_part") -> MeshData | None:
    """Convert a CadQuery shape to canonical MeshData.

    Returns None if CadQuery is not available or tessellation fails.
    """
    if not _HAS_CADQUERY:
        return None
    try:
        vertices, indices = shape.tessellate(0.1)  # tolerance in mm
    except Exception:
        return None

    verts = np.array(vertices, dtype=np.float32)
    tris = np.array(indices, dtype=np.uint32).reshape(-1, 3)
    normals = _compute_normals(verts, tris)
    lo = tuple(float(v) for v in verts.min(axis=0))
    hi = tuple(float(v) for v in verts.max(axis=0))

    part = MeshPart(
        id="__cad__",
        name=name,
        vertex_offset=0,
        vertex_count=len(verts),
        triangle_offset=0,
        triangle_count=len(tris),
        bounds_min=lo,
        bounds_max=hi,
    )

    return MeshData(
        vertices=verts,
        indices=tris,
        normals=normals,
        edge_indices=build_edge_indices(tris),
        parts=[part],
        bounds_min=lo,
        bounds_max=hi,
        source_format="cadquery",
    )


def cad_part_to_mesh_data(part: CadPartScript) -> MeshData | None:
    """Best-effort CAD script preview mesh for feature-defined sample parts.

    This is intentionally conservative: it converts known high-level feature
    records to primitive preview geometry without executing arbitrary CAD code.
    CadQuery-backed conversion remains available through shape_to_mesh_data().
    """
    for feature in part.features:
        if feature.operation != "box":
            continue
        params = feature.parameters
        width = float(params.get("width", params.get("x", 1.0)))
        height = float(params.get("height", params.get("y", 1.0)))
        depth = float(params.get("depth", params.get("z", 1.0)))
        mesh = build_primitive_mesh(
            "box",
            {"size": (width, height, depth)},
            name=part.part_name,
        )
        if mesh is not None:
            mesh.source_format = "cad-preview"
            if mesh.parts:
                mesh.parts[0].id = part.part_name
                mesh.parts[0].name = part.part_name
            return mesh
    return None
