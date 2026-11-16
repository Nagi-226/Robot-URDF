"""Tests for :mod:`studio_io.mesh_ops`.

These are behavioural tests, not smoke tests: every assertion is meant to be
able to fail. Where a fixture is supposed to be "dirty", the test first proves
it is dirty (otherwise a no-op implementation would pass).
"""

from __future__ import annotations

import numpy as np
import pytest
import trimesh

from studio_io.mesh_data import MeshData
from studio_io.mesh_ops import (
    clean,
    convex_hull,
    decimate,
    mesh_stats,
    to_collision_mesh,
)


def mesh_from_trimesh(tri: trimesh.Trimesh, source_format: str = "test") -> MeshData:
    """Build a MeshData the way every loader does: **2-D (M, 3)** index array.

    Verified against the real loader: ``load_stl_mesh()`` returns indices with
    shape ``(140, 3)`` and ``MeshData.triangle_count == len(indices) == 140``.
    """
    vertices = np.asarray(tri.vertices, dtype=np.float32)
    faces = np.asarray(tri.faces, dtype=np.uint32)  # (M, 3)
    lo = tuple(float(x) for x in vertices.min(axis=0))
    hi = tuple(float(x) for x in vertices.max(axis=0))
    return MeshData(
        vertices=vertices,
        indices=faces,
        normals=np.asarray(tri.vertex_normals, dtype=np.float32),
        parts=[],
        bounds_min=lo,
        bounds_max=hi,
        source_format=source_format,
    )


def face_count(mesh: MeshData) -> int:
    """Triangle count regardless of whether indices are (M,3) or flat M*3."""
    return int(np.asarray(mesh.indices).size // 3)


# ---------------------------------------------------------------------------
# 1. Decimation actually decimates, and does not move the bounding box
# ---------------------------------------------------------------------------


def test_decimate_sphere_to_500_keeps_bounding_box() -> None:
    sphere = mesh_from_trimesh(trimesh.creation.icosphere(subdivisions=5))  # 20 * 4**5 = 20480 faces
    assert face_count(sphere) == 20480, "fixture must really be a ~20k-face sphere"

    reduced = decimate(sphere, 500)

    assert face_count(reduced) <= 500, f"expected <= 500 faces, got {face_count(reduced)}"
    assert face_count(reduced) > 0, "decimation must not wipe the mesh out"

    # Bounding box must survive within 5% on every axis.
    for axis, name in enumerate("xyz"):
        original_extent = sphere.bounds_max[axis] - sphere.bounds_min[axis]
        reduced_extent = reduced.bounds_max[axis] - reduced.bounds_min[axis]
        relative_error = abs(reduced_extent - original_extent) / original_extent
        assert relative_error <= 0.05, (
            f"{name} extent drifted {relative_error:.1%} "
            f"(original {original_extent:.6f} -> {reduced_extent:.6f})"
        )


# ---------------------------------------------------------------------------
# 2. Target above the current face count is a no-op, not an error
# ---------------------------------------------------------------------------


def test_decimate_noop_when_target_exceeds_face_count() -> None:
    cube = mesh_from_trimesh(trimesh.creation.box())
    original_faces = face_count(cube)
    assert original_faces == 12

    result = decimate(cube, 1000)

    assert face_count(result) == original_faces, "asking for more faces must not change the mesh"
    # Must be a copy, not the same arrays: callers mutate results.
    assert result.vertices is not cube.vertices
    np.testing.assert_array_equal(result.indices, cube.indices)


# ---------------------------------------------------------------------------
# 3. Convex hull of a non-convex input
# ---------------------------------------------------------------------------


def test_convex_hull_of_two_separated_cubes() -> None:
    left = trimesh.creation.box().apply_translation((-2.0, 0.0, 0.0))
    right = trimesh.creation.box().apply_translation((2.0, 0.0, 0.0))
    two_boxes = mesh_from_trimesh(trimesh.util.concatenate([left, right]))

    assert face_count(two_boxes) == 24
    assert len(two_boxes.vertices) == 16
    # NOTE: trimesh's `is_watertight` is about manifold edges, not connectivity --
    # two disjoint *closed* boxes are still "watertight" (each component is
    # closed). Euler number 4 == two genus-0 components, which is the property
    # we actually care about here.
    assert mesh_stats(two_boxes).euler_number == 4, "fixture must really be two closed components"

    hull = convex_hull(two_boxes)
    hull_stats = mesh_stats(hull)

    assert hull_stats.watertight, "a convex hull must be closed/watertight"
    assert hull_stats.vertices < len(two_boxes.vertices), (
        f"hull should need fewer vertices than the input "
        f"(hull={hull_stats.vertices}, input={len(two_boxes.vertices)})"
    )
    # The hull of two boxes separated on x spans both: extent ~5 (4 apart + 1 wide).
    assert (hull.bounds_max[0] - hull.bounds_min[0]) > 4.5


# ---------------------------------------------------------------------------
# 4. Cleaning removes duplicate and degenerate faces
# ---------------------------------------------------------------------------


def dirty_mesh() -> MeshData:
    """A flat square with one duplicated face and one zero-area face."""
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],  # 0
            [1.0, 0.0, 0.0],  # 1
            [1.0, 1.0, 0.0],  # 2
            [0.0, 1.0, 0.0],  # 3
            [2.0, 0.0, 0.0],  # 4: collinear with 0 and 1 -> degenerate face
        ],
        dtype=np.float32,
    )
    faces = np.array(
        [
            # valid square
            [0, 1, 2],
            [0, 2, 3],
            # duplicate of the first face (same vertex set)
            [0, 1, 2],
            # degenerate: 0,1,4 are collinear -> zero area
            [0, 1, 4],
        ],
        dtype=np.uint32,
    )
    return MeshData(
        vertices=vertices,
        indices=faces,
        normals=np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (len(vertices), 1)),
        parts=[],
        bounds_min=(0.0, 0.0, 0.0),
        bounds_max=(2.0, 1.0, 0.0),
        source_format="dirty",
    )


