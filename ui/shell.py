from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Iterable

from PySide6.QtCore import Qt, QTimer, Signal
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
    QScrollArea,
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

from robot_model import JointSpec, RobotModel, ViewState
from rendering import MeshViewportBackend, SkeletonViewportBackend, ViewportBackend, ViewportOverlay
from config import CONFIG
from i18n import tr
from studio_io.urdf_io import collect_related_resources, convert_summary_to_model, parse_urdf_file, validate_urdf_path
from ui.workflow_status import ConnectionState, build_workflow_status_snapshot, compare_snapshots
from robot.animation import interpolate_joint_values
from cad.edit_bridge import EditAction, EditHistory, PickToHandleMapping
from cad.sample_parts import build_base_mount_part, build_wrist_link_part
from app.theme import ThemeManager


RECENT_PROJECTS = ["AtlasArm / production-cell-01", "DeltaBot / calibration-suite", "FieldRig / embedded-testbench"]
DEVICE_PORTS = ["COM3", "COM5", "COM8", "USB0"]
PROJECT_HINTS = ["models", "assets", "configs", "logs", "firmware", "urdf"]


def _infer_selection_kind(text: str) -> str:
    lowered = text.lower()
    if lowered.startswith("urdf:"):
        return "urdf"
    if lowered.endswith("/"):
        return "folder"
    kind_map = {
        "links": "links",
        "joints": "joints",
        "warnings": "warnings",
    }
    for prefix, kind in kind_map.items():
        if lowered.startswith(prefix):
            return kind
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
    joint_specs: list[JointSpec] | None = None
    warnings: list[str] | None = None

    def __post_init__(self):
        if self.warnings is None:
            object.__setattr__(self, "warnings", [])
        if self.joint_specs is None:
            object.__setattr__(self, "joint_specs", [])


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
    _SLIDER_SCALE = 100

    def __init__(self, name: str, minimum: float, maximum: float, value: float) -> None:
        super().__init__()
        self.name = name
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(4)

        label = QLabel(name.replace("_", " ").title())
        label.setMinimumWidth(90)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(1.0)
        self.spin.setSuffix("°")
        self.spin.setValue(value)
        self.spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin.setMinimumWidth(78)

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
    pick_changed = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.values = [spec.default for spec in JOINT_SPECS]
        self.selected_item = tr("robot.no_selection")
        self.selection_kind = "none"
        self.robot_name = tr("robot.workspace_name")
        self.urdf_summary: RobotModel | None = None
        self.view_mode = "skeleton"
        self.model_path = tr("robot.no_model")
        self.backend: ViewportBackend = SkeletonViewportBackend()
        self._overlay = ViewportOverlay(title=self.robot_name, subtitle=tr("robot.no_model"))
        self._fps = 0.0
        self._fps_visible = True
        self._last_frame_time = time.perf_counter()
        self.setMinimumSize(CONFIG.viewport_min_width, CONFIG.viewport_min_height)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._scene_layout = QVBoxLayout()
        self._scene_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._scene_layout)
        self._install_backend_widget()
        self.hud = ViewportHudOverlay(self)
        self.hud.raise_()

    def _install_backend_widget(self) -> None:
        while self._scene_layout.count():
            item = self._scene_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        widget = self.backend.build_widget()
        if hasattr(widget, "selection_changed"):
            widget.selection_changed.connect(self.pick_changed.emit)
        self._scene_layout.addWidget(widget)
        if hasattr(self, "hud"):
            self.hud.raise_()

    def set_joint_values(self, values: Iterable[float]) -> None:
        self.values = list(values)
        self._refresh_render_frame()
        self.update()

    def set_selected_item(self, item_text: str) -> None:
        self.selected_item = item_text
        self.selection_kind = _infer_selection_kind(item_text)
        widget = self.backend.build_widget()
        if hasattr(widget, "set_highlighted_item"):
            widget.set_highlighted_item(item_text)
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
        now = time.perf_counter()
        elapsed = max(now - self._last_frame_time, 1e-6)
        self._fps = 0.85 * self._fps + 0.15 * (1.0 / elapsed) if self._fps else 1.0 / elapsed
        self._last_frame_time = now
        model = self.urdf_summary or RobotModel(name=self.robot_name)
        state = ViewState(model_path=self.model_path, selected_item=self.selected_item, selection_kind=self.selection_kind, viewport_mode=self.view_mode)
        self.backend.update_frame(model, state, list(self.values))
        self._overlay = self.backend.get_overlay()
        if hasattr(self, "hud"):
            self.hud.update()

    def set_model_path(self, path_text: str) -> None:
        self.model_path = path_text
        self._refresh_render_frame()
        self.update()

    def set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        self._refresh_render_frame()
        self.update()

    def reset_camera(self) -> None:
        widget = self.backend.build_widget()
        if hasattr(widget, "reset_camera"):
            widget.reset_camera()
        self._refresh_render_frame()

    def set_camera_preset(self, preset_name: str) -> None:
        widget = self.backend.build_widget()
        if hasattr(widget, "set_camera_preset"):
            widget.set_camera_preset(preset_name)
        self._refresh_render_frame()

    def set_wireframe(self, enabled: bool) -> None:
        widget = self.backend.build_widget()
        if hasattr(widget, "set_wireframe"):
            widget.set_wireframe(enabled)
        self._refresh_render_frame()

    def export_screenshot(self, path: str | Path) -> bool:
        widget = self.backend.build_widget()
        if hasattr(widget, "export_screenshot"):
            return bool(widget.export_screenshot(path))
        return False

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "hud"):
            self.hud.setGeometry(self.rect())
            self.hud.raise_()

    def hud_metrics(self) -> dict[str, str]:
        model = self.urdf_summary or RobotModel(name=self.robot_name)
        mode = "orbit" if self.view_mode != "skeleton" else "skeleton"
        scale = "URDF m" if self.model_path.lower().endswith((".urdf", ".xacro", ".xml")) else "CAD mm"
        return {
            "model": model.name or tr("robot.workspace_name"),
            "joints": str(model.joint_count or len(self.values)),
            "camera": mode,
            "fps": f"{self._fps:.0f} FPS" if self._fps_visible else "",
            "scale": scale,
            "selected": self.selected_item,
        }


