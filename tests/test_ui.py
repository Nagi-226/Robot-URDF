"""Tests for UI modules: workflow_status, data models, collapsible panel."""

import sys
import pytest

from ui.workflow_status import (
    ConnectionHealth,
    ConnectionState,
    MotionState,
    build_workflow_status_snapshot,
    compare_snapshots,
    DeviceConsoleStatus,
    TelemetryStatus,
    WorkflowStatusDelta,
    WorkflowStatusSnapshot,
)

_qapp = None
try:
    from PySide6.QtWidgets import QApplication
    _qapp = QApplication.instance() or QApplication(sys.argv)
except Exception:
    pass


def _require_qapp():
    if _qapp is None:
        pytest.skip("QApplication not available")


class TestConnectionHealth:
    def test_connected_ready(self):
        health = ConnectionHealth.derive(ConnectionState.CONNECTED, True)
        assert health == ConnectionHealth.READY

    def test_connected_busy(self):
        health = ConnectionHealth.derive(ConnectionState.CONNECTED, False)
        assert health == ConnectionHealth.BUSY

    def test_disconnected(self):
        health = ConnectionHealth.derive(ConnectionState.DISCONNECTED, False)
        assert health == ConnectionHealth.OFFLINE

    def test_connecting(self):
        health = ConnectionHealth.derive(ConnectionState.CONNECTING, False)
        assert health == ConnectionHealth.CONNECTING

    def test_fault(self):
        health = ConnectionHealth.derive(ConnectionState.FAULT, False)
        assert health == ConnectionHealth.FAULT

    def test_unknown_falls_to_offline(self):
        health = ConnectionHealth.derive("UnknownState", False)
        assert health == ConnectionHealth.OFFLINE


class TestMotionState:
    def test_standby_is_healthy(self):
        assert MotionState.is_healthy("standby") is True

    def test_idle_is_healthy(self):
        assert MotionState.is_healthy("idle") is True

    def test_ready_is_healthy(self):
        assert MotionState.is_healthy("ready") is True

    def test_homing_is_not_healthy(self):
        assert MotionState.is_healthy("homing") is False

    def test_case_insensitive(self):
        assert MotionState.is_healthy("STANDBY") is True


class TestDeviceConsoleStatus:
    def test_health_from_connection(self):
        status = DeviceConsoleStatus(
            connection_state=ConnectionState.CONNECTED, port="COM3",
            baud_rate="115200", command_ready=True,
        )
        assert status.connection_health == ConnectionHealth.READY

    def test_disconnected_health(self):
        status = DeviceConsoleStatus(
            connection_state=ConnectionState.DISCONNECTED, port="COM3",
            baud_rate="115200", command_ready=False,
        )
        assert status.connection_health == ConnectionHealth.OFFLINE


class TestTelemetryStatus:
    def test_summary_no_warnings(self):
        t = TelemetryStatus(heartbeat="active", joint_count=6,
                            motion_state="standby", temperature_c=31.5,
                            supply_voltage_v=24.0)
        assert "no warnings" in t.summary

    def test_summary_with_warnings(self):
        t = TelemetryStatus(heartbeat="active", joint_count=6,
                            motion_state="standby", temperature_c=31.5,
                            supply_voltage_v=24.0, warnings=["overheat"])
        assert "1 warning(s)" in t.summary


class TestWorkflowStatusSnapshot:
    def test_build_default_snapshot(self):
        snap = build_workflow_status_snapshot()
        assert snap.device.connection_state == ConnectionState.DISCONNECTED
        assert snap.device.port == "COM3"
        assert snap.telemetry.joint_count == 6

    def test_build_connected_snapshot(self):
        snap = build_workflow_status_snapshot(connection_state=ConnectionState.CONNECTED)
        assert snap.device.connection_state == ConnectionState.CONNECTED
        assert snap.device.command_ready is True

    def test_compact_summary(self):
        snap = build_workflow_status_snapshot()
        summary = snap.compact_summary()
        assert "conn=" in summary
        assert "telem=" in summary

    def test_device_lines(self):
        snap = build_workflow_status_snapshot()
        lines = snap.device_lines()
        assert any("connection=" in l for l in lines)

    def test_telemetry_lines(self):
        snap = build_workflow_status_snapshot()
        lines = snap.telemetry_lines()
        assert any("heartbeat=" in l for l in lines)
        assert any("temperature_c=" in l for l in lines)


