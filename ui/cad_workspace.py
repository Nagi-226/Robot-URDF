from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from cad.interop import build_interop_snapshot


class CadWorkflowPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setMaximumHeight(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.toggle = QPushButton("Workflow ▸")
        self.toggle.setObjectName("CompactToggle")
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self._toggle_expanded)

        self.summary = QLabel("")
        self.summary.setObjectName("CardBody")
        self.summary.setWordWrap(False)

        row.addWidget(self.toggle, 0)
        row.addWidget(self.summary, 1)
        layout.addLayout(row)

        self.details = QLabel("")
        self.details.setObjectName("CardBody")
        self.details.setWordWrap(False)
        self.details.setVisible(False)
        layout.addWidget(self.details)

        self.refresh()

    def _toggle_expanded(self, expanded: bool) -> None:
        self.setMaximumHeight(68 if expanded else 40)
        self.toggle.setText("Workflow ▾" if expanded else "Workflow ▸")
        self.details.setVisible(expanded)

    def refresh(self) -> None:
        snapshot = build_interop_snapshot()
        self.summary.setText(f"v{snapshot.cad_version} · {snapshot.cad_readiness} · {snapshot.cad_writer}")
        self.details.setText(f"art={snapshot.cad_artifacts} · written={snapshot.cad_written_artifacts} · topo={snapshot.cad_topology_nodes} · desc={snapshot.cad_artifact_descriptors}")
