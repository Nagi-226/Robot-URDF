from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class JointSpec:
    name: str
    minimum: float
    maximum: float
    default: float
    origin_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    origin_rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)
    axis_xyz: tuple[float, float, float] = (0.0, 0.0, 1.0)


@dataclass(frozen=True)
class RobotLink:
    name: str


@dataclass(frozen=True)
class RobotJoint:
    name: str
    parent: str
    child: str
    origin_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    origin_rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)
    axis_xyz: tuple[float, float, float] = (0.0, 0.0, 1.0)


@dataclass
class RobotModel:
    name: str = "Robot Workspace"
    links: list[RobotLink] = field(default_factory=list)
    joints: list[RobotJoint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def link_count(self) -> int:
        return len(self.links)

    @property
    def joint_count(self) -> int:
        return len(self.joints)


@dataclass(frozen=True)
class ViewState:
    model_path: str = "No model loaded"
    selected_item: str = "No selection"
    selection_kind: str = "none"
    viewport_mode: str = "skeleton"