class TestCompareSnapshots:
    def test_no_changes(self):
        snap = build_workflow_status_snapshot()
        delta = compare_snapshots(snap, snap)
        assert delta.connection_changed is False
        assert delta.telemetry_changed is False
        assert delta.note == ""

    def test_connection_change_detected(self):
        prev = build_workflow_status_snapshot(connection_state=ConnectionState.DISCONNECTED)
        curr = build_workflow_status_snapshot(connection_state=ConnectionState.CONNECTED)
        delta = compare_snapshots(prev, curr)
        assert delta.connection_changed is True
        assert "connection:" in delta.note
        assert ConnectionState.DISCONNECTED in delta.note
        assert ConnectionState.CONNECTED in delta.note

    def test_telemetry_change_detected(self):
        prev = build_workflow_status_snapshot(motion_state="standby")
        curr = build_workflow_status_snapshot(motion_state="active")
        delta = compare_snapshots(prev, curr)
        assert delta.telemetry_changed is True
        assert "motion_state" in delta.note


class TestPosePreset:
    def test_creation(self):
        from ui.shell import PosePreset
        pose = PosePreset("Test", [1.0, 2.0, 3.0])
        assert pose.name == "Test"
        assert pose.values == [1.0, 2.0, 3.0]


class TestSelectionState:
    def test_creation(self):
        from ui.shell import SelectionState
        state = SelectionState("joint1", "joint")
        assert state.label == "joint1"
        assert state.kind == "joint"


class TestUrdfModelSummary:
    def test_creation(self):
        from ui.shell import UrdfModelSummary
        summary = UrdfModelSummary(robot_name="test", links=[], joints=[], warnings=[])
        assert summary.robot_name == "test"


class TestViewportControlApi:
    def test_robot_viewport_exposes_view_control_methods(self):
        _require_qapp()
        from ui.shell import RobotViewport
        viewport = RobotViewport()
        assert viewport.export_screenshot is not None
        viewport.reset_camera()
        viewport.set_wireframe(True)
        viewport.set_camera_preset("isometric")

    def test_robot_viewport_hud_metrics_are_populated(self):
        _require_qapp()
        from ui.shell import RobotViewport

        viewport = RobotViewport()
        metrics = viewport.hud_metrics()

        assert metrics["model"]
        assert metrics["joints"].isdigit()
        assert metrics["camera"] in {"skeleton", "orbit"}
        assert "FPS" in metrics["fps"]


class TestThemeManager:
    def test_theme_definitions_load_qss(self):
        from app.theme import ThemeManager

        manager = ThemeManager.instance()
        keys = {theme.key for theme in manager.available_themes()}

        assert {"industrial_dark", "high_contrast", "compact"}.issubset(keys)
        assert "#TopNav" in manager.load_qss("industrial_dark")

    def test_unknown_theme_falls_back_to_default(self):
        from app.theme import ThemeManager

        qss = ThemeManager.instance().load_qss("missing_theme")

        assert "Dark Industrial Precision" in qss


class TestUpdateCheck:
    def test_version_tuple_and_comparison(self):
        from app.update_check import is_newer_version, version_tuple

        assert version_tuple("v0.7.5") == (0, 7, 5)
        assert is_newer_version("v0.7.6", "v0.7.5") is True
        assert is_newer_version("v0.7.5", "v0.7.5") is False


class TestOnboarding:
    def test_onboarding_dialog_constructs(self):
        _require_qapp()
        from app.onboarding import OnboardingDialog

        dialog = OnboardingDialog()

        assert dialog.windowTitle() == "Robot URDF Studio Setup"
        assert dialog.language.count() == 2
        assert dialog.theme.count() >= 3


class TestWorkspaceCadViewportIntegration:
    def test_pick_candidates_strip_viewport_prefixes(self):
        from ui.shell import WorkspaceShell

        candidates = WorkspaceShell._tree_candidates_from_pick({
            "part_id": "cad_base_mount",
            "face_part_id": "link_base_link",
        })

        assert "cad_base_mount" in candidates
        assert "base_mount" in candidates
        assert "base_link" in candidates

    def test_cad_pick_records_undo_redo_refresh_path(self):
        _require_qapp()
        from ui.shell import WorkspaceShell

        shell = WorkspaceShell()
        mapping = shell._resolve_pick_cad_handle({
            "part_id": "cad_base_mount",
            "face_index": 0,
        })
        assert mapping is not None

        shell._record_pick_edit(mapping)
        assert shell.edit_history.can_undo is True
        undone = shell.undo_last_cad_edit()
        redone = shell.redo_last_cad_edit()

        assert undone is not None
        assert redone is not None