def test_clean_removes_duplicate_and_degenerate_faces() -> None:
    before = mesh_stats(dirty_mesh())
    # Anti-tautology: the fixture must really be dirty, otherwise a no-op would pass.
    assert before.duplicate_faces == 1, f"fixture should have 1 duplicate face, got {before.duplicate_faces}"
    assert before.degenerate_faces == 1, f"fixture should have 1 degenerate face, got {before.degenerate_faces}"

    cleaned, report = clean(dirty_mesh())

    after = mesh_stats(cleaned)
    assert after.duplicate_faces == 0, f"duplicate faces left: {after.duplicate_faces}"
    assert after.degenerate_faces == 0, f"degenerate faces left: {after.degenerate_faces}"
    # Both repairs must be accounted for in the report.
    assert report["faces_duplicate_removed"] == 1
    assert report["faces_degenerate_removed"] == 1
    assert face_count(cleaned) == 2


def test_clean_merges_coincident_vertices() -> None:
    """Same square, but split so the seam has duplicated vertices."""
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            # duplicated seam for the second triangle
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    faces = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint32)
    split = MeshData(
        vertices=vertices,
        indices=faces,
        normals=np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (6, 1)),
        parts=[],
        bounds_min=(0.0, 0.0, 0.0),
        bounds_max=(1.0, 1.0, 0.0),
        source_format="split",
    )
    assert len(split.vertices) == 6

    merged, report = clean(split)
    assert report["vertices_merged"] == 2, f"expected 2 merged vertices, got {report['vertices_merged']}"
    assert len(merged.vertices) == 4


# ---------------------------------------------------------------------------
# 5. Collision mesh: hull + face budget
# ---------------------------------------------------------------------------


