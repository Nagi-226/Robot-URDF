from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from cad.ui_bridge import get_ui_bridge


class CadOverviewPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("CAD runway overview")
        title.setObjectName("CardTitle")
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setObjectName("CardBody")
        self.report = QLabel("")
        self.report.setWordWrap(True)
        self.report.setObjectName("CardBody")
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setObjectName("CardBody")
        self.scope = QLabel("Scope: overview only, no control actions")
        self.scope.setWordWrap(True)
        self.scope.setObjectName("CardBody")

        layout.addWidget(title)
        layout.addWidget(self.summary)
        layout.addWidget(self.report)
        layout.addWidget(self.status)
        layout.addWidget(self.scope)
        self.refresh()

    def refresh(self) -> None:
        bridge = get_ui_bridge()
        lines = bridge.as_lines()
        self.summary.setText("\n".join(lines))
        self.report.setText(bridge.report.splitlines()[0] if bridge.report else "")
        self.status.setText(
            f"version={bridge.version} | ready={bridge.ready} | readiness={bridge.readiness} | writer={bridge.writer} | artifacts={bridge.artifact_count} | written={bridge.written_artifact_count} | edits={bridge.edit_summary} | descriptors={bridge.artifact_descriptor_count} | topology_nodes={bridge.topology_nodes}"
        )
