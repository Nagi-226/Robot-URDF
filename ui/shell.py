from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from robot_model import JointSpec, RobotJoint, RobotLink, RobotModel, ViewState
from rendering import FakeThreeDViewportBackend, SkeletonViewportBackend, ViewportBackend, ViewportOverlay
from ui.workflow_status import build_workflow_status_snapshot, compare_snapshots, WorkflowStatusSnapshot


RECENT_PROJECTS = ["AtlasArm / production-cell-01", "DeltaBot / calibration-suite", "FieldRig / embedded-testbench"]
DEVICE_PORTS = ["COM3", "COM5", "COM8", "USB0"]
PROJECT_HINTS = ["models", "assets", "configs", "logs", "firmware", "urdf"]
URDF_HINTS = [".urdf", ".xacro", ".xml"]
RESOURCE_SUFFIXES = {".stl", ".dae", ".obj", ".step", ".stp", ".json", ".yaml", ".yml", ".launch", ".py", ".cfg", ".ini"}


def _infer_selection_kind(text: str) -> str:
    """Classify a tree item label into a selection kind."""
    lowered = text.lower()
    if lowered.startswith("urdf:"):
        return "urdf"
    if lowered.startswith("links"):
        return "links"
    if lowered.startswith("joints"):
        return "joints"
    if lowered.startswith("warnings"):
        return "warnings"
    if lowered.endswith("/"):
        return "folder"
    return "item"


@dataclass(frozen=True)
class PosePreset:
    name: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class UrdfModelSummary:
    robot_name: str
    links: list[str]
    joints: list[tuple[str, str, str]]
    warnings: list[str]


@dataclass(frozen=True)
class SelectionState:
    label: str = "No selection"
    kind: str = "none"


POSES: list[PosePreset] = [
    PosePreset("Home", (0, 25, 35, -10, 0, 15)),
    PosePreset("Reach", (20, 55, 40, -25, 15, 10)),
    PosePreset("Inspect", (-30, 40, 10, 15, -20, 35)),
]

JOINT_SPECS: list[JointSpec] = [
    JointSpec("base_yaw", -180, 180, 0),
    JointSpec("shoulder_pitch", -90, 120, 30),
    JointSpec("elbow_pitch", -120, 120, 45),
    JointSpec("wrist_pitch", -180, 180, -15),
    JointSpec("wrist_roll", -180, 180, 0),
    JointSpec("gripper", 0, 90, 20),
]


