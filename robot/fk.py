from __future__ import annotations

import math


def compute_forward_kinematics(
    bone_lengths: list[float],
    joint_angles_degrees: list[float],
    base_angle_degrees: float = -90.0,
    angle_scale: float = 0.45,
) -> list[tuple[float, float, float]]:
    """Compute 3D positions along a serial kinematic chain.

    Args:
        bone_lengths: length of each bone segment, len N.
        joint_angles_degrees: absolute joint angles in degrees, len N+1.
            joint_angles[0] is the base yaw offset; angles[1:]
            are scaled by `angle_scale` before accumulation.
        base_angle_degrees: absolute angle for the first bone.
        angle_scale: multiplier applied to each joint angle increment.

    Returns:
        list of (x, y, z) world positions, one per joint (length = N+1).
    """
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
