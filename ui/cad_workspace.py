from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from cad.interop import build_interop_snapshot


class CadWorkflowPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("CAD workflow link")
        title.setObjectName("CardTitle")
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setObjectName("CardBody")
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.details.setObjectName("CardBody")
        self.telemetry_hint = QLabel("")
        self.telemetry_hint.setWordWrap(True)
        self.telemetry_hint.setObjectName("CardBody")

        layout.addWidget(title)
        layout.addWidget(self.summary)
        layout.addWidget(self.details)
        layout.addWidget(self.telemetry_hint)
        self.refresh()

    def refresh(self) -> None:
        snapshot = build_interop_snapshot()
        self.summary.setText(
            f"CAD version {snapshot.cad_version} | readiness={snapshot.cad_readiness} | writer={snapshot.cad_writer} | artifacts={snapshot.cad_artifacts} | written={snapshot.cad_written_artifacts}"
        )
        self.details.setText(
            f"edit summary={snapshot.cad_edit_summary} | topology nodes={snapshot.cad_topology_nodes} | descriptors={snapshot.cad_artifact_descriptors}"
        )
        self.telemetry_hint.setText("Telemetry bridge uses a stable snapshot model before direct device integration.")