class ViewportHudOverlay(QWidget):
    """Transparent corner HUD that remains visible above 2D and 3D backends."""

    def __init__(self, viewport: RobotViewport) -> None:
        super().__init__(viewport)
        self.viewport = viewport
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _draw_hud_card(self, painter: QPainter, x: int, y: int, w: int, lines: list[str]) -> None:
        h = 24 + 18 * max(0, len(lines) - 1)
        painter.setBrush(QColor(10, 14, 24, 186))
        painter.setPen(QPen(QColor(95, 120, 165, 170), 1))
        painter.drawRoundedRect(x, y, w, h, 10, 10)
        for index, line in enumerate(lines):
            painter.setPen(QPen(QColor("#e6edf8" if index == 0 else "#aebbd0"), 1))
            painter.drawText(x + 10, y + 17 + index * 18, line)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        metrics = self.viewport.hud_metrics()
        rect = self.rect()

        self._draw_hud_card(
            painter, 14, 14, 260,
            [metrics["model"], f"{metrics['joints']} joints | selected: {metrics['selected']}"],
        )
        if metrics["fps"]:
            self._draw_hud_card(painter, rect.width() - 116, 14, 102, [metrics["fps"]])
        self._draw_hud_card(painter, 14, rect.height() - 52, 146, [f"camera: {metrics['camera']}"])
        self._draw_hud_card(painter, rect.width() - 126, rect.height() - 52, 112, [metrics["scale"]])

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
        self._draw_status_badge(painter, 18, 100, tr("shell.3d_shell"), active)
        self._draw_card(painter, 18, 134, 220, 58, tr("shell.joint_count"), f"{len(self.values)} {tr('shell.axis_controls')}")
        self._draw_card(painter, 18, 202, 220, 58, tr("shell.selection"), self.selected_item)
        self._draw_card(painter, 18, 270, 220, 58, tr("shell.view_mode"), self.view_mode)
        self._draw_card(painter, 18, 338, 220, 58, tr("shell.model"), self.model_path)
        if self.urdf_summary is not None:
            self._draw_card(
                painter, 18, 406, 220, 84, tr("shell.urdf_model"),
                f"{self.urdf_summary.name}: {len(self.urdf_summary.links)} {tr('shell.links_unit')} / {len(self.urdf_summary.joints)} {tr('shell.joints_unit')}",
            )
        self._draw_axis_widget(painter, rect)
        painter.drawText(18, rect.height() - 22, tr("shell.viewport_footer"))


class ConsoleCard(QFrame):
    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("CardTitle")
        text = QLabel(body)
        text.setWordWrap(True)
        text.setObjectName("CardBody")
        layout.addWidget(label)
        layout.addWidget(text)


