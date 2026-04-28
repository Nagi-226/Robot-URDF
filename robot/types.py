from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChainPose:
    """Full kinematic chain state for one joint configuration."""
    joint_names: list[str]
    joint_values: list[float]
    positions_3d: list[tuple[float, float, float]]
    link_names: list[str]
