"""Tests for the robot package: fk, chain, types."""

import math

import pytest

from robot.fk import compute_3d_tree_fk_transforms, compute_forward_kinematics
from robot.types import ChainPose
from robot.chain import KinematicChain
from robot_model import RobotJoint, RobotLink, RobotModel


class TestForwardKinematics:
    def test_zero_bones_returns_origin(self):
        positions = compute_forward_kinematics([], [0.0])
        assert len(positions) == 1
        assert positions[0] == (0.0, 0.0, 0.0)

    def test_zero_angles_produces_straight_line(self):
        positions = compute_forward_kinematics(
            [100.0, 100.0], [0.0, 0.0, 0.0],
            base_angle_degrees=0.0, angle_scale=1.0,
        )
        assert len(positions) == 3
        for i, p in enumerate(positions):
            assert p[0] == pytest.approx(100.0 * i, abs=0.01)
            assert p[1] == pytest.approx(0.0, abs=0.01)

    def test_empty_angles_list(self):
        positions = compute_forward_kinematics([100.0], [30.0])
        assert len(positions) == 2

    def test_known_angle_45_degrees(self):
        positions = compute_forward_kinematics(
            [100.0], [0.0, 45.0],
            base_angle_degrees=0.0, angle_scale=1.0,
        )
        x, y, _ = positions[1]
        expected = 100.0 * math.cos(math.radians(45.0))
        assert x == pytest.approx(expected, abs=0.1)
        assert y == pytest.approx(expected, abs=0.1)

    def test_three_bone_chain(self):
        positions = compute_forward_kinematics(
            [100.0, 100.0, 100.0],
            [-90.0, 45.0, -30.0, 0.0],
        )
        assert len(positions) == 4

    def test_tree_fk_transforms_include_joint_origin(self):
        transforms = compute_3d_tree_fk_transforms(
            ["base_to_link"],
            [0.0],
            ["base"],
            ["link"],
            [(1.0, 2.0, 3.0)],
            [(0.0, 0.0, 0.0)],
            [(0.0, 0.0, 1.0)],
            "base",
        )
        assert transforms["base"][3] == pytest.approx(0.0)
        assert transforms["link"][3] == pytest.approx(1.0)
        assert transforms["link"][7] == pytest.approx(2.0)
        assert transforms["link"][11] == pytest.approx(3.0)


class TestChainPose:
    def test_empty_construction(self):
        pose = ChainPose(
            joint_names=[], joint_values=[], positions_3d=[], link_names=[],
        )
        assert pose.joint_names == []
        assert len(pose.positions_3d) == 0

    def test_valid_pose(self):
        pose = ChainPose(
            joint_names=["j1", "j2"],
            joint_values=[0.0, 45.0],
            positions_3d=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
            link_names=["base", "link1", "link2"],
        )
        assert len(pose.positions_3d) == 3


def _make_test_model():
    return RobotModel(
        name="test_arm",
        links=[RobotLink("base_link"), RobotLink("shoulder_link"), RobotLink("elbow_link")],
        joints=[
            RobotJoint("base_to_shoulder", "base_link", "shoulder_link"),
            RobotJoint("shoulder_to_elbow", "shoulder_link", "elbow_link"),
        ],
    )


class TestKinematicChain:
    def test_empty_model_falls_back_to_default(self):
        model = RobotModel(name="empty")
        chain = KinematicChain(model)
        assert len(chain.joint_names) == 6

    def test_valid_model_builds_chain(self):
        model = _make_test_model()
        chain = KinematicChain(model)
        assert len(chain.joint_names) >= 2
        assert "base_link" in chain.link_names

    def test_compute_pose_with_values(self):
        model = _make_test_model()
        chain = KinematicChain(model)
        pose = chain.compute_pose([10.0] * len(chain.joint_names))
        assert len(pose.positions_3d) > 0

    def test_compute_pose_empty_values(self):
        model = _make_test_model()
        chain = KinematicChain(model)
        pose = chain.compute_pose([])
        assert len(pose.positions_3d) == 0

    def test_chain_uses_default_bone_lengths(self):
        model = _make_test_model()
        chain = KinematicChain(model)
        assert all(b == 120.0 for b in chain.bone_lengths)