class TelemetryCard(QFrame):
    """Structured telemetry display with color-coded status indicators."""

    _HEARTBEAT_COLORS = {"active": "#4ade80", "idle": "#facc15", "fault": "#f87171"}
    _HEALTH_COLORS = {"nominal": "#4ade80", "active": "#4ade80", "degraded": "#facc15", "offline": "#9ca3af", "fault": "#f87171", "connecting": "#60a5fa"}

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(4)

        self.heartbeat = self._add_indicator(layout, tr("shell.heartbeat"), 0, 0)
        self.temperature = self._add_label_pair(layout, tr("shell.temp"), 0, 1)
        self.motion = self._add_indicator(layout, tr("shell.motion"), 1, 0)
        self.voltage = self._add_label_pair(layout, tr("shell.voltage"), 1, 1)
        self.health = self._add_label_pair(layout, tr("shell.health"), 2, 0)
        self.warnings = self._add_label_pair(layout, tr("shell.warnings_label"), 2, 1)

    def _add_indicator(self, layout: QGridLayout, label: str, row: int, col: int) -> QLabel:
        header = QLabel(f"{label}:")
        header.setObjectName("CardBody")
        value_label = QLabel("--")
        value_label.setObjectName("CardBody")
        layout.addWidget(header, row, col * 2)
        layout.addWidget(value_label, row, col * 2 + 1)
        return value_label

    def _add_label_pair(self, layout: QGridLayout, label: str, row: int, col: int) -> QLabel:
        return self._add_indicator(layout, label, row, col)

    def refresh(self, snapshot) -> None:
        t = snapshot.telemetry
        hb_color = self._HEARTBEAT_COLORS.get(t.heartbeat, "#9ca3af")
        self.heartbeat.setText(t.heartbeat)
        self.heartbeat.setStyleSheet(f"color: {hb_color}; font-weight: 600;")

        self.temperature.setText(f"{t.temperature_c:.1f} °C")
        self.motion.setText(t.motion_state)
        mt_color = "#4ade80" if t.motion_state in {"standby", "idle", "ready"} else "#facc15"
        self.motion.setStyleSheet(f"color: {mt_color}; font-weight: 600;")

        self.voltage.setText(f"{t.supply_voltage_v:.1f} V")
        health = snapshot.telemetry_health
        hl_color = self._HEALTH_COLORS.get(health, "#9ca3af")
        self.health.setText(health)
        self.health.setStyleSheet(f"color: {hl_color}; font-weight: 600;")

        wc = len(t.warnings)
        if wc == 0:
            self.warnings.setText(tr("shell.warnings_none"))
            self.warnings.setStyleSheet("color: #4ade80;")
        else:
            self.warnings.setText(tr("shell.warnings_active", wc))
            self.warnings.setStyleSheet("color: #f87171; font-weight: 600;")


