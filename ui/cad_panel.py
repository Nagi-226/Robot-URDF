from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from cad.ui_bridge import get_ui_bridge


class CadOverviewPanel(QFrame):
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

        self.toggle = QPushButton("CAD ▸")
        self.toggle.setObjectName("CompactToggle")
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self._toggle_expanded)

        self.status = QLabel("")
        self.status.setObjectName("CardBody")
        self.status.setWordWrap(False)

        row.addWidget(self.toggle, 0)
        row.addWidget(self.status, 1)
        layout.addLayout(row)

        self.details = QLabel("")
        self.details.setObjectName("CardBody")
        self.details.setWordWrap(False)
        self.details.setVisible(False)
        layout.addWidget(self.details)

        self.refresh()

    def _toggle_expanded(self, expanded: bool) -> None:
        self.setMaximumHeight(68 if expanded else 40)
        self.toggle.setText("CAD ▾" if expanded else "CAD ▸")
        self.details.setVisible(expanded)

    def refresh(self) -> None:
        bridge = get_ui_bridge()
        self.status.setText(f"v{bridge.version} · {bridge.readiness} · {bridge.writer} · art={bridge.artifact_count}")
        self.details.setText(f"edit={bridge.edit_summary} · desc={bridge.artifact_descriptor_count}")
