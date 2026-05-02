"""Format loaders that produce canonical MeshData from disk files.

Each loader is format-specific but returns the same MeshData contract,
adopting text-to-cad's pattern of load-then-render separation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from studio_io.mesh_data import MeshData, MeshPart


def _compute_normals(vertices: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Per-vertex smooth normals from face data."""
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


def build_edge_indices(indices: np.ndarray) -> np.ndarray:
    """Build unique undirected edge pairs from triangle indices."""
    if indices is None or len(indices) == 0:
        return np.zeros((0, 2), dtype=np.uint32)
    faces = np.asarray(indices, dtype=np.uint32)
    if faces.ndim == 1:
        faces = faces.reshape(-1, 3)
    edges: set[tuple[int, int]] = set()
    for a, b, c in faces:
        for left, right in ((a, b), (b, c), (c, a)):
            lo = int(min(left, right))
            hi = int(max(left, right))
            if lo != hi:
                edges.add((lo, hi))
    if not edges:
        return np.zeros((0, 2), dtype=np.uint32)
    return np.array(sorted(edges), dtype=np.uint32)


def _mesh_from_arrays(
    vertices: np.ndarray,
    faces: np.ndarray,
    name: str,
    source_format: str,
) -> MeshData:
    vertices = np.asarray(vertices, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.uint32)
    normals = _compute_normals(vertices, faces)
    edge_indices = build_edge_indices(faces)
    lo = tuple(float(v) for v in vertices.min(axis=0))
    hi = tuple(float(v) for v in vertices.max(axis=0))
    return MeshData(
        vertices=vertices,
        indices=faces,
        normals=normals,
        edge_indices=edge_indices,
        parts=[MeshPart(
            id=name, name=name,
            vertex_offset=0, vertex_count=len(vertices),
            triangle_offset=0, triangle_count=len(faces),
            edge_index_offset=0, edge_index_count=len(edge_indices),
            bounds_min=lo, bounds_max=hi,
        )],
        bounds_min=lo,
        bounds_max=hi,
        source_format=source_format,
    )


def _build_box_mesh(size: tuple[float, float, float], name: str) -> MeshData:
    sx, sy, sz = (float(size[0]) / 2.0, float(size[1]) / 2.0, float(size[2]) / 2.0)
    vertices = np.array([
        [-sx, -sy, -sz], [sx, -sy, -sz], [sx, sy, -sz], [-sx, sy, -sz],
        [-sx, -sy, sz], [sx, -sy, sz], [sx, sy, sz], [-sx, sy, sz],
    ], dtype=np.float32)
    faces = np.array([
        [0, 2, 1], [0, 3, 2],
        [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4],
        [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6],
        [3, 0, 4], [3, 4, 7],
    ], dtype=np.uint32)
    return _mesh_from_arrays(vertices, faces, name, "primitive")


def _build_cylinder_mesh(radius: float, length: float, name: str, segments: int = 32) -> MeshData:
    half = float(length) / 2.0
    radius = float(radius)
    vertices = []
    for z in (-half, half):
        for i in range(segments):
            angle = 2.0 * np.pi * i / segments
            vertices.append((radius * np.cos(angle), radius * np.sin(angle), z))
    bottom_center = len(vertices)
    vertices.append((0.0, 0.0, -half))
    top_center = len(vertices)
    vertices.append((0.0, 0.0, half))

    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j))
        faces.append((i, segments + j, segments + i))
        faces.append((bottom_center, j, i))
        faces.append((top_center, segments + i, segments + j))
    return _mesh_from_arrays(np.array(vertices), np.array(faces), name, "primitive")


def _build_cone_mesh(radius: float, length: float, name: str, segments: int = 32) -> MeshData:
    half = float(length) / 2.0
    radius = float(radius)
    vertices = [(0.0, 0.0, half)]
    for i in range(segments):
        angle = 2.0 * np.pi * i / segments
        vertices.append((radius * np.cos(angle), radius * np.sin(angle), -half))
    base_center = len(vertices)
    vertices.append((0.0, 0.0, -half))

    faces = []
    for i in range(segments):
        j = 1 + (i + 1) % segments
        a = 1 + i
        faces.append((0, a, j))
        faces.append((base_center, j, a))
    return _mesh_from_arrays(np.array(vertices), np.array(faces), name, "primitive")


def _build_sphere_mesh(radius: float, name: str, rings: int = 12, segments: int = 24) -> MeshData:
    radius = float(radius)
    vertices = [(0.0, 0.0, radius)]
    for ring in range(1, rings):
        phi = np.pi * ring / rings
        z = radius * np.cos(phi)
        r = radius * np.sin(phi)
        for i in range(segments):
            theta = 2.0 * np.pi * i / segments
            vertices.append((r * np.cos(theta), r * np.sin(theta), z))
    bottom = len(vertices)
    vertices.append((0.0, 0.0, -radius))

    faces = []
    first_ring = 1
    for i in range(segments):
        faces.append((0, first_ring + i, first_ring + ((i + 1) % segments)))
    for ring in range(rings - 2):
        a = 1 + ring * segments
        b = a + segments
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((a + i, b + i, b + j))
            faces.append((a + i, b + j, a + j))
    last_ring = 1 + (rings - 2) * segments
    for i in range(segments):
        faces.append((bottom, last_ring + ((i + 1) % segments), last_ring + i))
    return _mesh_from_arrays(np.array(vertices), np.array(faces), name, "primitive")


