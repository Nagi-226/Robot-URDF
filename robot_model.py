from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class JointSpec:
    name: str
    minimum: float
    maximum: float
    default: float


@dataclass(frozen=True)
class RobotLink:
    name: str


@dataclass(frozen=True)
class RobotJoint:
    name: str
    parent: str
    child: str


@dataclass
class RobotModel:
    name: str = "Robot Workspace"
    links: list[RobotLink] = field(default_factory=list)
    joints: list[RobotJoint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def link_count(self) -> int:
        return len(self.links)

    def joint_count(self) -> int:
        return len(self.joints)


@dataclass(frozen=True)
class ViewState:
    model_path: str = "No model loaded"
    selected_item: str = "No selection"
    selection_kind: str = "none"
    viewport_mode: str = "skeleton"
