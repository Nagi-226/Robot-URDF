from __future__ import annotations

from robot_model import RobotModel

from robot.fk import compute_forward_kinematics
from robot.types import ChainPose


# Hardcoded for backward compatibility with the existing 2D skeleton visual.
_DEFAULT_JOINT_NAMES = [
    "base_yaw", "shoulder_pitch", "elbow_pitch",
    "wrist_pitch", "wrist_roll", "gripper",
]
_DEFAULT_BONE_LENGTHS = [120.0, 140.0, 120.0, 90.0, 70.0]
_DEFAULT_LINK_NAMES = ["base", "shoulder", "elbow", "wrist", "wrist_rotated", "gripper"]


class KinematicChain:
    """Ordered serial chain built from a RobotModel's joint graph.

    When the model has no links or joints, falls back to a hardcoded
    6-DOF default chain so the 2D skeleton viewport always has bones
    to render.
    """

    def __init__(self, model: RobotModel) -> None:
        self.joint_names: list[str] = []
        self.bone_lengths: list[float] = []
        self.link_names: list[str] = []
        self._build_from_model(model)

    def _build_from_model(self, model: RobotModel) -> None:
        if not model.links or not model.joints:
            self._build_default_chain()
            return

        child_to_parent: dict[str, str] = {}
        parent_to_children: dict[str, list[str]] = {}
        joint_by_child: dict[str, str] = {}
        all_links: set[str] = set()

        for joint in model.joints:
            child_to_parent[joint.child] = joint.parent
            parent_to_children.setdefault(joint.parent, []).append(joint.child)
            joint_by_child[joint.child] = joint.name
            all_links.add(joint.parent)
            all_links.add(joint.child)

        roots = [link for link in all_links if link not in child_to_parent]
        if not roots:
            self._build_default_chain()
            return

        current = roots[0]
        ordered_joints: list[str] = []
        ordered_links: list[str] = [current]

        while current in joint_by_child:
            children = parent_to_children.get(current, [])
            if not children:
                break
            child = children[0]
            ordered_joints.append(joint_by_child[child])
            ordered_links.append(child)
            current = child

        if len(ordered_joints) < 1:
            self._build_default_chain()
            return

        self.joint_names = ordered_joints
        self.link_names = ordered_links
        self.bone_lengths = [120.0] * len(ordered_joints)

    def _build_default_chain(self) -> None:
        self.joint_names = list(_DEFAULT_JOINT_NAMES)
        self.bone_lengths = list(_DEFAULT_BONE_LENGTHS)
        self.link_names = list(_DEFAULT_LINK_NAMES)

    def compute_pose(self, joint_values: list[float]) -> ChainPose:
        """Run FK for the given joint values (degrees)."""
        if not joint_values:
            return ChainPose(
                joint_names=list(self.joint_names),
                joint_values=[],
                positions_3d=[],
                link_names=list(self.link_names),
            )
        positions = compute_forward_kinematics(self.bone_lengths, joint_values)
        return ChainPose(
            joint_names=list(self.joint_names),
            joint_values=list(joint_values),
            positions_3d=positions,
            link_names=list(self.link_names),
        )
