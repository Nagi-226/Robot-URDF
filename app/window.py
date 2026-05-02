from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QMainWindow, QStatusBar, QTextEdit, QWidget, QVBoxLayout

from config import CONFIG
from i18n import tr
from ui.cad_panel import CadOverviewPanel
from ui.cad_workspace import CadWorkflowPanel
from ui.shell import WorkspaceShell
from ui.top_nav import TopNavigationBar


VERSION = "v0.7.0"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.resize(CONFIG.window_width, CONFIG.window_height)
        self.setMinimumSize(CONFIG.window_min_width, CONFIG.window_min_height)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.top_nav = TopNavigationBar()
        self.workspace = WorkspaceShell()
        self.cad_overview = CadOverviewPanel()
        self.cad_workflow = CadWorkflowPanel()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(CONFIG.log_max_height)
        self.log_view.setPlaceholderText(tr("app.log_placeholder"))

        self.workspace.set_log_sink(self.log_view)

        self._wire_top_nav()

        layout.addWidget(self.top_nav, 0)
        layout.addWidget(self.cad_overview, 0)
        layout.addWidget(self.cad_workflow, 0)
        layout.addWidget(self.workspace, 1)
        layout.addWidget(self.log_view, 0)
        self.setCentralWidget(central)

        status = QStatusBar()
        status.showMessage(tr("app.ready"))
        self.setStatusBar(status)
        self.setFont(QFont("Segoe UI", 10))

    def _wire_top_nav(self) -> None:
        nav = self.top_nav
        nav.browse_workspace.connect(self.workspace.browse_workspace)
        nav.import_urdf.connect(self.workspace.import_urdf)
        nav.export_state.connect(self.workspace.export_viewport_screenshot)
        nav.toggle_viewport.connect(self.workspace._toggle_viewport_backend)
        nav.reset_view.connect(self.workspace.reset_view)
        nav.camera_preset_requested.connect(self.workspace.set_camera_preset)
        nav.wireframe_toggled.connect(self.workspace.set_wireframe)
        nav.refresh_snapshot.connect(self.workspace._refresh_workflow_panels)
        nav.clear_logs.connect(self.log_view.clear)
        nav.show_version.connect(self._show_version)
        nav.undo_cad_edit.connect(self.workspace.undo_last_cad_edit)
        nav.redo_cad_edit.connect(self.workspace.redo_last_cad_edit)

    def _stub_action(self, name: str) -> None:
        self.log_view.append(tr("app.stub_action", name))

    def _show_version(self) -> None:
        self.log_view.append(f"Robot URDF Studio — {VERSION}  (Windows 11, PySide6, dark engineering cockpit)")
