from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class CollapsiblePanel(QFrame):
    """Compact collapsible status bar shared by CAD overview and workflow panels."""

    def __init__(self, toggle_label: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setMaximumHeight(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.toggle = QPushButton(f"{toggle_label} ▸")
        self.toggle.setObjectName("CompactToggle")
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self._toggle_expanded)

        self._toggle_label = toggle_label
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

    def _toggle_expanded(self, expanded: bool) -> None:
        self.setMaximumHeight(68 if expanded else 40)
        self.toggle.setText(f"{self._toggle_label} ▾" if expanded else f"{self._toggle_label} ▸")
        self.details.setVisible(expanded)

    def refresh(self) -> None:
        raise NotImplementedError