class OverviewBanner(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Banner")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        self.title = QLabel(tr("app.title"))
        self.title.setObjectName("BannerTitle")
        self.subtitle = QLabel(tr("app.subtitle"))
        self.subtitle.setWordWrap(True)
        self.subtitle.setObjectName("BannerSubtitle")
        chip_row = QHBoxLayout()
        self.chips: list[QLabel] = []
        for text in [tr("tag.urdf"), tr("tag.cad"), tr("tag.io"), tr("tag.packaging")]:
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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        title = QLabel(tr("shell.selection_details"))
        title.setObjectName("CardTitle")
        self.summary = QLabel(tr("shell.select_hint"))
        self.summary.setObjectName("CardBody")
        self.summary.setWordWrap(True)

        self.fields = QTreeWidget()
        self.fields.setHeaderHidden(True)
        self.fields.setMinimumHeight(92)

        self.action_hint = QLabel(tr("shell.tip_tree"))
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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        title = QLabel(tr("shell.urdf_resources"))
        title.setObjectName("CardTitle")
        self.summary = QLabel(tr("shell.no_urdf"))
        self.summary.setObjectName("CardBody")
        self.summary.setWordWrap(True)
        self.resource_list = QListWidget()
        self.resource_list.setMinimumHeight(74)
        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderHidden(True)
        self.structure_tree.setMinimumHeight(92)
        layout.addWidget(title)
        layout.addWidget(self.summary)
        layout.addWidget(self.resource_list)
        layout.addWidget(QLabel(tr("shell.urdf_structure")))
        layout.addWidget(self.structure_tree)

    def set_resources(self, items: list[str], summary: str) -> None:
        self.summary.setText(summary)
        self.resource_list.clear()
        self.resource_list.addItems(items)

    def set_structure(self, summary: UrdfModelSummary | None) -> None:
        self.structure_tree.clear()
        if summary is None:
            self.structure_tree.addTopLevelItem(QTreeWidgetItem([tr("shell.no_parsed_urdf")]))
            return
        robot_item = QTreeWidgetItem([f"{tr('robot.robot')}: {summary.robot_name}"])
        links_item = QTreeWidgetItem([f"{tr('robot.links')} ({len(summary.links)})"])
        for link in summary.links:
            links_item.addChild(QTreeWidgetItem([link]))
        joints_item = QTreeWidgetItem([f"{tr('robot.joints')} ({len(summary.joints)})"])
        for name, parent, child in summary.joints:
            joints_item.addChild(QTreeWidgetItem([f"{name}: {parent} -> {child}"]))
        robot_item.addChild(links_item)
        robot_item.addChild(joints_item)
        if summary.warnings:
            warn_item = QTreeWidgetItem([f"{tr('robot.warnings')} ({len(summary.warnings)})"])
            for warning in summary.warnings:
                warn_item.addChild(QTreeWidgetItem([warning]))
            robot_item.addChild(warn_item)
        robot_item.setExpanded(True)
        self.structure_tree.addTopLevelItem(robot_item)


class WorkspaceShell(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.log_sink: QTextEdit | None = None
        self.connection_state = QLabel(tr("conn.disconnected"))
        self.project_root: Path | None = None
        self.loaded_urdf: Path | None = None
        self.current_model = RobotModel()
        self.current_urdf_summary: UrdfModelSummary | None = None
        self.selection_state = SelectionState()
        self.workflow_snapshot = build_workflow_status_snapshot()
        self.edit_history = EditHistory()
        self._cad_parts = {
            "cad_base_mount": build_base_mount_part()[0],
            "cad_wrist_link": build_wrist_link_part()[0],
        }
        self._pose_timer = QTimer(self)
        self._pose_timer.setInterval(16)
        self._pose_timer.timeout.connect(self._advance_pose_animation)
        self._pose_elapsed_ms = 0.0
        self._pose_duration_ms = 840.0
        self._pose_start: dict[str, float] = {}
        self._pose_target: dict[str, float] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.left_panel = self._build_left_panel()
        self.viewport = RobotViewport()
        self.viewport.pick_changed.connect(self._update_details_from_pick)
        self.right_panel = self._build_right_panel()

        root.addWidget(self.left_panel, 0)
        root.addWidget(self.viewport, 1)
        root.addWidget(self.right_panel, 0)

        self._apply_style()
        self._sync_view()
        self._append_log(tr("shell.workspace_ready"))

    def _build_left_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("SidePanel")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(250)

        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        banner = OverviewBanner()
        layout.addWidget(banner)

        layout.addWidget(ConsoleCard(tr("shell.project"), tr("shell.project_body")))

        recent_label = QLabel(tr("shell.recent"))
        recent_label.setObjectName("SectionTitle")
        layout.addWidget(recent_label)
        self.recent_list = QListWidget()
        self.recent_list.addItems(RECENT_PROJECTS)
        self.recent_list.itemDoubleClicked.connect(self._open_recent_project)
        self.recent_list.setMinimumHeight(60)
        layout.addWidget(self.recent_list)

        browse_row = QHBoxLayout()
        self.workspace_path = QLineEdit()
        self.workspace_path.setPlaceholderText(tr("shell.workspace_path"))
        browse_btn = QPushButton(tr("shell.browse"))
        browse_btn.clicked.connect(self.browse_workspace)
        browse_row.addWidget(self.workspace_path, 1)
        browse_row.addWidget(browse_btn)
        layout.addLayout(browse_row)

        open_btn = QPushButton(tr("shell.open"))
        open_btn.clicked.connect(self._open_workspace)
        layout.addWidget(open_btn)

        tree_label = QLabel(tr("shell.tree"))
        tree_label.setObjectName("SectionTitle")
        layout.addWidget(tree_label)
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.project_tree.itemClicked.connect(self._tree_clicked)
        self.project_tree.setMinimumHeight(120)
        layout.addWidget(self.project_tree, 1)

        self.detail_panel = DetailPanel()
        layout.addWidget(self.detail_panel)
        self.resource_panel = ResourcePanel()
        layout.addWidget(self.resource_panel)

        urdf_row = QHBoxLayout()
        self.urdf_path = QLineEdit()
        self.urdf_path.setPlaceholderText(tr("shell.urdf_xacro"))
        import_btn = QPushButton(tr("shell.import"))
        import_btn.clicked.connect(self.import_urdf)
        urdf_row.addWidget(self.urdf_path, 1)
        urdf_row.addWidget(import_btn)
        layout.addLayout(urdf_row)

        layout.addWidget(ConsoleCard(tr("shell.links_card"), tr("shell.links_body")))
        layout.addWidget(ConsoleCard(tr("shell.workflow_card"), tr("shell.workflow_body")))
        layout.addItem(QSpacerItem(20, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))

        scroll.setWidget(panel)
        return scroll

    def _build_right_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("SidePanel")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(CONFIG.right_panel_min_width)
        scroll.setMaximumWidth(CONFIG.right_panel_max_width)

        panel = QFrame()
        panel.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding))
        self._right_layout = QVBoxLayout(panel)
        self._right_layout.setContentsMargins(10, 10, 10, 10)
        self._right_layout.setSpacing(8)
        scroll.setWidget(panel)

        header = QLabel(tr("shell.joint_control"))
        header.setObjectName("PanelTitle")
        self._right_layout.addWidget(header)

        self._joint_container = QWidget()
        self._joint_container_layout = QVBoxLayout(self._joint_container)
        self._joint_container_layout.setContentsMargins(0, 0, 0, 0)
        self._joint_container_layout.setSpacing(8)
        self._right_layout.addWidget(self._joint_container)

        self.joints: list[JointSlider] = []
        self._populate_default_joints()

        row = QHBoxLayout()
        for preset in POSES:
            btn = QPushButton(preset.name)
            btn.clicked.connect(lambda _=False, p=preset: self.apply_pose(p))
            row.addWidget(btn)
        self._right_layout.addLayout(row)

        actions = QHBoxLayout()
        reset_btn = QPushButton(tr("shell.reset"))
        reset_btn.clicked.connect(self.reset_pose)
        copy_btn = QPushButton(tr("shell.copy"))
        copy_btn.clicked.connect(self.copy_angles)
        actions.addWidget(reset_btn)
        actions.addWidget(copy_btn)
        self._right_layout.addLayout(actions)

        toggle_btn = QPushButton(tr("shell.toggle_2d3d"))
        toggle_btn.clicked.connect(self._toggle_viewport_backend)
        self._right_layout.addWidget(toggle_btn)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_runtime_tab(), tr("shell.runtime"))
        self.tabs.addTab(self._build_io_tab(), tr("shell.io"))
        self.tabs.addTab(self._build_tasks_tab(), tr("shell.tasks"))
        self._right_layout.addWidget(self.tabs)
        self._right_layout.addItem(QSpacerItem(20, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        return scroll

    def _build_runtime_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.addWidget(ConsoleCard(tr("shell.telemetry_card"), tr("shell.telemetry_body")))
        layout.addWidget(ConsoleCard(tr("shell.planner_card"), tr("shell.planner_body")))
        return widget

    def _build_io_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.addWidget(ConsoleCard(tr("shell.serial_card"), tr("shell.serial_body")))

        io_row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.addItems(DEVICE_PORTS)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["115200", "230400", "460800", "921600"])
        io_row.addWidget(self.port_combo, 1)
        io_row.addWidget(self.baud_combo, 1)
        layout.addLayout(io_row)

        conn_row = QHBoxLayout()
        self.connect_btn = QPushButton(tr("shell.connect"))
        self.disconnect_btn = QPushButton(tr("shell.disconnect"))
        self.connect_btn.clicked.connect(self._connect_device)
        self.disconnect_btn.clicked.connect(self._disconnect_device)
        self.disconnect_btn.setEnabled(False)
        conn_row.addWidget(self.connect_btn)
        conn_row.addWidget(self.disconnect_btn)
        layout.addLayout(conn_row)

        self.connection_state.setObjectName("ConnectionState")
        layout.addWidget(self.connection_state)

        self.command_box = QLineEdit()
        self.command_box.setPlaceholderText(tr("shell.send_placeholder"))
        send_btn = QPushButton(tr("shell.send"))
        send_btn.clicked.connect(self._send_command)
        layout.addWidget(self.command_box)
        layout.addWidget(send_btn)

        self.telemetry_title = QLabel(tr("shell.telemetry_title"))
        self.telemetry_title.setObjectName("SectionTitle")
        layout.addWidget(self.telemetry_title)
        self.telemetry_card = TelemetryCard()
        self.telemetry_card.setMaximumHeight(110)
        layout.addWidget(self.telemetry_card)

        layout.addWidget(ConsoleCard(tr("shell.network_card"), tr("shell.network_body")))
        layout.addWidget(ConsoleCard(tr("shell.flash_card"), tr("shell.flash_body")))
        self._refresh_workflow_panels()
        return widget

    def _build_tasks_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.addWidget(ConsoleCard(tr("shell.actions_card"), tr("shell.actions_body")))
        layout.addWidget(ConsoleCard(tr("shell.logs_card"), tr("shell.logs_body")))
        layout.addWidget(ConsoleCard(tr("shell.status_card"), tr("shell.status_body")))
        return widget

    def _populate_default_joints(self) -> None:
        for spec in JOINT_SPECS:
            js = JointSlider(spec.name, spec.minimum, spec.maximum, spec.default)
            js.spin.valueChanged.connect(self._sync_view)
            self._joint_container_layout.addWidget(js)
            self.joints.append(js)

    def _rebuild_joint_panel(self, joint_specs: list[JointSpec]) -> None:
        for js in self.joints:
            js.setParent(None)
        self.joints.clear()
        for spec in joint_specs:
            js = JointSlider(spec.name, spec.minimum, spec.maximum, spec.default)
            js.spin.valueChanged.connect(self._sync_view)
            self._joint_container_layout.addWidget(js)
            self.joints.append(js)
        self._append_log(tr("log.joint_panel_rebuilt", len(joint_specs)))

    def _apply_style(self) -> None:
        ThemeManager.instance().apply_to(self, persist=False)
        self.refresh_theme_chrome()

    def refresh_theme_chrome(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 125))
        self.viewport.setGraphicsEffect(shadow)

    def set_log_sink(self, sink: QTextEdit) -> None:
        self.log_sink = sink

    def browse_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select workspace folder")
        if path:
            self.workspace_path.setText(path)
            self._set_project_root(Path(path))
            self._append_log(tr("log.workspace_selected", path))

    def import_urdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Import URDF", str(self.project_root or Path.cwd()), "Robot files (*.urdf *.xacro *.xml)")
        if not file_path:
            self._append_log(tr("log.urdf_import_cancelled"))
            return
        self.load_urdf_path(Path(file_path))

    def load_urdf_path(self, path: str | Path) -> None:
        path = Path(path)
        self.urdf_path.setText(str(path))
        self.loaded_urdf = path
        issues = self._validate_urdf_path(path)
        summary = self._parse_urdf(path)
        self._render_resource_report(path, issues, summary)
        if summary is None:
            self._append_log(tr("log.urdf_parse_failed", path.name))
        elif issues:
            self._append_log(tr("log.urdf_validation_warnings", '; '.join(issues)))
            self._append_log(tr("log.urdf_parsed", summary.robot_name, len(summary.links), len(summary.joints)))
        else:
            self._append_log(tr("log.urdf_import_ok", path.name))
            self._append_log(tr("log.urdf_parsed", summary.robot_name, len(summary.links), len(summary.joints)))

    def _validate_urdf_path(self, path: Path) -> list[str]:
        return validate_urdf_path(path)

    def _parse_urdf(self, path: Path) -> UrdfModelSummary | None:
        result = parse_urdf_file(path)
        if result is None:
            self._append_log(tr("log.urdf_parse_failed", path.name))
            return None
        raw_specs = result.get("joint_specs", [])
        joint_specs = [
            JointSpec(
                s["name"], s["lower"], s["upper"], s["default"],
                origin_xyz=tuple(s.get("origin_xyz", (0.0, 0.0, 0.0))),
                origin_rpy=tuple(s.get("origin_rpy", (0.0, 0.0, 0.0))),
                axis_xyz=tuple(s.get("axis", (0.0, 0.0, 1.0))),
            )
            for s in raw_specs
        ]
        return UrdfModelSummary(
            robot_name=result["robot_name"],
            links=result["links"],
            joints=result["joints"],
            joint_specs=joint_specs,
            warnings=result.get("warnings", []),
        )

    def _render_resource_report(self, path: Path, issues: list[str], summary: UrdfModelSummary | None) -> None:
        related = self._collect_related_resources(path)
        status = tr("shell.validation_passed") if not issues else tr("shell.validation_warnings", ", ".join(issues))
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
            if summary.joint_specs:
                self._rebuild_joint_panel(summary.joint_specs)

    def _convert_summary_to_model(self, summary: UrdfModelSummary | None) -> RobotModel:
        if summary is None:
            return RobotModel()
        raw_specs = [
            {"name": s.name, "origin_xyz": s.origin_xyz, "origin_rpy": s.origin_rpy,
             "axis": s.axis_xyz}
            for s in (summary.joint_specs or [])
        ]
        result = {
            "robot_name": summary.robot_name,
            "links": summary.links,
            "joints": summary.joints,
            "joint_specs": raw_specs,
            "warnings": summary.warnings,
        }
        return convert_summary_to_model(result)

    def _collect_related_resources(self, path: Path) -> list[str]:
        return collect_related_resources(path)

    def _sync_project_tree_with_urdf(self, summary: UrdfModelSummary | None) -> None:
        if summary is None:
            return
        top = self.project_tree.topLevelItem(0)
        if top is None:
            top = QTreeWidgetItem([self.project_root.name if self.project_root else "project"])
            self.project_tree.addTopLevelItem(top)
        urdf_root = self._find_or_create_child(top, f"URDF: {summary.robot_name}")
        urdf_root.takeChildren()
        links_branch = QTreeWidgetItem([f"{tr('robot.links')} ({len(summary.links)})"])
        for link in summary.links:
            links_branch.addChild(QTreeWidgetItem([link]))
        joints_branch = QTreeWidgetItem([f"{tr('robot.joints')} ({len(summary.joints)})"])
        for name, parent, child in summary.joints:
            joints_branch.addChild(QTreeWidgetItem([f"{name}: {parent} -> {child}"]))
        urdf_root.addChild(links_branch)
        urdf_root.addChild(joints_branch)
        if summary.warnings:
            warn_branch = QTreeWidgetItem([f"{tr('robot.warnings')} ({len(summary.warnings)})"])
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
        self._append_log(tr("log.recent_project_opened", item.text()))

    def _open_workspace(self) -> None:
        text = self.workspace_path.text().strip()
        if not text:
            self._append_log(tr("log.open_workspace_empty"))
            return
        path = Path(text)
        if path.exists():
            self._set_project_root(path)
            self._append_log(tr("log.workspace_opened", path))
        else:
            self._append_log(tr("log.workspace_not_found", path))

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
        kind = _infer_selection_kind(text)
        self.selection_state = SelectionState(label=text, kind=kind)
        self.viewport.set_selected_item(text)
        self._update_details_from_tree(text)
        self._append_log(tr("log.tree_item_selected", text))

    def _update_details_from_tree(self, text: str) -> None:
        details = [(tr("shell.detail_selected_item"), text), (tr("shell.detail_category"), self.selection_state.kind)]
        if self.current_model is not None:
            details.append((tr("shell.detail_loaded_robot"), self.current_model.name))
            details.append((tr("shell.detail_link_count"), str(self.current_model.link_count)))
            details.append((tr("shell.detail_joint_count"), str(self.current_model.joint_count)))
            if self.current_model.warnings:
                details.append((tr("shell.detail_warnings"), str(len(self.current_model.warnings))))
        self.detail_panel.set_details(tr("shell.detail_live_selection"), details)

    def _update_details_from_pick(self, payload: dict) -> None:
        kind = str(payload.get("kind", "")).strip()
        if not kind:
            return
        part_id = str(payload.get("part_id", "")).strip()
        self.selection_state = SelectionState(label=f"3D {kind}: {part_id}", kind=f"3d-{kind}")
        details = [
            (tr("shell.pick_kind"), kind),
            (tr("shell.pick_part"), part_id or "-"),
        ]
        for key in ("face_index", "edge_index", "vertex_index"):
            if key in payload:
                details.append((tr(f"shell.pick_{key}"), str(payload[key])))
        for key in ("face_point", "edge_point", "vertex_point"):
            if key in payload:
                point = payload[key]
                if isinstance(point, (tuple, list)) and len(point) == 3:
                    details.append((tr(f"shell.pick_{key}"), f"{point[0]:.3f}, {point[1]:.3f}, {point[2]:.3f}"))
        if self.current_model is not None:
            details.append((tr("shell.detail_loaded_robot"), self.current_model.name))
        mapping = self._resolve_pick_cad_handle(payload)
        if mapping is not None:
            details.append(("CAD handle", mapping.handle.name))
            details.append(("CAD selector", mapping.handle.selector))
            self._record_pick_edit(mapping)
        self.detail_panel.set_details(tr("shell.pick_selection_title"), details)
        self._sync_tree_selection_from_pick(payload)
        self.viewport.set_selected_item(self.selection_state.label)
        self._append_log(tr("log.tree_item_selected", self.selection_state.label))

    def _resolve_pick_cad_handle(self, payload: dict) -> PickToHandleMapping | None:
        part_id = str(payload.get("part_id", ""))
        if part_id not in self._cad_parts:
            return None
        try:
            face_index = int(payload.get("face_index", 0))
        except (TypeError, ValueError):
            face_index = 0
        return PickToHandleMapping.resolve(part_id, face_index, self._cad_parts[part_id].handles)

    def _sync_tree_selection_from_pick(self, payload: dict) -> None:
        candidates = self._tree_candidates_from_pick(payload)
        if not candidates:
            return
        self._select_tree_item(self.project_tree, candidates)
        self._select_tree_item(self.resource_panel.structure_tree, candidates)

    @staticmethod
    def _tree_candidates_from_pick(payload: dict) -> list[str]:
        raw_values = [
            str(payload.get(key, "")).strip()
            for key in ("part_id", "face_part_id", "edge_part_id", "vertex_part_id")
        ]
        candidates: list[str] = []
        for value in raw_values:
            if not value or value in candidates:
                continue
            candidates.append(value)
            stripped = value
            for prefix in ("cad_", "link_"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):]
            if stripped and stripped not in candidates:
                candidates.append(stripped)
        return candidates

    def _select_tree_item(self, tree: QTreeWidget, candidates: list[str]) -> bool:
        root_count = tree.topLevelItemCount()
        for idx in range(root_count):
            item = self._find_tree_item(tree.topLevelItem(idx), candidates)
            if item is not None:
                tree.setCurrentItem(item)
                return True
        return False

    def _find_tree_item(self, item: QTreeWidgetItem | None, candidates: list[str]) -> QTreeWidgetItem | None:
        if item is None:
            return None
        text = item.text(0)
        for candidate in candidates:
            if candidate and (candidate == text or candidate in text or text in candidate):
                return item
        for idx in range(item.childCount()):
            found = self._find_tree_item(item.child(idx), candidates)
            if found is not None:
                return found
        return None

    def _record_pick_edit(self, mapping: PickToHandleMapping) -> None:
        action = EditAction(
            handle_name=mapping.handle.name,
            parameter="selection",
            old_value=0.0,
            new_value=float(len(self.edit_history.undo_stack) + 1),
            timestamp=time.time(),
        )
        self.edit_history.push(action)

    def undo_last_cad_edit(self) -> EditAction | None:
        action = self.edit_history.undo()
        if action is not None:
            self._sync_view()
            self._append_log(f"Undo CAD edit: {action.handle_name}.{action.parameter}")
        return action

    def redo_last_cad_edit(self) -> EditAction | None:
        action = self.edit_history.redo()
        if action is not None:
            self._sync_view()
            self._append_log(f"Redo CAD edit: {action.handle_name}.{action.parameter}")
        return action

    def _toggle_viewport_backend(self) -> None:
        if isinstance(self.viewport.backend, SkeletonViewportBackend):
            self.viewport.set_viewport_backend(MeshViewportBackend())
            self.viewport.set_view_mode("3d-shell")
            self._append_log(tr("log.viewport_3d"))
        else:
            self.viewport.set_viewport_backend(SkeletonViewportBackend())
            self.viewport.set_view_mode("skeleton")
            self._append_log(tr("log.viewport_2d"))

    def reset_view(self) -> None:
        self.viewport.reset_camera()
        self._append_log(tr("log.viewport_reset"))

    def set_camera_preset(self, preset_name: str) -> None:
        self.viewport.set_camera_preset(preset_name)
        self._append_log(f"Viewport camera preset: {preset_name}")

    def set_wireframe(self, enabled: bool) -> None:
        self.viewport.set_wireframe(enabled)
        self._append_log(f"Viewport display mode: {'wireframe' if enabled else 'solid'}")

    def export_viewport_screenshot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export viewport screenshot",
            str((self.project_root or Path.cwd()) / "viewport.png"),
            "PNG images (*.png)",
        )
        if not path:
            return
        ok = self.viewport.export_screenshot(Path(path))
        self._append_log(
            tr("log.viewport_screenshot_saved", path)
            if ok else tr("log.viewport_screenshot_failed", path)
        )

    def _sync_view(self) -> None:
        self.viewport.set_joint_values(j.value() for j in self.joints)
        self.viewport.set_selected_item(self.selection_state.label)

    def _refresh_workflow_panels(self) -> None:
        previous = self.workflow_snapshot
        self.workflow_snapshot = build_workflow_status_snapshot()
        delta = compare_snapshots(previous, self.workflow_snapshot)
        self.connection_state.setText(self.workflow_snapshot.device.connection_state)
        self.telemetry_card.refresh(self.workflow_snapshot)
        if delta.note:
            self._append_log(tr("log.snapshot_updated", delta.note))

    def apply_pose(self, pose: PosePreset) -> None:
        if len(pose.values) != len(self.joints):
            self._append_log(tr("log.pose_mismatch", pose.name, len(pose.values), len(self.joints)))
            return
        self._start_pose_animation(dict(zip((js.name for js in self.joints), pose.values)))
        self._append_log(tr("log.pose_applied", pose.name))

    def _start_pose_animation(self, target_values: dict[str, float]) -> None:
        self._pose_start = {js.name: js.value() for js in self.joints}
        self._pose_target = dict(target_values)
        self._pose_elapsed_ms = 0.0
        self._pose_timer.start()

    def _advance_pose_animation(self) -> None:
        self._pose_elapsed_ms += float(self._pose_timer.interval())
        progress = self._pose_elapsed_ms / max(self._pose_duration_ms, 1.0)
        values, done = interpolate_joint_values(
            self._pose_start,
            self._pose_target,
            progress,
        )
        for js in self.joints:
            if js.name in values:
                js.set_value(values[js.name])
        self._sync_view()
        if done or progress >= 1.0:
            self._pose_timer.stop()
            for js in self.joints:
                if js.name in self._pose_target:
                    js.set_value(self._pose_target[js.name])
            self._sync_view()

    def reset_pose(self) -> None:
        for preset in POSES:
            if preset.name == "Home":
                self.apply_pose(preset)
                return
        self._append_log(tr("log.no_home_preset"))

    def copy_angles(self) -> None:
        text = ", ".join(f"{js.name}={js.value():.1f}" for js in self.joints)
        QApplication.clipboard().setText(text)
        self._append_log(tr("log.angles_copied"))

    def _connect_device(self) -> None:
        port = self.port_combo.currentText()
        baud = self.baud_combo.currentText()
        self.connection_state.setText(tr("conn.connected_to", port, baud))
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.workflow_snapshot = build_workflow_status_snapshot(connection_state=ConnectionState.CONNECTED, last_command=self.workflow_snapshot.device.last_command)
        self._refresh_workflow_panels()
        self._append_log(tr("log.connected_to", port, baud))

    def _disconnect_device(self) -> None:
        self.connection_state.setText(tr("conn.disconnected"))
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.workflow_snapshot = build_workflow_status_snapshot(connection_state=ConnectionState.DISCONNECTED, last_command=self.workflow_snapshot.device.last_command)
        self._refresh_workflow_panels()
        self._append_log(tr("log.device_disconnected"))

    def _send_command(self) -> None:
        command = self.command_box.text().strip()
        if not command:
            self._append_log(tr("log.send_empty"))
            return
        self.workflow_snapshot = build_workflow_status_snapshot(
            connection_state=self.workflow_snapshot.device.connection_state,
            last_command=command,
            last_error=self.workflow_snapshot.device.last_error,
        )
        self._refresh_workflow_panels()
        self._append_log(tr("log.tx_command", command))
        self.command_box.clear()

    def _append_log(self, message: str) -> None:
        if self.log_sink is not None:
            self.log_sink.append(message)
