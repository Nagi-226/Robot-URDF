"""Mesh preprocessing operations for the design-time geometry workbench.

Why this module exists
----------------------
Board/robot models coming out of CAD are usually far too heavy for URDF:
a bracket can carry 50k–500k triangles, ``<collision>`` geometry *must* be
convex, and CAD exports routinely contain duplicated vertices, zero-area
(triangular-degenerate) faces and repeated faces.

This module provides the four operations needed before a model goes into a
URDF, plus a statistics function used to prove they did something:

    mesh_stats()        -> measure (watertight? duplicates? degenerate? euler)
    clean()             -> merge duplicate vertices, drop degenerate/duplicate faces
    decimate()          -> quadric edge-collapse simplification (target face count)
    convex_hull()       -> convex envelope (for <collision>)
    to_collision_mesh() -> convex_hull + decimate in one step

All functions are pure: they take a :class:`~studio_io.mesh_data.MeshData` and
return a **new** one. No UI, no global state, no file I/O (the CLI at the bottom
is a thin wrapper).

Implementation notes
--------------------
* Simplification uses ``fast_simplification`` (MIT, Sven Forstmann's quadric
  edge collapse). The algorithm and parameter semantics were studied from
  MeshLab's ``filter_meshing`` plugin **for ideas only** — MeshLab is GPL v3
  and no code is copied here. See ``docs/MESH_PREPROCESSING.md``.
* Convex hulls use ``trimesh`` + ``scipy`` (BSD-3).
* ``MeshData.indices`` is **flat** (``M * 3``); ``trimesh`` wants ``(M, 3)``.
  That conversion is the single most error-prone step here, so it is asserted
  in :func:`_to_trimesh` and :func:`_from_trimesh` rather than trusted.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import numpy as np
import trimesh

from .mesh_data import MeshData

__all__ = [
    "MeshStats",
    "mesh_stats",
    "clean",
    "decimate",
    "convex_hull",
    "to_collision_mesh",
]

# Faces whose area is below this are treated as degenerate (zero-area).
# 1e-12 in model units is well below any meaningful CAD feature size, and it
# catches the common CAD export failure modes: three collinear points and
# repeated vertex indices inside one face.
_DEGENERATE_AREA_EPS = 1e-12


@dataclass
class MeshStats:
    """Snapshot of the properties that matter before/after preprocessing."""

    vertices: int
    faces: int
    watertight: bool
    winding_consistent: bool
    duplicate_faces: int
    degenerate_faces: int
    euler_number: int

    def as_row(self) -> str:
        return (
            f"v={self.vertices:<7d} f={self.faces:<7d} "
            f"watertight={str(self.watertight):<5s} winding_ok={str(self.winding_consistent):<5s} "
            f"dup_faces={self.duplicate_faces:<5d} degen={self.degenerate_faces:<5d} "
            f"euler={self.euler_number}"
        )


# ---------------------------------------------------------------------------
# MeshData <-> trimesh conversion (the flat-index trap lives here)
# ---------------------------------------------------------------------------


def _face_count(indices: np.ndarray, what: str) -> int:
    """Number of triangles in an index array, whatever shape it arrives in.

    The repository contract is a **2-D ``(M, 3)``** array: ``MeshData.triangle_count``
    is ``len(indices)``, and both ``rendering.py`` and ``urdf_mesh_builder.py``
    treat ``len(indices)`` as the triangle count. A stale comment in
    ``mesh_data.py`` claims "flat: M*3", and some external producers may hand us
    a flat array, so both shapes are accepted here -- but the *output* of every
    operation in this module is always ``(M, 3)``.
    """
    arr = np.asarray(indices)
    if arr.ndim == 2:
        if arr.shape[1] != 3:
            raise ValueError(f"{what}: expected shape (M, 3), got {arr.shape}")
        return int(arr.shape[0])
    if arr.ndim == 1:
        if arr.size % 3 != 0:
            raise ValueError(f"{what}: flat index array length {arr.size} is not a multiple of 3")
        return int(arr.size // 3)
    raise ValueError(f"{what}: index array must be 1-D or 2-D, got {arr.ndim}-D")


def _as_face_matrix(flat_indices: np.ndarray, what: str) -> np.ndarray:
    """Normalise indices to an integer ``(M, 3)`` matrix for trimesh.

    Accepts both the repository's native ``(M, 3)`` shape and a flat ``M*3``
    array. Getting this wrong is the classic failure mode here: passing a flat
    array straight through gives trimesh ``M/3`` faces (mesh silently loses
    two thirds of itself), while treating ``(M, 3)`` as flat gives ``3M`` faces
    (out-of-range indices).
    """
    arr = np.asarray(flat_indices)
    count = _face_count(arr, what)  # validates shape/divisibility
    return arr.reshape(count, 3).astype(np.int64, copy=False)


def _to_trimesh(mesh: MeshData, what: str = "mesh") -> trimesh.Trimesh:
    """Build a trimesh mesh from ``MeshData`` with face-count assertions."""
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError(f"{what}: vertices must be (N, 3), got {vertices.shape}")

    faces = _as_face_matrix(mesh.indices, what)
    expected_faces = _face_count(mesh.indices, what)

    tri = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    # process=False keeps vertex order, so this must hold exactly.
    if len(tri.faces) != expected_faces:
        raise AssertionError(
            f"{what}: face count mismatch after conversion "
            f"(trimesh={len(tri.faces)}, expected={expected_faces}); "
            "the index array was probably reshaped incorrectly"
        )
    return tri


def _bounds_of(vertices: np.ndarray) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if len(vertices) == 0:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    lo = tuple(float(x) for x in np.asarray(vertices, dtype=np.float64).min(axis=0))
    hi = tuple(float(x) for x in np.asarray(vertices, dtype=np.float64).max(axis=0))
    return lo, hi


def _from_trimesh(tri: trimesh.Trimesh, source_format: str, what: str) -> MeshData:
    """Build a fresh ``MeshData`` from a trimesh mesh.

    ``parts`` is deliberately emptied -- see :func:`decimate` for why.
    ``indices`` is emitted as ``(M, 3)`` (the repository contract), never flat.
    """
    vertices = np.ascontiguousarray(np.asarray(tri.vertices, dtype=np.float32))
    faces = np.asarray(tri.faces, dtype=np.uint32)
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise AssertionError(f"{what}: trimesh returned a non-triangular face array {faces.shape}")

    if len(vertices) > 0:
        normals = np.ascontiguousarray(np.asarray(tri.vertex_normals, dtype=np.float32))
    else:
        normals = np.zeros((0, 3), dtype=np.float32)

    lo, hi = _bounds_of(vertices)
    return MeshData(
        vertices=vertices,
        indices=np.ascontiguousarray(faces),
        normals=normals,
        colors=None,
        edge_indices=None,
        parts=[],
        bounds_min=lo,
        bounds_max=hi,
        source_format=source_format,
    )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def mesh_stats(mesh: MeshData) -> MeshStats:
    """Measure a mesh. Cheap enough to call before and after every operation.

    Definition notes (they matter when comparing against MeshLab):

    * ``duplicate_faces`` -- faces sharing the *same vertex set* count as one;
      the surplus is reported. Vertex order inside a face does not matter.
    * ``degenerate_faces`` -- area below ``1e-12``, i.e. three collinear points
      or a face with repeated vertex indices.
    * ``euler_number`` -- ``V - E + F``; for a closed genus-0 mesh it is 2.
    """
    tri = _to_trimesh(mesh, "mesh_stats")

    face_count = int(len(tri.faces))  # authoritative, whatever the input shape was

    unique_mask = tri.unique_faces()
    # NOTE: trimesh returns a *boolean mask* here (length == face count), not an
    # array of unique indices. Using len() on it would always yield face_count
    # and silently report "0 duplicate faces" for any input.
    duplicate_faces = face_count - int(np.count_nonzero(unique_mask))

    areas = np.asarray(tri.area_faces, dtype=np.float64)
    degenerate_faces = int(np.count_nonzero(areas < _DEGENERATE_AREA_EPS))

    return MeshStats(
        vertices=len(np.asarray(mesh.vertices)),
        faces=face_count,
        watertight=bool(tri.is_watertight),
        winding_consistent=bool(tri.is_winding_consistent),
        duplicate_faces=int(duplicate_faces),
        degenerate_faces=degenerate_faces,
        euler_number=int(tri.euler_number),
    )


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------


def clean(mesh: MeshData, *, merge_tol: float = 1e-6) -> tuple[MeshData, dict]:
    """Repair the usual CAD export damage.

    Steps, in order:

    1. **Merge coincident vertices** -- vertices are snapped to a grid of
       ``merge_tol`` and collapsed. Snapping (rather than pairwise distance)
       keeps the operation deterministic and O(n log n); the downside is that
       two vertices closer than ``merge_tol`` but on opposite sides of a grid
       boundary are not merged. That is acceptable for CAD repair, where the
       intent is to kill exact duplicates and float noise.
    2. **Drop degenerate faces** (zero area -- collinear points or repeated
       indices inside one face).
    3. **Drop duplicate faces** (same vertex set, any winding).
    4. **Drop unreferenced vertices** left over by 2 and 3.

    Returns the cleaned mesh and a dict with what was removed, so callers can
    log/report it instead of silently "fixing" geometry.
    """
    if merge_tol <= 0:
        raise ValueError("merge_tol must be > 0")

    tri = _to_trimesh(mesh, "clean")
    vertices = np.asarray(tri.vertices, dtype=np.float64)
    faces = np.asarray(tri.faces, dtype=np.int64)
    report = {
        "vertices_before": int(len(vertices)),
        "faces_before": int(len(faces)),
        "vertices_merged": 0,
        "faces_degenerate_removed": 0,
        "faces_duplicate_removed": 0,
        "vertices_unreferenced_removed": 0,
    }

    # -- 1) merge coincident vertices -------------------------------------
    if len(vertices) > 0:
        grid = np.round(vertices / float(merge_tol)).astype(np.int64)
        _, first_index, inverse = np.unique(
            grid, axis=0, return_index=True, return_inverse=True
        )
        merged_vertices = vertices[first_index]
        new_faces = inverse.reshape(-1)[faces.reshape(-1)].reshape(-1, 3)
        report["vertices_merged"] = int(len(vertices) - len(merged_vertices))
        vertices, faces = merged_vertices, new_faces

    # -- 2) drop degenerate faces -----------------------------------------
    if len(faces) > 0:
        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]
        # area = |cross| / 2 -- avoid sqrt, compare squared magnitudes
        cross = np.cross(v1 - v0, v2 - v0)
        area2 = np.einsum("ij,ij->i", cross, cross)  # (2*area)^2
        keep = area2 > (2.0 * _DEGENERATE_AREA_EPS) ** 2
        report["faces_degenerate_removed"] = int(np.count_nonzero(~keep))
        faces = faces[keep]

    # -- 3) drop duplicate faces (same vertex set, winding-insensitive) ----
    if len(faces) > 0:
        canonical = np.sort(faces, axis=1)
        _, unique_rows = np.unique(canonical, axis=0, return_index=True)
        unique_rows = np.sort(unique_rows)
        report["faces_duplicate_removed"] = int(len(faces) - len(unique_rows))
        faces = faces[unique_rows]

    # -- 4) drop unreferenced vertices ------------------------------------
    if len(faces) > 0:
        used = np.unique(faces.reshape(-1))
        if len(used) != len(vertices):
            remap = np.full(len(vertices), -1, dtype=np.int64)
            remap[used] = np.arange(len(used), dtype=np.int64)
            report["vertices_unreferenced_removed"] = int(len(vertices) - len(used))
            vertices = vertices[used]
            faces = remap[faces]
    else:
        report["vertices_unreferenced_removed"] = int(len(vertices))
        vertices = np.zeros((0, 3), dtype=np.float64)

    cleaned = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    report["vertices_after"] = int(len(cleaned.vertices))
    report["faces_after"] = int(len(cleaned.faces))
    return _from_trimesh(cleaned, mesh.source_format, "clean"), report


# ---------------------------------------------------------------------------
# Decimation
# ---------------------------------------------------------------------------


def decimate(mesh: MeshData, target_faces: int, *, aggressiveness: float = 7.0) -> MeshData:
    """Quadric edge-collapse simplification down to ``target_faces``.

    ``aggressiveness`` maps to ``fast_simplification``'s ``agg`` (0-10, default
    7.0): 0 tries hardest to preserve shape (slower, may fail to reach the
    target), 10 is fastest and roughest. It has no MeshLab counterpart -- see
    ``docs/MESH_PREPROCESSING.md``.

    If ``target_faces >= current face count`` the mesh is returned unchanged
    (a shallow copy), because simplifying "up" is impossible and reporting an
    error would be noise for a batch pipeline.

    ``parts`` is **cleared** on the result. Simplification renumbers vertices
    and triangles freely, so every ``MeshPart.vertex_offset`` /
    ``triangle_offset`` from the input becomes wrong. Keeping them would be
    worse than dropping them: a stale offset does not crash, it silently
    segments the mesh into garbage. If you need per-part meshes afterwards,
    split the mesh into parts *first* and decimate each part separately.

    Raises:
        ValueError: if the mesh has no faces, or ``target_faces < 1``.
    """
    import fast_simplification

    tri = _to_trimesh(mesh, "decimate")
    source_faces = int(len(tri.faces))
    if source_faces == 0:
        raise ValueError("decimate: mesh has no faces")
    if target_faces < 1:
        raise ValueError("decimate: target_faces must be >= 1")

    if target_faces >= source_faces:
        return MeshData(
            vertices=np.array(mesh.vertices, dtype=np.float32, copy=True),
            indices=np.array(
                _as_face_matrix(mesh.indices, "decimate"), dtype=np.uint32, copy=True
            ),
            normals=np.array(mesh.normals, dtype=np.float32, copy=True),
            colors=None,
            edge_indices=None,
            parts=[],
            bounds_min=mesh.bounds_min,
            bounds_max=mesh.bounds_max,
            source_format=mesh.source_format,
        )

    points, faces = fast_simplification.simplify(
        np.asarray(tri.vertices, dtype=np.float64),
        np.asarray(tri.faces, dtype=np.int64),
        target_count=int(target_faces),
        agg=float(aggressiveness),
    )
    reduced = trimesh.Trimesh(vertices=points, faces=faces, process=False)
    return _from_trimesh(reduced, mesh.source_format, "decimate")


# ---------------------------------------------------------------------------
# Convex hull / collision geometry
# ---------------------------------------------------------------------------


def convex_hull(mesh: MeshData) -> MeshData:
    """Return the convex hull (``<collision>`` geometry must be convex).

    ``parts`` is cleared for the same reason as in :func:`decimate`: a hull has
    no relationship to the input's vertex/triangle ordering.

    Raises:
        ValueError: if the mesh has no vertices, or the points are coplanar/
            collinear so that no 3D hull exists (trimesh raises, we re-raise
            with context).
    """
    tri = _to_trimesh(mesh, "convex_hull")
    if len(tri.vertices) < 4:
        raise ValueError("convex_hull: need at least 4 non-coplanar vertices")
    try:
        hull = tri.convex_hull
    except Exception as exc:  # trimesh raises QhullError for degenerate input
        raise ValueError(f"convex_hull failed (degenerate or coplanar input): {exc}") from exc
    return _from_trimesh(hull, mesh.source_format, "convex_hull")


def to_collision_mesh(mesh: MeshData, max_faces: int = 64) -> MeshData:
    """Build URDF ``<collision>`` geometry: convex hull, then decimated.

    URDF collision geometry must be convex **and** small (physics engines pay
    per triangle). 64 faces is a reasonable default for a rigid link.

    Raises:
        ValueError: if ``max_faces < 4`` (a closed hull needs at least a
            tetrahedron) or the hull cannot be built.
    """
    if max_faces < 4:
        raise ValueError("to_collision_mesh: max_faces must be >= 4")
    hull = convex_hull(mesh)
    hull_faces = _face_count(hull.indices, "to_collision_mesh")
    if hull_faces <= max_faces:
        return hull
    return decimate(hull, max_faces)


# ---------------------------------------------------------------------------
# CLI -- lets the capability be verified without launching the UI
# ---------------------------------------------------------------------------


def _print_stats(label: str, stats: MeshStats) -> None:
    print(f"{label:<10s} {stats.as_row()}")


def _main(argv: list[str] | None = None) -> int:
    from .mesh_loader import load_mesh_auto

    parser = argparse.ArgumentParser(
        prog="python -m studio_io.mesh_ops",
        description="Mesh preprocessing (clean / decimate / convex hull) for URDF assets.",
    )
    parser.add_argument("input", help="input mesh (.stl / .glb / .gltf)")
    parser.add_argument("--out", help="write result to this .stl file")
    parser.add_argument("--target-faces", type=int, default=0, help="decimation target face count")
    parser.add_argument("--hull", action="store_true", help="take the convex hull before writing")
    parser.add_argument(
        "--collision",
        type=int,
        metavar="MAX_FACES",
        default=None,
        help="build collision geometry (hull + decimate) with this face budget",
    )
    parser.add_argument("--clean", action="store_true", help="merge/repair before everything else")
    parser.add_argument("--stats", action="store_true", help="print stats (default when nothing else is asked)")
    args = parser.parse_args(argv)

    loaded = load_mesh_auto(args.input)
    if loaded is None:
        print(f"error: unsupported or unreadable mesh: {args.input}", file=sys.stderr)
        return 2

    _print_stats("before", mesh_stats(loaded))
    result = loaded

    if args.clean:
        result, report = clean(result)
        print(
            "clean     "
            f"merged_v={report['vertices_merged']} "
            f"degen_f={report['faces_degenerate_removed']} "
            f"dup_f={report['faces_duplicate_removed']} "
            f"unref_v={report['vertices_unreferenced_removed']}"
        )

    if args.hull:
        result = convex_hull(result)
        print("hull      done")

    if args.collision is not None:
        result = to_collision_mesh(result, max_faces=args.collision)
        print(f"collision hull+decimate -> <= {args.collision} faces")

    if args.target_faces > 0:
        result = decimate(result, args.target_faces)
        print(f"decimate  target={args.target_faces}")

    _print_stats("after", mesh_stats(result))

    if args.out:
        _write_stl(result, args.out)
        print(f"wrote     {args.out}")
    elif not (args.clean or args.hull or args.collision is not None or args.target_faces > 0):
        print("(no operation requested -- pass --clean/--hull/--collision/--target-faces)")
    return 0


def _write_stl(mesh: MeshData, path: str) -> None:
    """Write a MeshData out as binary STL using trimesh."""
    tri = _to_trimesh(mesh, "write_stl")
    tri.export(path)


if __name__ == "__main__":
    raise SystemExit(_main())