def test_to_collision_mesh_respects_face_budget() -> None:
    sphere = mesh_from_trimesh(trimesh.creation.icosphere(subdivisions=3))  # 1280 faces
    assert face_count(sphere) > 64

    collision = to_collision_mesh(sphere, max_faces=64)

    assert face_count(collision) <= 64, f"budget exceeded: {face_count(collision)} faces"
    assert face_count(collision) >= 4, "a closed hull needs at least a tetrahedron"
    stats = mesh_stats(collision)
    assert stats.watertight, "collision geometry must be closed (watertight)"


# ---------------------------------------------------------------------------
# 6. Index-array contract and parts invalidation
# ---------------------------------------------------------------------------


def test_results_use_2d_index_contract_and_clear_parts() -> None:
    """Output must match the repository's real contract: ``indices`` is (M, 3).

    Verified against the rest of the codebase: ``MeshData.triangle_count`` is
    ``len(indices)`` and ``rendering.py`` / ``urdf_mesh_builder.py`` both treat
    ``len(indices)`` as the triangle count. A flat array here would report 3x
    the faces and break those consumers.
    """
    from studio_io.mesh_data import MeshPart

    sphere = mesh_from_trimesh(trimesh.creation.icosphere(subdivisions=4))
    sphere.parts = [
        MeshPart(
            id="p0",
            name="shell",
            vertex_offset=0,
            vertex_count=len(sphere.vertices),
            triangle_offset=0,
            triangle_count=face_count(sphere),
        )
    ]
    assert sphere.parts, "fixture must carry a part so that clearing is observable"

    reduced = decimate(sphere, 200)

    assert reduced.indices.ndim == 2, f"indices must be (M, 3), got {reduced.indices.shape}"
    assert reduced.indices.shape[1] == 3
    assert reduced.indices.dtype == np.uint32
    # len(indices) IS the triangle count for this codebase -- not len//3.
    assert len(reduced.indices) == face_count(reduced)
    assert len(reduced.indices) <= 200

    # Stale offsets would silently segment the mesh; they must be gone.
    assert reduced.parts == [], "parts must be cleared after remeshing (offsets are stale)"
    assert reduced.source_format == sphere.source_format
    assert reduced.vertices.shape[1] == 3
    assert reduced.normals.shape == reduced.vertices.shape


def test_flat_index_input_is_accepted() -> None:
    """A stale comment says indices are "flat: M*3"; accept that shape too.

    Some producers may hand us a flat array. It must be interpreted correctly --
    if it were treated as (M, 3) directly, the face count would come out 3x too
    large and trimesh would see out-of-range indices.
    """
    cube = trimesh.creation.box()
    flat = MeshData(
        vertices=np.asarray(cube.vertices, dtype=np.float32),
        indices=np.asarray(cube.faces, dtype=np.uint32).reshape(-1),  # flat M*3
        normals=np.asarray(cube.vertex_normals, dtype=np.float32),
        parts=[],
        bounds_min=tuple(float(x) for x in cube.bounds[0]),
        bounds_max=tuple(float(x) for x in cube.bounds[1]),
        source_format="flat",
    )
    assert flat.indices.ndim == 1

    stats = mesh_stats(flat)
    assert stats.faces == 12, f"flat input must be read as 12 faces, got {stats.faces}"

    reduced = decimate(flat, 6)
    assert face_count(reduced) <= 6
    # Output is always the 2-D contract, even when the input was flat.
    assert reduced.indices.ndim == 2 and reduced.indices.shape[1] == 3


# ---------------------------------------------------------------------------
# 7. Guard rails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_target", [0, -5])
def test_decimate_rejects_non_positive_target(bad_target: int) -> None:
    cube = mesh_from_trimesh(trimesh.creation.box())
    with pytest.raises(ValueError):
        decimate(cube, bad_target)


def test_to_collision_mesh_rejects_impossible_budget() -> None:
    cube = mesh_from_trimesh(trimesh.creation.box())
    with pytest.raises(ValueError):
        to_collision_mesh(cube, max_faces=3)
