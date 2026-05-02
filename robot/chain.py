from __future__ import annotations

import math

from robot_model import RobotModel

from robot.fk import (
    compute_3d_chain_fk,
    compute_3d_tree_fk,
    compute_forward_kinematics,
)
from robot.types import ChainPose


_DEFAULT_JOINT_NAMES = [
    "base_yaw", "shoulder_pitch", "elbow_pitch",
    "wrist_pitch", "wrist_roll", "gripper",
]
_DEFAULT_BONE_LENGTHS = [120.0, 140.0, 120.0, 90.0, 70.0]
_DEFAULT_LINK_NAMES = ["base", "shoulder", "elbow", "wrist", "wrist_rotated", "gripper"]


def _origin_length(origin_xyz: tuple[float, float, float]) -> float:
    length = math.sqrt(sum(v * v for v in origin_xyz))
    return length if length > 0.001 else 120.0


def _has_3d_data(model: RobotModel) -> bool:
    """Return True when joints carry real axis data (vs default 0,0,1)."""
    if not model.joints:
        return False
    for j in model.joints:
        if j.axis_xyz != (0.0, 0.0, 1.0) or j.origin_xyz != (0.0, 0.0, 0.0):
            return True
    return False


class KinematicChain:
    """Kinematic chain built from a RobotModel's joint graph.

    When the model has no links or joints, falls back to a hardcoded
    6-DOF default chain so the 2D skeleton viewport always has bones
    to render.

    When joints carry axis / origin data (e.g. from URDF import), 3D
    forward kinematics are used instead of the planar 2D solver.
    """

    def __init__(self, model: RobotModel) -> None:
        self.joint_names: list[str] = []
        self.bone_lengths: list[float] = []
        self.link_names: list[str] = []
        self._use_3d = _has_3d_data(model)
        self._joint_origins: list[tuple[float, float, float]] = []
        self._joint_rpys: list[tuple[float, float, float]] = []
        self._joint_axes: list[tuple[float, float, float]] = []
        self._joint_parents: list[str] = []
        self._joint_children: list[str] = []
        self._root_link = ""
        self._is_tree = False
        self._build_from_model(model)

    def _build_from_model(self, model: RobotModel) -> None:
        if not model.links or not model.joints:
            self._build_default_chain()
            return

        child_to_parent: dict[str, str] = {}
        parent_to_children: dict[str, list[str]] = {}
        joint_by_child: dict[str, str] = {}
        origin_by_joint: dict[str, tuple[float, float, float]] = {}
        rpy_by_joint: dict[str, tuple[float, float, float]] = {}
        axis_by_joint: dict[str, tuple[float, float, float]] = {}
        parent_by_joint: dict[str, str] = {}
        child_by_joint: dict[str, str] = {}
        all_links: set[str] = set()

        for joint in model.joints:
            child_to_parent[joint.child] = joint.parent
            parent_to_children.setdefault(joint.parent, []).append(joint.child)
            joint_by_child[joint.child] = joint.name
            origin_by_joint[joint.name] = joint.origin_xyz
            rpy_by_joint[joint.name] = joint.origin_rpy
            axis_by_joint[joint.name] = joint.axis_xyz
            parent_by_joint[joint.name] = joint.parent
            child_by_joint[joint.name] = joint.child
            all_links.add(joint.parent)
            all_links.add(joint.child)

        roots = [link for link in all_links if link not in child_to_parent]
        if not roots:
            self._build_default_chain()
            return

        self._root_link = roots[0]

        # Detect tree: any link has >1 child
        self._is_tree = any(len(children) > 1 for children in parent_to_children.values())

        if self._is_tree and self._use_3d:
            self._build_tree_chain(
                joint_by_child, parent_to_children, origin_by_joint,
                rpy_by_joint, axis_by_joint, parent_by_joint, child_by_joint,
                roots[0],
            )
            return

        # Serial chain: follow first child from root
        current = roots[0]
        ordered_joints: list[str] = []
        ordered_links: list[str] = [current]

        while current in parent_to_children:
            children = parent_to_children[current]
            if not children:
                break
            child = children[0]
            if child not in joint_by_child:
                break
            jname = joint_by_child[child]
            ordered_joints.append(jname)
            ordered_links.append(child)
            current = child

        if len(ordered_joints) < 1:
            self._build_default_chain()
            return

        self.joint_names = ordered_joints
        self.link_names = ordered_links
        self._joint_origins = [origin_by_joint.get(jn, (0.0, 0.0, 0.0)) for jn in ordered_joints]
        self._joint_rpys = [rpy_by_joint.get(jn, (0.0, 0.0, 0.0)) for jn in ordered_joints]
        self._joint_axes = [axis_by_joint.get(jn, (0.0, 0.0, 1.0)) for jn in ordered_joints]
        self._joint_parents = [parent_by_joint.get(jn, "") for jn in ordered_joints]
        self._joint_children = [child_by_joint.get(jn, "") for jn in ordered_joints]
        self.bone_lengths = [
            _origin_length(origin_by_joint.get(jn, (0.0, 0.0, 0.0)))
            for jn in ordered_joints
        ]

    def _build_tree_chain(
        self, joint_by_child, parent_to_children, origin_by_joint,
        rpy_by_joint, axis_by_joint, parent_by_joint, child_by_joint,
        root: str,
    ) -> None:
        # BFS order for slider display; DFS for FK is handled at solve time
        ordered_joints: list[str] = []
        ordered_links: list[str] = [root]
        visited_links = {root}
        queue = [root]
        while queue:
            parent = queue.pop(0)
            for child in parent_to_children.get(parent, []):
                if child in joint_by_child and child not in visited_links:
                    visited_links.add(child)
                    jname = joint_by_child[child]
                    ordered_joints.append(jname)
                    ordered_links.append(child)
                    queue.append(child)

        self.joint_names = ordered_joints
        self.link_names = ordered_links
        self._joint_origins = [origin_by_joint.get(jn, (0.0, 0.0, 0.0)) for jn in ordered_joints]
        self._joint_rpys = [rpy_by_joint.get(jn, (0.0, 0.0, 0.0)) for jn in ordered_joints]
        self._joint_axes = [axis_by_joint.get(jn, (0.0, 0.0, 1.0)) for jn in ordered_joints]
        self._joint_parents = [parent_by_joint.get(jn, "") for jn in ordered_joints]
        self._joint_children = [child_by_joint.get(jn, "") for jn in ordered_joints]
        self.bone_lengths = [
            _origin_length(origin_by_joint.get(jn, (0.0, 0.0, 0.0)))
            for jn in ordered_joints
        ]

    def _build_default_chain(self) -> None:
        self.joint_names = list(_DEFAULT_JOINT_NAMES)
        self.bone_lengths = list(_DEFAULT_BONE_LENGTHS)
        self.link_names = list(_DEFAULT_LINK_NAMES)
        self._use_3d = False

    def compute_pose(self, joint_values: list[float]) -> ChainPose:
        """Run FK for the given joint values (degrees)."""
        if not joint_values:
            return ChainPose(
                joint_names=list(self.joint_names),
                joint_values=[],
                positions_3d=[],
                link_names=list(self.link_names),
            )

        if self._use_3d and self._joint_origins:
            if self._is_tree:
                link_positions = compute_3d_tree_fk(
                    self.joint_names, joint_values,
                    self._joint_parents, self._joint_children,
                    self._joint_origins, self._joint_rpys, self._joint_axes,
                    self.link_names, self._root_link,
                )
                positions = [link_positions.get(ln, (0.0, 0.0, 0.0)) for ln in self.link_names]
            else:
                positions = compute_3d_chain_fk(
                    self.joint_names, joint_values,
                    self._joint_origins, self._joint_rpys, self._joint_axes,
                )
        else:
            positions = compute_forward_kinematics(self.bone_lengths, joint_values)

        return ChainPose(
            joint_names=list(self.joint_names),
            joint_values=list(joint_values),
            positions_3d=positions,
            link_names=list(self.link_names),
        )
