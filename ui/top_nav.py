from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QSizePolicy, QToolButton

from app.theme import ThemeManager
from cad.interop import build_interop_snapshot
from i18n import tr, current_lang, I18nManager
from ui.workflow_status import build_workflow_status_snapshot


@dataclass(frozen=True)
class NavSection:
    title_key: str
    tip_key: str


NAV_SECTIONS: list[NavSection] = [
    NavSection("nav.file",   "nav.file.tip"),
    NavSection("nav.cad",    "nav.cad.tip"),
    NavSection("nav.device", "nav.device.tip"),
    NavSection("nav.view",   "nav.view.tip"),
    NavSection("nav.run",    "nav.run.tip"),
    NavSection("nav.logs",   "nav.logs.tip"),
    NavSection("nav.about",  "nav.about.tip"),
]


_ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
_SECTION_ICONS = {
    "nav.file": "file-open",
    "nav.cad": "solid",
    "nav.device": "device-connect",
    "nav.view": "view-3d",
    "nav.run": "robot-play",
    "nav.logs": "file-export",
    "nav.about": "robot-home",
}
_ACTION_ICONS = {
    "open": "file-open",
    "save": "file-save",
    "export": "file-export",
    "2d": "view-2d",
    "3d": "view-3d",
    "reset": "view-reset",
    "wireframe": "wireframe",
    "solid": "solid",
    "connect": "device-connect",
    "disconnect": "device-disconnect",
    "send": "device-send",
    "home": "robot-home",
    "play": "robot-play",
    "pause": "robot-pause",
}


def _icon(name: str) -> QIcon:
    path = _ICON_DIR / f"{name}.svg"
    return QIcon(str(path)) if path.is_file() else QIcon()