def _build_capsule_mesh(radius: float, length: float, name: str) -> MeshData:
    cylinder = _build_cylinder_mesh(radius, max(float(length) - 2.0 * float(radius), 0.001), name)
    sphere_top = _build_sphere_mesh(radius, f"{name}_top")
    sphere_bottom = _build_sphere_mesh(radius, f"{name}_bottom")
    z_offset = max(float(length) / 2.0 - float(radius), 0.0)
    sphere_top.vertices[:, 2] += z_offset
    sphere_bottom.vertices[:, 2] -= z_offset

    vertices = []
    faces = []
    offset = 0
    for mesh in (cylinder, sphere_top, sphere_bottom):
        vertices.append(mesh.vertices)
        faces.append(mesh.indices + offset)
        offset += len(mesh.vertices)
    return _mesh_from_arrays(np.vstack(vertices), np.vstack(faces), name, "primitive")


def _build_primitive_mesh_fallback(
    primitive_type: str,
    params: dict,
    name: str,
) -> MeshData | None:
    if primitive_type == "box":
        return _build_box_mesh(params.get("size", (1.0, 1.0, 1.0)), name)
    if primitive_type == "cylinder":
        return _build_cylinder_mesh(
            float(params.get("radius", 0.5)),
            float(params.get("length", 1.0)),
            name,
        )
    if primitive_type == "sphere":
        return _build_sphere_mesh(float(params.get("radius", 0.5)), name)
    if primitive_type == "cone":
        return _build_cone_mesh(
            float(params.get("radius", 0.5)),
            float(params.get("length", 1.0)),
            name,
        )
    if primitive_type == "capsule":
        return _build_capsule_mesh(
            float(params.get("radius", 0.5)),
            float(params.get("length", 1.0)),
            name,
        )
    return None


def load_stl_mesh(path: str | Path) -> MeshData | None:
    """Load a binary or ASCII STL file into canonical MeshData.

    Tries trimesh first, falls back to numpy-stl.
    """
    path = Path(path)
    if not path.is_file():
        return None

    vertices = None
    indices_list = None

    # Try trimesh
    try:
        import trimesh
        m = trimesh.load(str(path))
        if isinstance(m, trimesh.Scene):
            geoms = list(m.geometry.values())
            m = trimesh.util.concatenate(geoms) if geoms else None
        if m is not None and len(m.vertices) > 0 and len(m.faces) > 0:
            vertices = np.array(m.vertices, dtype=np.float32)
            indices_list = np.array(m.faces, dtype=np.uint32)
    except Exception:
        pass

    # Fallback: numpy-stl
    if vertices is None:
        try:
            from stl.mesh import Mesh as StlMesh
            stl = StlMesh.from_file(str(path))
            raw = np.array(stl.vectors, dtype=np.float32)  # F×3×3
            F = raw.shape[0]
            vertices = raw.reshape(-1, 3)
            indices_list = np.arange(F * 3, dtype=np.uint32).reshape(F, 3)
        except Exception:
            return None

    if vertices is None or indices_list is None or len(vertices) == 0:
        return None

    normals = _compute_normals(vertices, indices_list)
    edge_indices = build_edge_indices(indices_list)
    lo = tuple(float(v) for v in vertices.min(axis=0))
    hi = tuple(float(v) for v in vertices.max(axis=0))

    part = MeshPart(
        id="__model__",
        name=path.stem,
        vertex_offset=0,
        vertex_count=len(vertices),
        triangle_offset=0,
        triangle_count=len(indices_list),
        edge_index_offset=0,
        edge_index_count=len(edge_indices),
        bounds_min=lo,
        bounds_max=hi,
    )

    return MeshData(
        vertices=vertices,
        indices=indices_list,
        normals=normals,
        edge_indices=edge_indices,
        parts=[part],
        bounds_min=lo,
        bounds_max=hi,
        source_format="stl",
    )