class JointSlider(QWidget):
    _SLIDER_SCALE = 100  # preserve 2 decimal places on the integer slider

    def __init__(self, name: str, minimum: float, maximum: float, value: float) -> None:
        super().__init__()
        self.name = name
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(4)

        label = QLabel(name.replace("_", " ").title())
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(1.0)
        self.spin.setSuffix("°")
        self.spin.setValue(value)
        self.spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(minimum * self._SLIDER_SCALE), int(maximum * self._SLIDER_SCALE))
        self.slider.setValue(int(value * self._SLIDER_SCALE))

        layout.addWidget(label, 0, 0)
        layout.addWidget(self.spin, 0, 1)
        layout.addWidget(self.slider, 1, 0, 1, 2)

        self.spin.valueChanged.connect(self._on_spin_changed)
        self.slider.valueChanged.connect(self._on_slider_changed)

    def _on_spin_changed(self, v: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(int(v * self._SLIDER_SCALE))
        self.slider.blockSignals(False)

    def _on_slider_changed(self, v: int) -> None:
        self.spin.blockSignals(True)
        new_value = v / self._SLIDER_SCALE
        if abs(self.spin.value() - new_value) > 0.005:
            self.spin.setValue(new_value)
        self.spin.blockSignals(False)

    def value(self) -> float:
        return float(self.spin.value())

    def set_value(self, value: float) -> None:
        self.spin.setValue(value)


class RobotViewport(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.values = [spec.default for spec in JOINT_SPECS]
        self.selected_item = "No selection"
        self.selection_kind = "none"
        self.robot_name = "Robot Workspace"
        self.urdf_summary: RobotModel | None = None
        self.view_mode = "skeleton"
        self.model_path = "No model loaded"
        self.backend: ViewportBackend = SkeletonViewportBackend()
        self._overlay = ViewportOverlay(title=self.robot_name, subtitle="No model loaded")
        self.setMinimumSize(900, 620)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._scene_layout = QVBoxLayout()
        self._scene_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._scene_layout)
        self._install_backend_widget()

    def _install_backend_widget(self) -> None:
        while self._scene_layout.count():
            item = self._scene_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        widget = self.backend.build_widget()
        self._scene_layout.addWidget(widget)

    def set_joint_values(self, values: Iterable[float]) -> None:
        self.values = list(values)
        self._refresh_render_frame()
        self.update()

    def set_selected_item(self, item_text: str) -> None:
        self.selected_item = item_text
        self.selection_kind = _infer_selection_kind(item_text)
        self.update()

    def set_robot_summary(self, summary: RobotModel | None) -> None:
        self.urdf_summary = summary
        if summary is not None:
            self.robot_name = summary.name
            self.view_mode = "urdf-loaded"
            self.model_path = summary.name
        self._refresh_render_frame()
        self.update()

    def set_viewport_backend(self, backend: ViewportBackend) -> None:
        self.backend = backend
        self._install_backend_widget()
        self._refresh_render_frame()
        self.update()

    def _refresh_render_frame(self) -> None:
        model = self.urdf_summary or RobotModel(name=self.robot_name)
        state = ViewState(model_path=self.model_path, selected_item=self.selected_item, selection_kind=self.selection_kind, viewport_mode=self.view_mode)
        self.backend.update_frame(model, state, list(self.values))
        self._overlay = self.backend.get_overlay()

    def set_model_path(self, path_text: str) -> None:
        self.model_path = path_text
        self._refresh_render_frame()
        self.update()

    def set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        self._refresh_render_frame()
        self.update()

    def _draw_card(self, painter: QPainter, x: int, y: int, w: int, h: int, title: str, value: str) -> None:
        painter.setBrush(QColor("#10182a"))
        painter.setPen(QPen(QColor("#30405f"), 1))
        painter.drawRoundedRect(x, y, w, h, 10, 10)
        painter.setPen(QPen(QColor("#d6def1"), 1))
        painter.drawText(x + 10, y + 18, title)
        painter.setPen(QPen(QColor("#9fb0d0"), 1))
        painter.drawText(x + 10, y + 38, value)

    def _draw_workspace_grid(self, painter: QPainter, rect) -> None:
        painter.setPen(QPen(QColor("#30405f"), 1, Qt.PenStyle.DashLine))
        step = 40
        for x in range(0, rect.width(), step):
            painter.drawLine(x, 0, x, rect.height())
        for y in range(0, rect.height(), step):
            painter.drawLine(0, y, rect.width(), y)

    def _draw_status_badge(self, painter: QPainter, x: int, y: int, text: str, active: bool = False) -> None:
        painter.setBrush(QColor("#1f2a42" if active else "#10182a"))
        painter.setPen(QPen(QColor("#5c6f95" if active else "#30405f"), 1))
        painter.drawRoundedRect(x, y, 120, 28, 14, 14)
        painter.setPen(QPen(QColor("#e6edf8"), 1))
        painter.drawText(x + 12, y + 19, text)

    def _draw_axis_widget(self, painter: QPainter, rect) -> None:
        origin_x = rect.width() - 90
        origin_y = rect.height() - 90
        painter.setPen(QPen(QColor("#91a4cb"), 3))
        painter.drawLine(origin_x, origin_y, origin_x + 48, origin_y)
        painter.setPen(QPen(QColor("#6fbf73"), 3))
        painter.drawLine(origin_x, origin_y, origin_x, origin_y - 48)
        painter.setPen(QPen(QColor("#6fa8ff"), 3))
        painter.drawLine(origin_x, origin_y, origin_x + 26, origin_y + 26)
        painter.setBrush(QColor("#10182a"))
        painter.setPen(QPen(QColor("#30405f"), 1))
        painter.drawEllipse(origin_x - 14, origin_y - 14, 28, 28)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#0a1020"))
        painter.fillRect(rect.adjusted(0, 0, 0, -rect.height() // 2), QColor(18, 26, 50))
        painter.fillRect(rect.adjusted(0, rect.height() // 2, 0, 0), QColor(9, 13, 25))

        cx = rect.width() * 0.52
        cy = rect.height() * 0.58
        base = min(rect.width(), rect.height()) * 0.12

        self._draw_workspace_grid(painter, rect)

        painter.setBrush(QColor("#cfd6e6"))
        painter.setPen(QPen(QColor("#66708b"), 2))
        painter.drawRoundedRect(int(cx - base * 0.4), int(cy + 15), int(base * 0.8), int(base * 0.55), 10, 10)
        painter.setBrush(QColor("#20283d"))
        painter.drawRoundedRect(int(cx - 55), int(cy - 10), 110, 24, 6, 6)
        painter.setPen(QPen(QColor("#d6def1"), 1))
        painter.drawText(18, 32, self._overlay.title)
        painter.drawText(18, 56, self._overlay.subtitle)
        painter.drawText(18, 80, f"Selected: {self.selected_item}")

        active = self.view_mode != "skeleton"
        self._draw_status_badge(painter, 18, 100, "3D shell", active)
        self._draw_card(painter, 18, 134, 220, 58, "Joint count", f"{len(self.values)} axis controls")
        self._draw_card(painter, 18, 202, 220, 58, "Selection", self.selected_item)
        self._draw_card(painter, 18, 270, 220, 58, "View mode", self.view_mode)
        self._draw_card(painter, 18, 338, 220, 58, "Model", self.model_path)
        if self.urdf_summary is not None:
            self._draw_card(
                painter,
                18,
                406,
                220,
                84,
                "URDF model",
                f"{self.urdf_summary.name}: {len(self.urdf_summary.links)} links / {len(self.urdf_summary.joints)} joints",
            )
        self._draw_axis_widget(painter, rect)
        painter.drawText(18, rect.height() - 22, "Viewport shell prepared for real 3D backend")


class ConsoleCard(QFrame):
    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        label = QLabel(title)
        label.setObjectName("CardTitle")
        text = QLabel(body)
        text.setWordWrap(True)
        text.setObjectName("CardBody")
        layout.addWidget(label)
        layout.addWidget(text)


class OverviewBanner(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Banner")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        self.title = QLabel("Robot URDF Studio")
        self.title.setObjectName("BannerTitle")
        self.subtitle = QLabel("Industrial workbench for robot models, device control, and packaging-ready Win11 delivery.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setObjectName("BannerSubtitle")
        chip_row = QHBoxLayout()
        self.chips: list[QLabel] = []
        for text in ["URDF import", "link/joint tree", "device console", "exe-ready path"]:
            chip = QLabel(text)
            chip.setObjectName("BannerChip")
            self.chips.append(chip)
            chip_row.addWidget(chip)
        chip_row.addStretch(1)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(chip_row)


class DetailPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Selection details")
        title.setObjectName("CardTitle")
        self.summary = QLabel("Select a project tree node or URDF item")
        self.summary.setObjectName("CardBody")
        self.summary.setWordWrap(True)

        self.fields = QTreeWidget()
        self.fields.setHeaderHidden(True)
        self.fields.setMinimumHeight(180)

        self.action_hint = QLabel("Tip: use the tree to inspect URDF structure and workspace resources.")
        self.action_hint.setObjectName("CardBody")
        self.action_hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.summary)
        layout.addWidget(self.fields)
        layout.addWidget(self.action_hint)

    def set_details(self, title: str, items: list[tuple[str, str]]) -> None:
        self.summary.setText(title)
        self.fields.clear()
        for key, value in items:
            self.fields.addTopLevelItem(QTreeWidgetItem([f"{key}: {value}"]))


class ResourcePanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("URDF resources")
        title.setObjectName("CardTitle")
        self.summary = QLabel("No URDF loaded yet")
        self.summary.setObjectName("CardBody")
        self.summary.setWordWrap(True)
        self.resource_list = QListWidget()
        self.resource_list.setMinimumHeight(120)
        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderHidden(True)
        self.structure_tree.setMinimumHeight(160)
        layout.addWidget(title)
        layout.addWidget(self.summary)
        layout.addWidget(self.resource_list)
        layout.addWidget(QLabel("URDF structure"))
        layout.addWidget(self.structure_tree)

    def set_resources(self, items: list[str], summary: str) -> None:
        self.summary.setText(summary)
        self.resource_list.clear()
        self.resource_list.addItems(items)

    def set_structure(self, summary: UrdfModelSummary | None) -> None:
        self.structure_tree.clear()
        if summary is None:
            self.structure_tree.addTopLevelItem(QTreeWidgetItem(["No parsed URDF structure"]))
            return
        robot_item = QTreeWidgetItem([f"robot: {summary.robot_name}"])
        links_item = QTreeWidgetItem([f"links ({len(summary.links)})"])
        for link in summary.links:
            links_item.addChild(QTreeWidgetItem([link]))
        joints_item = QTreeWidgetItem([f"joints ({len(summary.joints)})"])
        for name, parent, child in summary.joints:
            joints_item.addChild(QTreeWidgetItem([f"{name}: {parent} -> {child}"]))
        robot_item.addChild(links_item)
        robot_item.addChild(joints_item)
        if summary.warnings:
            warn_item = QTreeWidgetItem([f"warnings ({len(summary.warnings)})"])
            for warning in summary.warnings:
                warn_item.addChild(QTreeWidgetItem([warning]))
            robot_item.addChild(warn_item)
        robot_item.setExpanded(True)
        self.structure_tree.addTopLevelItem(robot_item)


class WorkspaceShell(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.log_sink: QTextEdit | None = None
        self.connection_state = QLabel("Disconnected")
        self.project_root: Path | None = None
        self.loaded_urdf: Path | None = None
        self.current_model = RobotModel()
        self.current_urdf_summary: UrdfModelSummary | None = None
        self.selection_state = SelectionState()
        self.workflow_snapshot = build_workflow_status_snapshot()

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self.left_panel = self._build_left_panel()
        self.viewport = RobotViewport()
        self.right_panel = self._build_right_panel()

        root.addWidget(self.left_panel, 0)
        root.addWidget(self.viewport, 1)
        root.addWidget(self.right_panel, 0)

        self._apply_style()
        self._sync_view()
        self._append_log("Workspace ready")

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setMaximumWidth(400)
        panel.setMinimumWidth(350)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        banner = OverviewBanner()
        layout.addWidget(banner)

        layout.addWidget(ConsoleCard("Project", "Load robot assets, recent workspaces, and build targets."))

        recent_label = QLabel("Recent projects")
        recent_label.setObjectName("SectionTitle")
        layout.addWidget(recent_label)
        self.recent_list = QListWidget()
        self.recent_list.addItems(RECENT_PROJECTS)
        self.recent_list.itemDoubleClicked.connect(self._open_recent_project)
        layout.addWidget(self.recent_list)

        browse_row = QHBoxLayout()
        self.workspace_path = QLineEdit()
        self.workspace_path.setPlaceholderText("Workspace path or project folder")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_workspace)
        browse_row.addWidget(self.workspace_path, 1)
        browse_row.addWidget(browse_btn)
        layout.addLayout(browse_row)

        open_btn = QPushButton("Open workspace")
        open_btn.clicked.connect(self._open_workspace)
        layout.addWidget(open_btn)

        tree_label = QLabel("Project tree")
        tree_label.setObjectName("SectionTitle")
        layout.addWidget(tree_label)
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.project_tree.itemClicked.connect(self._tree_clicked)
        layout.addWidget(self.project_tree, 1)

        self.detail_panel = DetailPanel()
        layout.addWidget(self.detail_panel)
        self.resource_panel = ResourcePanel()
        layout.addWidget(self.resource_panel)

        urdf_row = QHBoxLayout()
        self.urdf_path = QLineEdit()
        self.urdf_path.setPlaceholderText("URDF or Xacro file")
        import_btn = QPushButton("Import URDF")
        import_btn.clicked.connect(self.import_urdf)
        urdf_row.addWidget(self.urdf_path, 1)
        urdf_row.addWidget(import_btn)
        layout.addLayout(urdf_row)

        layout.addWidget(ConsoleCard("Device links", "Serial, CAN, and TCP adapters with status-aware connection handling."))
        layout.addWidget(ConsoleCard("Workflow", "Planning, logs, flashing, and test execution panels."))
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setMaximumWidth(450)
        panel.setMinimumWidth(380)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QLabel("Joint control")
        header.setObjectName("PanelTitle")
        layout.addWidget(header)

        self.joints: list[JointSlider] = []
        for spec in JOINT_SPECS:
            js = JointSlider(spec.name, spec.minimum, spec.maximum, spec.default)
            js.spin.valueChanged.connect(self._sync_view)
            layout.addWidget(js)
            self.joints.append(js)

        row = QHBoxLayout()
        for preset in POSES:
            btn = QPushButton(preset.name)
            btn.clicked.connect(partial(self.apply_pose, preset))
            row.addWidget(btn)
        layout.addLayout(row)

        actions = QHBoxLayout()
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_pose)
        copy_btn = QPushButton("Copy angles")
        copy_btn.clicked.connect(self.copy_angles)
        actions.addWidget(reset_btn)
        actions.addWidget(copy_btn)
        layout.addLayout(actions)

        toggle_btn = QPushButton("Toggle 3D / Skeleton")
        toggle_btn.clicked.connect(self._toggle_viewport_backend)
        layout.addWidget(toggle_btn)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_runtime_tab(), "Runtime")
        self.tabs.addTab(self._build_io_tab(), "I/O")
        self.tabs.addTab(self._build_tasks_tab(), "Tasks")
        layout.addWidget(self.tabs)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        return panel

    def _build_runtime_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.addWidget(ConsoleCard("Telemetry", "Joint states, temperature, supply voltage, and heartbeat monitoring."))
        layout.addWidget(ConsoleCard("Planner", "Path preview, sequence queue, and motion validation."))
        return widget

    def _build_io_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.addWidget(ConsoleCard("Serial", "Auto-detect COM ports, baud selection, reconnect, and log capture."))

        io_row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.addItems(DEVICE_PORTS)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["115200", "230400", "460800", "921600"])
        io_row.addWidget(self.port_combo, 1)
        io_row.addWidget(self.baud_combo, 1)
        layout.addLayout(io_row)

        conn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.connect_btn.clicked.connect(self._connect_device)
        self.disconnect_btn.clicked.connect(self._disconnect_device)
        self.disconnect_btn.setEnabled(False)
        conn_row.addWidget(self.connect_btn)
        conn_row.addWidget(self.disconnect_btn)
        layout.addLayout(conn_row)

        self.connection_state.setObjectName("ConnectionState")
        layout.addWidget(self.connection_state)

        self.command_box = QLineEdit()
        self.command_box.setPlaceholderText("Send command to controller, e.g. ping")
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._send_command)
        layout.addWidget(self.command_box)
        layout.addWidget(send_btn)

        self.telemetry_title = QLabel("Telemetry state")
        self.telemetry_title.setObjectName("SectionTitle")
        layout.addWidget(self.telemetry_title)
        self.telemetry_box = QTextEdit()
        self.telemetry_box.setReadOnly(True)
        self.telemetry_box.setMaximumHeight(140)
        layout.addWidget(self.telemetry_box)

        layout.addWidget(ConsoleCard("Network", "TCP/UDP bridge support for embedded controllers and simulators."))
        layout.addWidget(ConsoleCard("Flash", "Future hook for firmware upload and device-specific tooling."))
        self._refresh_workflow_panels()
        return widget

    def _build_tasks_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.addWidget(ConsoleCard("Quick actions", "Open workspace, import URDF, connect device, run checks."))
        layout.addWidget(ConsoleCard("Logs", "Timestamped event stream designed for copy/paste debugging."))
        layout.addWidget(ConsoleCard("Status", "Keep operators aware of connection health, errors, and motion state."))
        return widget

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #SidePanel {
                background: rgba(10, 14, 24, 0.94);
                border: 1px solid rgba(122, 139, 174, 0.24);
                border-radius: 20px;
            }
            #Banner {
                background: linear-gradient(135deg, rgba(30, 40, 64, 0.96), rgba(14, 19, 31, 0.98));
                border: 1px solid rgba(154, 168, 198, 0.18);
                border-radius: 18px;
            }
            #BannerTitle {
                font-size: 21px;
                font-weight: 800;
                letter-spacing: 0.4px;
            }
            #BannerSubtitle {
                color: #b3bfd8;
            }
            #BannerChip {
                background: rgba(39, 50, 74, 0.95);
                color: #dce5f7;
                border: 1px solid rgba(130, 146, 182, 0.25);
                border-radius: 999px;
                padding: 4px 10px;
            }
            #SectionTitle, #MutedLabel, #CardBody {
                color: #a7b2c9;
            }
            #ConnectionState {
                color: #d6def1;
                font-weight: 600;
                padding: 4px 0;
            }
            #Card {
                background: rgba(20, 28, 44, 0.94);
                border-radius: 14px;
            }
            #CardTitle {
                font-weight: 700;
            }
            QListWidget, QLineEdit, QComboBox, QTextEdit, QTreeWidget {
                background: #0f1626;
                border: 1px solid #394867;
                border-radius: 10px;
                padding: 7px 9px;
                color: #e6edf8;
            }
            QPushButton {
                background: #1f2a42;
                border: 1px solid #40506f;
                border-radius: 10px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #293753;
            }
            QPushButton:disabled {
                color: #66708b;
                background: #151d2e;
            }
            QSlider::groove:horizontal {
                border-radius: 4px;
                height: 6px;
                background: #27324a;
            }
            QSlider::handle:horizontal {
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
                background: #d8e1f5;
            }
            QDoubleSpinBox {
                background: #11182a;
                border: 1px solid #394867;
                border-radius: 8px;
                padding: 4px 8px;
                min-width: 72px;
            }
            QTabWidget::pane {
                border: 1px solid #394867;
                border-radius: 10px;
                top: -1px;
            }
            QTabBar::tab {
                background: #1b2437;
                padding: 8px 14px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #27324a;
            }
            """
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 140))
        self.viewport.setGraphicsEffect(shadow)

    def set_log_sink(self, sink: QTextEdit) -> None:
        self.log_sink = sink

    def browse_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select workspace folder")
        if path:
            self.workspace_path.setText(path)
            self._set_project_root(Path(path))
            self._append_log(f"Workspace selected: {path}")

    def import_urdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Import URDF", str(self.project_root or Path.cwd()), "Robot files (*.urdf *.xacro *.xml)")
        if not file_path:
            self._append_log("URDF import cancelled")
            return
        path = Path(file_path)
        self.urdf_path.setText(str(path))
        self.loaded_urdf = path
        issues = self._validate_urdf_path(path)
        summary = self._parse_urdf(path)
        self._render_resource_report(path, issues, summary)
        if summary is None:
            self._append_log(f"URDF parsing failed for: {path.name}")
        elif issues:
            self._append_log(f"URDF validation warnings: {'; '.join(issues)}")
            self._append_log(f"URDF parsed: {summary.robot_name} ({len(summary.links)} links, {len(summary.joints)} joints)")
        else:
            self._append_log(f"URDF imported successfully: {path.name}")
            self._append_log(f"URDF parsed: {summary.robot_name} ({len(summary.links)} links, {len(summary.joints)} joints)")

    def _validate_urdf_path(self, path: Path) -> list[str]:
        issues: list[str] = []
        if not path.exists():
            issues.append("file not found")
            return issues
        if path.suffix.lower() not in URDF_HINTS:
            issues.append("unexpected file extension")
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            issues.append("unable to read file")
            return issues
        if "<robot" not in text:
            issues.append("missing <robot> root tag")
        if "link" not in text:
            issues.append("no link definitions found")
        if "joint" not in text:
            issues.append("no joint definitions found")
        return issues

    def _parse_urdf(self, path: Path) -> UrdfModelSummary | None:
        try:
            parser = ET.XMLParser(target=ET.TreeBuilder())
            parser.entity = {}
            tree = ET.parse(path, parser=parser)
            root = tree.getroot()
        except ET.ParseError as exc:
            self._append_log(f"URDF XML parse error: {exc}")
            return None
        except OSError as exc:
            self._append_log(f"URDF read error: {exc}")
            return None

        robot_name = root.attrib.get("name", path.stem)
        links = [node.attrib.get("name", "unnamed_link") for node in root.findall(".//link")]
        joints: list[tuple[str, str, str]] = []
        warnings: list[str] = []
        for joint in root.findall(".//joint"):
            name = joint.attrib.get("name", "unnamed_joint")
            parent = joint.find("parent")
            child = joint.find("child")
            parent_name = parent.attrib.get("link", "unknown") if parent is not None else "unknown"
            child_name = child.attrib.get("link", "unknown") if child is not None else "unknown"
            joints.append((name, parent_name, child_name))
            if parent is None or child is None:
                warnings.append(f"joint '{name}' is missing parent or child link")

        if not links:
            warnings.append("no link definitions were parsed")
        if not joints:
            warnings.append("no joint definitions were parsed")

        return UrdfModelSummary(robot_name=robot_name, links=links, joints=joints, warnings=warnings)

    def _render_resource_report(self, path: Path, issues: list[str], summary: UrdfModelSummary | None) -> None:
        related = self._collect_related_resources(path)
        status = "Validation passed" if not issues else "Validation warnings: " + ", ".join(issues)
        model = self._convert_summary_to_model(summary)
        self.current_model = model
        self.current_urdf_summary = summary
        self.resource_panel.set_resources(related, status)
        self.resource_panel.set_structure(summary)
        self.viewport.set_robot_summary(model)
        self.viewport.set_model_path(str(path))
        self._sync_project_tree_with_urdf(summary)
        if summary is not None:
            self._update_details_from_tree(f"URDF: {summary.robot_name}")

    def _convert_summary_to_model(self, summary: UrdfModelSummary | None) -> RobotModel:
        if summary is None:
            return RobotModel()
        return RobotModel(
            name=summary.robot_name,
            links=[RobotLink(name=link) for link in summary.links],
            joints=[RobotJoint(name=name, parent=parent, child=child) for name, parent, child in summary.joints],
            warnings=list(summary.warnings),
        )

    def _collect_related_resources(self, path: Path) -> list[str]:
        root = path.parent
        resources: list[str] = [path.name]
        for candidate in sorted(root.iterdir() if root.exists() else []):
            if candidate == path:
                continue
            if candidate.is_dir() and candidate.name.lower() in PROJECT_HINTS:
                resources.append(f"{candidate.name}/")
                continue
            if candidate.suffix.lower() in RESOURCE_SUFFIXES or candidate.name.lower().endswith(".urdf"):
                resources.append(candidate.name)
        if len(resources) == 1:
            resources.append("No adjacent robot assets found")
        return resources

    def _sync_project_tree_with_urdf(self, summary: UrdfModelSummary | None) -> None:
        if summary is None:
            return
        top = self.project_tree.topLevelItem(0)
        if top is None:
            top = QTreeWidgetItem([self.project_root.name if self.project_root else "project"])
            self.project_tree.addTopLevelItem(top)
        urdf_root = self._find_or_create_child(top, f"URDF: {summary.robot_name}")
        urdf_root.takeChildren()
        links_branch = QTreeWidgetItem([f"links ({len(summary.links)})"])
        for link in summary.links:
            links_branch.addChild(QTreeWidgetItem([link]))
        joints_branch = QTreeWidgetItem([f"joints ({len(summary.joints)})"])
        for name, parent, child in summary.joints:
            joints_branch.addChild(QTreeWidgetItem([f"{name}: {parent} -> {child}"]))
        urdf_root.addChild(links_branch)
        urdf_root.addChild(joints_branch)
        if summary.warnings:
            warn_branch = QTreeWidgetItem([f"warnings ({len(summary.warnings)})"])
            for warning in summary.warnings:
                warn_branch.addChild(QTreeWidgetItem([warning]))
            urdf_root.addChild(warn_branch)
        urdf_root.setExpanded(True)
        top.setExpanded(True)

    def _find_or_create_child(self, parent: QTreeWidgetItem, label: str) -> QTreeWidgetItem:
        for idx in range(parent.childCount()):
            child = parent.child(idx)
            if child.text(0) == label:
                return child
        child = QTreeWidgetItem([label])
        parent.addChild(child)
        return child

    def _open_recent_project(self, item) -> None:
        self.workspace_path.setText(item.text())
        self._append_log(f"Recent project opened: {item.text()}")

    def _open_workspace(self) -> None:
        text = self.workspace_path.text().strip()
        if not text:
            self._append_log("Open workspace requested with empty path")
            return
        path = Path(text)
        if path.exists():
            self._set_project_root(path)
            self._append_log(f"Workspace opened: {path}")
        else:
            self._append_log(f"Workspace path not found: {path}")

    def _set_project_root(self, path: Path) -> None:
        self.project_root = path
        self._populate_project_tree(path)
        if self.current_urdf_summary is not None:
            self._sync_project_tree_with_urdf(self.current_urdf_summary)

    def _populate_project_tree(self, root: Path) -> None:
        self.project_tree.clear()
        root_item = QTreeWidgetItem([root.name or str(root)])
        self.project_tree.addTopLevelItem(root_item)
        for folder_name in PROJECT_HINTS:
            folder = root / folder_name
            label = f"{folder_name}/"
            child = QTreeWidgetItem([label])
            root_item.addChild(child)
            if folder_name == "models":
                for model_name in ["urdf", "mesh", "cad"]:
                    child.addChild(QTreeWidgetItem([f"{model_name}/"]))
            if folder_name == "firmware":
                for fw in ["bootloader", "application", "tools"]:
                    child.addChild(QTreeWidgetItem([f"{fw}/"]))
        if self.loaded_urdf is not None:
            root_item.addChild(QTreeWidgetItem([f"URDF: {self.loaded_urdf.stem}"]))
        root_item.setExpanded(True)

    def _tree_clicked(self, item: QTreeWidgetItem) -> None:
        text = item.text(0)
        kind = self._infer_tree_kind(text)
        self.selection_state = SelectionState(label=text, kind=kind)
        self.viewport.set_selected_item(text)
        self._update_details_from_tree(text)
        self._append_log(f"Tree item selected: {text}")

    def _infer_tree_kind(self, text: str) -> str:
        return _infer_selection_kind(text)

    def _update_details_from_tree(self, text: str) -> None:
        details = [("Selected item", text), ("Category", self.selection_state.kind)]
        if self.current_model is not None:
            details.append(("Loaded robot", self.current_model.name))
            details.append(("Link count", str(self.current_model.link_count())))
            details.append(("Joint count", str(self.current_model.joint_count())))
            if self.current_model.warnings:
                details.append(("Warnings", str(len(self.current_model.warnings))))
        self.detail_panel.set_details("Live selection details", details)

    def _toggle_viewport_backend(self) -> None:
        if isinstance(self.viewport.backend, SkeletonViewportBackend):
            self.viewport.set_viewport_backend(FakeThreeDViewportBackend())
            self.viewport.set_view_mode("3d-shell")
            self._append_log("Viewport backend: 3D placeholder")
        else:
            self.viewport.set_viewport_backend(SkeletonViewportBackend())
            self.viewport.set_view_mode("skeleton")
            self._append_log("Viewport backend: 2D skeleton")

    def _sync_view(self) -> None:
        self.viewport.set_joint_values(j.value() for j in self.joints)
        self.viewport.set_selected_item(self.selection_state.label)

    def _refresh_workflow_panels(self) -> None:
        previous = self.workflow_snapshot
        self.workflow_snapshot = build_workflow_status_snapshot(
            connection_state=self.workflow_snapshot.device.connection_state,
            last_command=self.workflow_snapshot.device.last_command,
            last_error=self.workflow_snapshot.device.last_error,
        )
        delta = compare_snapshots(previous, self.workflow_snapshot)
        self.connection_state.setText(self.workflow_snapshot.device.connection_state)
        self.telemetry_box.setPlainText("\n".join(self.workflow_snapshot.telemetry_lines() + ([f"delta={delta.note}"] if delta.note else [])))
        if delta.note:
            self._append_log(f"Workflow snapshot updated: {delta.note}")

    def apply_pose(self, pose: PosePreset) -> None:
        for js, value in zip(self.joints, pose.values):
            js.set_value(value)
        self._sync_view()
        self._append_log(f"Pose applied: {pose.name}")

    def reset_pose(self) -> None:
        self.apply_pose(POSES[0])

    def copy_angles(self) -> None:
        text = ", ".join(f"{js.name}={js.value():.1f}" for js in self.joints)
        QApplication.clipboard().setText(text)
        self._append_log("Joint angles copied to clipboard")

    def _connect_device(self) -> None:
        port = self.port_combo.currentText()
        baud = self.baud_combo.currentText()
        self.connection_state.setText(f"Connected to {port} @ {baud}")
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.workflow_snapshot = build_workflow_status_snapshot(connection_state="Connected", last_command=self.workflow_snapshot.device.last_command)
        self._refresh_workflow_panels()
        self._append_log(f"Connected to {port} @ {baud}")

    def _disconnect_device(self) -> None:
        self.connection_state.setText("Disconnected")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.workflow_snapshot = build_workflow_status_snapshot(connection_state="Disconnected", last_command=self.workflow_snapshot.device.last_command)
        self._refresh_workflow_panels()
        self._append_log("Device disconnected")

    def _send_command(self) -> None:
        command = self.command_box.text().strip()
        if not command:
            self._append_log("Send command requested with empty payload")
            return
        self.workflow_snapshot = build_workflow_status_snapshot(
            connection_state=self.workflow_snapshot.device.connection_state,
            last_command=command,
            last_error=self.workflow_snapshot.device.last_error,
        )
        self._refresh_workflow_panels()
        self._append_log(f"TX > {command}")
        self.command_box.clear()

    def _append_log(self, message: str) -> None:
        if self.log_sink is not None:
            self.log_sink.append(message)