class TopNavigationBar(QFrame):
    browse_workspace = Signal()
    import_urdf = Signal()
    export_state = Signal()
    toggle_viewport = Signal()
    reset_view = Signal()
    camera_preset_requested = Signal(str)
    wireframe_toggled = Signal(bool)
    refresh_snapshot = Signal()
    clear_logs = Signal()
    show_version = Signal()
    undo_cad_edit = Signal()
    redo_cad_edit = Signal()
    theme_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TopNav")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 5, 6, 5)
        self._layout.setSpacing(4)

        self._buttons: list[QToolButton] = []
        self._menus: dict[str, QMenu] = {}
        self._build_all()

        self._layout.addStretch(1)

        self.summary = QLabel("")
        self.summary.setObjectName("TopNavSummary")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._layout.addWidget(self.summary)

        I18nManager.instance().language_changed.connect(self._on_language_changed)
        self.refresh()

    # ------------------------------------------------------------------
    # Build / rebuild
    # ------------------------------------------------------------------

    def _build_all(self) -> None:
        """Full rebuild of buttons and menus (called on init + language switch)."""
        # Clear existing buttons
        for btn in self._buttons:
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()
        self._menus.clear()

        for section in NAV_SECTIONS:
            menu = self._build_menu_for(section.title_key)
            self._menus[section.title_key] = menu
            btn = QToolButton()
            btn.setObjectName("TopNavButton")
            btn.setText(tr(section.title_key))
            btn.setIcon(_icon(_SECTION_ICONS.get(section.title_key, "")))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            btn.setMenu(menu)
            btn.setToolTip(tr(section.tip_key))
            self._layout.insertWidget(len(self._buttons), btn)
            self._buttons.append(btn)

    def _build_menu_for(self, title_key: str) -> QMenu:
        menu = QMenu(self)
        if title_key == "nav.file":
            menu.addAction(_icon("file-open"), tr("file.open_workspace")).triggered.connect(self.browse_workspace.emit)
            menu.addAction(_icon("file-open"), tr("file.import_urdf")).triggered.connect(self.import_urdf.emit)
            menu.addSeparator()
            menu.addAction(_icon("file-export"), tr("file.export_state")).triggered.connect(self.export_state.emit)
        elif title_key == "nav.cad":
            self._add_stub_action(menu, tr("cad.overview"))
            workflow = menu.addMenu(tr("cad.workflow"))
            self._add_stub_action(workflow, tr("cad.workflow_status"))
            self._add_stub_action(workflow, tr("cad.topology_summary"))
            edit = menu.addMenu(tr("cad.edit_demo"))
            self._add_stub_action(edit, tr("cad.view_handles"))
            self._add_stub_action(edit, tr("cad.refresh_samples"))
            edit.addSeparator()
            edit.addAction("Undo CAD Edit").triggered.connect(self.undo_cad_edit.emit)
            edit.addAction("Redo CAD Edit").triggered.connect(self.redo_cad_edit.emit)
            self._cad_workflow = workflow
        elif title_key == "nav.device":
            snapshot = build_workflow_status_snapshot()
            conn_key = _conn_state_key(snapshot.device.connection_state)
            menu.addAction(tr("device.connection_fmt", tr(conn_key))).setToolTip(tr("stub"))
            health_key = "health." + snapshot.device.connection_health
            menu.addAction(tr("device.health_fmt", tr(health_key))).setToolTip(tr("stub"))
            console = menu.addMenu(tr("device.console"))
            self._add_stub_action(console, tr("device.connect_settings"))
            self._add_stub_action(console, tr("device.send_command"))
            self._add_stub_action(console, tr("device.reconnect"))
            self._device_menu = menu
        elif title_key == "nav.view":
            menu.addAction(_icon("view-3d"), tr("view.toggle_2d3d")).triggered.connect(self.toggle_viewport.emit)
            menu.addAction(_icon("view-reset"), tr("view.reset_view")).triggered.connect(self.reset_view.emit)
            camera = menu.addMenu("Camera Presets")
            for label, preset in (
                ("Isometric", "isometric"),
                ("Front", "front"),
                ("Top", "top"),
                ("Right", "right"),
            ):
                camera.addAction(_icon("view-3d"), label).triggered.connect(
                    lambda _checked=False, name=preset: self.camera_preset_requested.emit(name)
                )
            wireframe = menu.addAction(_icon("wireframe"), "Wireframe / Solid")
            wireframe.setCheckable(True)
            wireframe.triggered.connect(self.wireframe_toggled.emit)
            menu.addSeparator()
            theme_menu = menu.addMenu(tr("view.theme"))
            current_theme = ThemeManager.instance().current_theme_key
            for theme in ThemeManager.instance().available_themes():
                action = theme_menu.addAction(theme.label)
                action.setCheckable(True)
                action.setChecked(theme.key == current_theme)
                action.setToolTip(theme.description)
                action.triggered.connect(
                    lambda _checked=False, key=theme.key: self.theme_selected.emit(key)
                )
            menu.addSeparator()
            lang_menu = menu.addMenu(tr("view.language"))
            en_action = lang_menu.addAction(tr("view.language_en"))
            en_action.triggered.connect(lambda: I18nManager.instance().set_language("en"))
            zh_action = lang_menu.addAction(tr("view.language_zh"))
            zh_action.triggered.connect(lambda: I18nManager.instance().set_language("zh"))
            self._view_menu = menu
        elif title_key == "nav.run":
            self._add_stub_action(menu, tr("run.checks"))
            menu.addAction(tr("run.refresh_snapshot")).triggered.connect(self.refresh_snapshot.emit)
        elif title_key == "nav.logs":
            workflow = build_workflow_status_snapshot()
            telemetry = menu.addMenu(tr("logs.telemetry_fmt", workflow.telemetry_health))
            self._add_stub_action(telemetry, tr("logs.health_status"))
            self._add_stub_action(telemetry, tr("logs.power_temp"))
            menu.addSeparator()
            self._add_stub_action(menu, tr("logs.open_logs"))
            menu.addAction(tr("logs.clear_output")).triggered.connect(self.clear_logs.emit)
        elif title_key == "nav.about":
            self._add_stub_action(menu, tr("about.project_info"))
            menu.addAction(tr("about.version_info")).triggered.connect(self.show_version.emit)
        return menu

    # ------------------------------------------------------------------
    # Language switching
    # ------------------------------------------------------------------

    def _on_language_changed(self, lang: str) -> None:
        self._build_all()
        self.refresh()

    # ------------------------------------------------------------------
    # Refresh summary line (called periodically)
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        cad = build_interop_snapshot()
        workflow = build_workflow_status_snapshot()
        self.summary.setText(f"CAD {cad.cad_version} · {cad.cad_readiness} | {workflow.compact_summary()}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _add_stub_action(menu: QMenu, label: str) -> None:
        action = menu.addAction(label)
        action.setToolTip(tr("stub"))


def _conn_state_key(state_str: str) -> str:
    """Map a ConnectionState value string to its i18n key."""
    mapping = {
        "Connected":    "conn.connected",
        "Disconnected": "conn.disconnected",
        "Connecting":   "conn.connecting",
        "Fault":        "conn.fault",
    }
    return mapping.get(state_str, "conn.disconnected")