def load_glb_mesh(path: str | Path) -> MeshData | None:
    """Load a GLB/GLTF file into canonical MeshData.

    Uses trimesh which supports GLTF scene graphs natively.
    Each scene node becomes a MeshPart with its world transform.
    """
    path = Path(path)
    if not path.is_file():
        return None

    try:
        import trimesh
    except ImportError:
        return None

    try:
        scene = trimesh.load(str(path))
        if not isinstance(scene, trimesh.Scene):
            # Single mesh — treat as monolithic
            if hasattr(scene, 'vertices') and len(scene.vertices) > 0:
                verts = np.array(scene.vertices, dtype=np.float32)
                faces = np.array(scene.faces, dtype=np.uint32)
                normals = _compute_normals(verts, faces)
                edge_indices = build_edge_indices(faces)
                lo = tuple(float(v) for v in verts.min(axis=0))
                hi = tuple(float(v) for v in verts.max(axis=0))
                return MeshData(
                    vertices=verts, indices=faces, normals=normals,
                    parts=[MeshPart(
                        id="__model__", name=path.stem,
                        vertex_offset=0, vertex_count=len(verts),
                        triangle_offset=0, triangle_count=len(faces),
                        edge_index_offset=0, edge_index_count=len(edge_indices),
                        bounds_min=lo, bounds_max=hi,
                    )],
                    edge_indices=edge_indices,
                    bounds_min=lo, bounds_max=hi, source_format="glb",
                )
            return None

        # Scene with multiple geometries
        all_verts = []
        all_faces = []
        all_normals = []
        parts = []
        v_offset = 0
        t_offset = 0

        for name, geometry in scene.geometry.items():
            if not hasattr(geometry, 'vertices') or len(geometry.vertices) == 0:
                continue
            verts = np.array(geometry.vertices, dtype=np.float32)
            faces = np.array(geometry.faces, dtype=np.uint32)
            all_verts.append(verts)
            all_faces.append(faces + v_offset)

            lo = tuple(float(v) for v in verts.min(axis=0))
            hi = tuple(float(v) for v in verts.max(axis=0))
            parts.append(MeshPart(
                id=name, name=name,
                vertex_offset=v_offset, vertex_count=len(verts),
                triangle_offset=t_offset, triangle_count=len(faces),
                bounds_min=lo, bounds_max=hi,
            ))
            v_offset += len(verts)
            t_offset += len(faces)

        if not all_verts:
            return None

        merged_verts = np.vstack(all_verts).astype(np.float32)
        merged_faces = np.vstack(all_faces).astype(np.uint32)
        merged_normals = _compute_normals(merged_verts, merged_faces)
        edge_indices = build_edge_indices(merged_faces)
        for part in parts:
            start = part.vertex_offset
            end = start + part.vertex_count
            part_edges = [
                i for i, (a, b) in enumerate(edge_indices)
                if start <= int(a) < end and start <= int(b) < end
            ]
            if part_edges:
                part.edge_index_offset = min(part_edges)
                part.edge_index_count = len(part_edges)

        lo = tuple(float(v) for v in merged_verts.min(axis=0))
        hi = tuple(float(v) for v in merged_verts.max(axis=0))

        return MeshData(
            vertices=merged_verts, indices=merged_faces,
            normals=merged_normals, edge_indices=edge_indices, parts=parts,
            bounds_min=lo, bounds_max=hi, source_format="glb",
        )
    except Exception:
        return None


def build_primitive_mesh(
    primitive_type: str,
    params: dict,
    name: str = "primitive",
) -> MeshData | None:
    """Generate MeshData for URDF primitive geometries.

    Supports: box, cylinder, sphere.
    This allows visualizing URDF models that use primitives (no mesh files).
    """
    try:
        import trimesh
    except ImportError:
        return _build_primitive_mesh_fallback(primitive_type, params, name)

    try:
        if primitive_type == "box":
            size = params.get("size", (1.0, 1.0, 1.0))
            geom = trimesh.creation.box(extents=size)
        elif primitive_type == "cylinder":
            radius = float(params.get("radius", 0.5))
            length = float(params.get("length", 1.0))
            geom = trimesh.creation.cylinder(radius=radius, height=length)
        elif primitive_type == "sphere":
            radius = float(params.get("radius", 0.5))
            geom = trimesh.creation.icosphere(radius=radius)
        elif primitive_type == "cone":
            radius = float(params.get("radius", 0.5))
            length = float(params.get("length", 1.0))
            geom = trimesh.creation.cone(radius=radius, height=length)
        elif primitive_type == "capsule":
            radius = float(params.get("radius", 0.5))
            length = float(params.get("length", 1.0))
            geom = trimesh.creation.capsule(radius=radius, height=length)
        else:
            return None

        verts = np.array(geom.vertices, dtype=np.float32)
        faces = np.array(geom.faces, dtype=np.uint32)
        normals = _compute_normals(verts, faces)
        edge_indices = build_edge_indices(faces)
        lo = tuple(float(v) for v in verts.min(axis=0))
        hi = tuple(float(v) for v in verts.max(axis=0))

        return MeshData(
            vertices=verts, indices=faces, normals=normals,
            edge_indices=edge_indices,
            parts=[MeshPart(
                id=name, name=name,
                vertex_offset=0, vertex_count=len(verts),
                triangle_offset=0, triangle_count=len(faces),
                edge_index_offset=0, edge_index_count=len(edge_indices),
                bounds_min=lo, bounds_max=hi,
            )],
            bounds_min=lo, bounds_max=hi, source_format="primitive",
        )
    except Exception:
        return _build_primitive_mesh_fallback(primitive_type, params, name)


def load_mesh_auto(path: str | Path) -> MeshData | None:
    """Auto-detect format and load."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".stl",):
        return load_stl_mesh(path)
    if suffix in (".glb", ".gltf"):
        return load_glb_mesh(path)
    return None
