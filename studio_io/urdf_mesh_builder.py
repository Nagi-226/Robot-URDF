"""URDF mesh geometry builder — resolves visual elements into canonical MeshData.

Adopted from text-to-cad's buildUrdfMeshGeometry() / poseUrdfMeshData() in
kinematics.js.  Handles both mesh-file references and primitive geometries
(box, cylinder, sphere).
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from studio_io.mesh_data import MeshData, MeshPart
from studio_io.mesh_loader import build_edge_indices, build_primitive_mesh, load_mesh_auto


def _parse_origin(element: ET.Element) -> tuple[tuple[float, ...], tuple[float, ...]]:
    origin = element.find("origin")
    if origin is None:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    xyz = tuple(float(v) for v in origin.attrib.get("xyz", "0 0 0").split())
    rpy = tuple(float(v) for v in origin.attrib.get("rpy", "0 0 0").split())
    return xyz, rpy


def _origin_to_matrix(xyz: tuple[float, ...], rpy: tuple[float, ...]) -> list[float]:
    """Convert xyz + rpy to 16-element flat row-major matrix."""
    cr, sr = math.cos(rpy[0]), math.sin(rpy[0])
    cp, sp = math.cos(rpy[1]), math.sin(rpy[1])
    cy, sy = math.cos(rpy[2]), math.sin(rpy[2])
    return [
        cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, xyz[0],
        sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr, xyz[1],
        -sp,     cp * sr,                cp * cr,                xyz[2],
        0.0,     0.0,                    0.0,                    1.0,
    ]


def _mult_m4(a: list[float], b: list[float]) -> list[float]:
    r = [0.0] * 16
    for row in range(4):
        for col in range(4):
            s = 0.0
            for k in range(4):
                s += a[row * 4 + k] * b[k * 4 + col]
            r[row * 4 + col] = s
    return r


def _transform_bounds(
    bmin: tuple[float, float, float],
    bmax: tuple[float, float, float],
    matrix: list[float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Transform AABB by 4x4 matrix (8 corners, recompute min/max)."""
    corners = [
        (bmin[0], bmin[1], bmin[2]),
        (bmax[0], bmin[1], bmin[2]),
        (bmin[0], bmax[1], bmin[2]),
        (bmax[0], bmax[1], bmin[2]),
        (bmin[0], bmin[1], bmax[2]),
        (bmax[0], bmin[1], bmax[2]),
        (bmin[0], bmax[1], bmax[2]),
        (bmax[0], bmax[1], bmax[2]),
    ]
    tx = []
    for x, y, z in corners:
        tx.append(matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3])
        tx.append(matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7])
        tx.append(matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11])
    tx = np.array(tx).reshape(8, 3)
    return (
        tuple(float(v) for v in tx.min(axis=0)),
        tuple(float(v) for v in tx.max(axis=0)),
    )


def build_urdf_mesh_data(urdf_path: str | Path) -> MeshData | None:
    """Build unified MeshData from all visual elements in a URDF file.

    For each link's visual element:
      - If it uses <mesh filename="...">, load the mesh file (STL/GLB).
      - If it uses <box/cylinder/sphere>, generate the primitive mesh.
      - Apply the visual's local origin transform.
      - Track per-part metadata (link name, transform).

    Returns canonical MeshData with per-link parts.
    """
    urdf_path = Path(urdf_path)
    try:
        root = ET.parse(urdf_path).getroot()
    except (ET.ParseError, OSError):
        return None

    all_verts: list[np.ndarray] = []
    all_faces: list[np.ndarray] = []
    all_normals: list[np.ndarray] = []
    parts: list[MeshPart] = []
    v_offset = 0
    t_offset = 0
    uri_base = urdf_path.parent

    for link in root.findall(".//link"):
        link_name = link.attrib.get("name", "unnamed_link")
        for visual in link.findall("visual"):
            geometry = visual.find("geometry")
            if geometry is None:
                continue

            mesh_data = None
            visual_name = f"{link_name}_vis"

            # Check for <mesh> reference
            mesh_elem = geometry.find("mesh")
            if mesh_elem is not None:
                filename = mesh_elem.attrib.get("filename", "")
                if filename.startswith("package://"):
                    # Strip package:// prefix
                    filename = filename.split("//", 1)[1] if "//" in filename else filename
                mesh_path = uri_base / filename
                if mesh_path.is_file():
                    mesh_data = load_mesh_auto(mesh_path)

            # Check for primitives
            if mesh_data is None:
                for ptype in ("box", "cylinder", "sphere"):
                    prim = geometry.find(ptype)
                    if prim is not None:
                        params = {}
                        if ptype == "box":
                            s = prim.attrib.get("size", "1 1 1")
                            params["size"] = tuple(float(v) for v in s.split())
                        elif ptype == "cylinder":
                            params["radius"] = float(prim.attrib.get("radius", "0.5"))
                            params["length"] = float(prim.attrib.get("length", "1.0"))
                        elif ptype == "sphere":
                            params["radius"] = float(prim.attrib.get("radius", "0.5"))
                        mesh_data = build_primitive_mesh(ptype, params, visual_name)
                        break

            if mesh_data is None:
                continue

            # Apply visual origin transform
            vis_xyz, vis_rpy = _parse_origin(visual)
            local_transform = _origin_to_matrix(vis_xyz, vis_rpy)

            # Transform bounds
            bmin, bmax = _transform_bounds(
                mesh_data.bounds_min, mesh_data.bounds_max, local_transform,
            )

            all_verts.append(mesh_data.vertices)
            all_faces.append(mesh_data.indices + v_offset)
            all_normals.append(mesh_data.normals)

            parts.append(MeshPart(
                id=f"{link_name}_{len(parts)}",
                name=visual_name,
                link_name=link_name,
                vertex_offset=v_offset,
                vertex_count=len(mesh_data.vertices),
                triangle_offset=t_offset,
                triangle_count=len(mesh_data.indices),
                bounds_min=bmin,
                bounds_max=bmax,
                transform=local_transform,
            ))
            v_offset += len(mesh_data.vertices)
            t_offset += len(mesh_data.indices)

    if not all_verts:
        return None

    merged_verts = np.vstack(all_verts).astype(np.float32)
    merged_faces = np.vstack(all_faces).astype(np.uint32)
    merged_normals = np.vstack(all_normals).astype(np.float32)
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
        vertices=merged_verts,
        indices=merged_faces,
        normals=merged_normals,
        edge_indices=edge_indices,
        parts=parts,
        bounds_min=lo,
        bounds_max=hi,
        source_format="urdf",
    )


def pose_urdf_mesh_parts(
    mesh_data: MeshData,
    link_world_transforms: dict[str, list[float]],
) -> list[dict]:
    """Apply FK world transforms to per-link mesh parts.

    Args:
        mesh_data: canonical MeshData with per-link parts.
        link_world_transforms: mapping from link name to 16-element world matrix.

    Returns:
        list of {part, world_transform, posed_bounds_min, posed_bounds_max}.
    """
    posed = []
    for part in mesh_data.parts:
        world = link_world_transforms.get(part.link_name)
        if world is None:
            world = [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ]
        # Combine: world * local_transform
        local = part.transform or [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ]
        combined = _mult_m4(world, local)
        bmin, bmax = _transform_bounds(part.bounds_min, part.bounds_max, combined)
        posed.append({
            "part": part,
            "world_transform": combined,
            "posed_bounds_min": bmin,
            "posed_bounds_max": bmax,
        })
    return posed
