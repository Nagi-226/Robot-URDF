from __future__ import annotations

import math
from typing import Sequence


# ---------------------------------------------------------------------------
# 3D transform helpers (flat 16-element array convention, row-major)
# ---------------------------------------------------------------------------

def _zeros() -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _identity() -> list[float]:
    return _zeros()


def _translate(x: float, y: float, z: float) -> list[float]:
    return [
        1.0, 0.0, 0.0, x,
        0.0, 1.0, 0.0, y,
        0.0, 0.0, 1.0, z,
        0.0, 0.0, 0.0, 1.0,
    ]


def _rotate_rpy(roll: float, rad_y: float, pitch: float) -> list[float]:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(rad_y), math.sin(rad_y)
    return [
        cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, 0.0,
        sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr, 0.0,
        -sp,     cp * sr,                cp * cr,                0.0,
        0.0,     0.0,                    0.0,                    1.0,
    ]


def _rotate_axis(ax: float, ay: float, az: float, angle_rad: float) -> list[float]:
    """Rodrigues rotation formula: rotation matrix for axis-angle."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    t = 1.0 - c
    x, y, z = ax, ay, az
    # Normalise axis
    length = math.sqrt(x * x + y * y + z * z)
    if length < 1e-12:
        return _identity()
    x /= length
    y /= length
    z /= length
    return [
        t * x * x + c,     t * x * y - s * z, t * x * z + s * y, 0.0,
        t * x * y + s * z, t * y * y + c,     t * y * z - s * x, 0.0,
        t * x * z - s * y, t * y * z + s * x, t * z * z + c,     0.0,
        0.0,               0.0,               0.0,               1.0,
    ]


def _mult(a: list[float], b: list[float]) -> list[float]:
    """Multiply two 4x4 matrices (flat 16, row-major)."""
    r = [0.0] * 16
    for row in range(4):
        for col in range(4):
            s = 0.0
            for k in range(4):
                s += a[row * 4 + k] * b[k * 4 + col]
            r[row * 4 + col] = s
    return r


def _extract_translation(m: list[float]) -> tuple[float, float, float]:
    return (m[3], m[7], m[11])


# ---------------------------------------------------------------------------
# Joint-level transform builder
# ---------------------------------------------------------------------------

def joint_local_transform(
    origin_xyz: tuple[float, float, float],
    origin_rpy: tuple[float, float, float],
    axis_xyz: tuple[float, float, float],
    angle_deg: float,
) -> list[float]:
    """Build the 4x4 local transform for a joint at a given angle.

    T_local = translate(origin) * rotate_rpy(rpy) * rotate_axis(axis, angle)
    """
    t_origin = _translate(*origin_xyz)
    r_rpy = _rotate_rpy(*origin_rpy)
    r_axis = _rotate_axis(*axis_xyz, math.radians(angle_deg))
    return _mult(_mult(t_origin, r_rpy), r_axis)


# ---------------------------------------------------------------------------
# High-level FK
# ---------------------------------------------------------------------------

def compute_forward_kinematics(
    bone_lengths: list[float],
    joint_angles_degrees: list[float],
    base_angle_degrees: float = -90.0,
    angle_scale: float = 0.45,
) -> list[tuple[float, float, float]]:
    """Legacy 2D planar FK for the skeleton viewport fallback."""
    x, y, z = 0.0, 0.0, 0.0
    angle = math.radians(base_angle_degrees + joint_angles_degrees[0])
    positions: list[tuple[float, float, float]] = [(x, y, z)]

    for idx, length in enumerate(bone_lengths):
        if idx + 1 < len(joint_angles_degrees):
            angle += math.radians(joint_angles_degrees[idx + 1] * angle_scale)
        nx = x + math.cos(angle) * length
        ny = y + math.sin(angle) * length
        positions.append((nx, ny, z))
        x, y = nx, ny

    return positions


def compute_3d_chain_fk(
    joint_names: Sequence[str],
    joint_values_deg: Sequence[float],
    joint_origins: Sequence[tuple[float, float, float]],
    joint_rpys: Sequence[tuple[float, float, float]],
    joint_axes: Sequence[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    """Compute 3D link positions for a serial chain using URDF joint data.

    Each joint's local transform is applied in order, accumulating a world
    transform from the base frame.  Returns one (x, y, z) position per link
    (starting from the base at origin).

    All inputs must be the same length (one entry per joint).
    """
    if not joint_names:
        return [(0.0, 0.0, 0.0)]

    world = _identity()
    positions: list[tuple[float, float, float]] = [_extract_translation(world)]

    for i in range(len(joint_names)):
        angle = joint_values_deg[i] if i < len(joint_values_deg) else 0.0
        origin = joint_origins[i] if i < len(joint_origins) else (0.0, 0.0, 0.0)
        rpy = joint_rpys[i] if i < len(joint_rpys) else (0.0, 0.0, 0.0)
        axis = joint_axes[i] if i < len(joint_axes) else (0.0, 0.0, 1.0)
        local = joint_local_transform(origin, rpy, axis, angle)
        world = _mult(world, local)
        positions.append(_extract_translation(world))

    return positions


def compute_3d_tree_fk(
    joint_names: Sequence[str],
    joint_values_deg: Sequence[float],
    joint_parents: Sequence[str],
    joint_children: Sequence[str],
    joint_origins: Sequence[tuple[float, float, float]],
    joint_rpys: Sequence[tuple[float, float, float]],
    joint_axes: Sequence[tuple[float, float, float]],
    link_names: Sequence[str],
    root_link: str,
) -> dict[str, tuple[float, float, float]]:
    """Compute 3D link positions for a tree-structured robot.

    Walks the joint tree via DFS from the root link, accumulating world
    transforms.  Returns a mapping from link name to (x, y, z) world position.
    """
    if not joint_names:
        return {root_link: (0.0, 0.0, 0.0)}

    # Build index by child link name
    joint_by_child: dict[str, int] = {}
    for i, child in enumerate(joint_children):
        joint_by_child[child] = i

    # Build children map for DFS
    children_of: dict[str, list[str]] = {}
    for i, (parent, child) in enumerate(zip(joint_parents, joint_children)):
        children_of.setdefault(parent, []).append(child)

    link_positions: dict[str, tuple[float, float, float]] = {}

    def _dfs(link: str, parent_world: list[float]) -> None:
        link_positions[link] = _extract_translation(parent_world)
        for child in children_of.get(link, []):
            if child not in joint_by_child:
                continue
            idx = joint_by_child[child]
            angle = joint_values_deg[idx] if idx < len(joint_values_deg) else 0.0
            origin = joint_origins[idx] if idx < len(joint_origins) else (0.0, 0.0, 0.0)
            rpy = joint_rpys[idx] if idx < len(joint_rpys) else (0.0, 0.0, 0.0)
            axis = joint_axes[idx] if idx < len(joint_axes) else (0.0, 0.0, 1.0)
            local = joint_local_transform(origin, rpy, axis, angle)
            child_world = _mult(parent_world, local)
            _dfs(child, child_world)

    _dfs(root_link, _identity())
    return link_positions


def compute_3d_tree_fk_transforms(
    joint_names: Sequence[str],
    joint_values_deg: Sequence[float],
    joint_parents: Sequence[str],
    joint_children: Sequence[str],
    joint_origins: Sequence[tuple[float, float, float]],
    joint_rpys: Sequence[tuple[float, float, float]],
    joint_axes: Sequence[tuple[float, float, float]],
    root_link: str,
) -> dict[str, list[float]]:
    """Compute 4x4 world transforms for each link in a URDF joint tree."""
    if not joint_names:
        return {root_link: _identity()}

    joint_by_child = {child: i for i, child in enumerate(joint_children)}
    children_of: dict[str, list[str]] = {}
    for parent, child in zip(joint_parents, joint_children):
        children_of.setdefault(parent, []).append(child)

    transforms: dict[str, list[float]] = {}

    def _dfs(link: str, parent_world: list[float]) -> None:
        transforms[link] = parent_world
        for child in children_of.get(link, []):
            idx = joint_by_child.get(child)
            if idx is None:
                continue
            angle = joint_values_deg[idx] if idx < len(joint_values_deg) else 0.0
            origin = joint_origins[idx] if idx < len(joint_origins) else (0.0, 0.0, 0.0)
            rpy = joint_rpys[idx] if idx < len(joint_rpys) else (0.0, 0.0, 0.0)
            axis = joint_axes[idx] if idx < len(joint_axes) else (0.0, 0.0, 1.0)
            _dfs(child, _mult(parent_world, joint_local_transform(origin, rpy, axis, angle)))

    _dfs(root_link, _identity())
    return transforms
