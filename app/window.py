from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QMainWindow, QStatusBar, QTextEdit, QWidget, QVBoxLayout

from ui.cad_panel import CadOverviewPanel
from ui.cad_workspace import CadWorkflowPanel
from ui.shell import WorkspaceShell


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Robot URDF Studio")
        self.resize(1600, 980)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.workspace = WorkspaceShell()
        self.cad_overview = CadOverviewPanel()
        self.cad_workflow = CadWorkflowPanel()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(180)
        self.log_view.setPlaceholderText("Event log and telemetry output")

        self.workspace.set_log_sink(self.log_view)
        layout.addWidget(self.cad_overview, 0)
        layout.addWidget(self.cad_workflow, 0)
        layout.addWidget(self.workspace, 1)
        layout.addWidget(self.log_view, 0)
        self.setCentralWidget(central)

        status = QStatusBar()
        status.showMessage("Ready")
        self.setStatusBar(status)
        self.setFont(QFont("Segoe UI", 10))
