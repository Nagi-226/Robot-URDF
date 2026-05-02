"""Central configuration for Robot URDF Studio geometry and theming defaults."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudioConfig:
    window_width: int = 1280
    window_height: int = 800
    window_min_width: int = 1024
    window_min_height: int = 600

    left_panel_min_width: int = 250
    right_panel_min_width: int = 280
    right_panel_max_width: int = 340

    viewport_min_width: int = 480
    viewport_min_height: int = 340

    log_max_height: int = 72

    default_bone_length: float = 120.0
    joint_angle_scale: float = 0.45
    base_angle_degrees: float = -90.0


CONFIG = StudioConfig()
