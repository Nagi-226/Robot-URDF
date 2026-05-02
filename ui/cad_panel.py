from __future__ import annotations

from cad.ui_bridge import get_ui_bridge
from ui.collapsible import CollapsiblePanel


class CadOverviewPanel(CollapsiblePanel):
    def __init__(self) -> None:
        super().__init__("CAD")
        self.refresh()

    def refresh(self) -> None:
        bridge = get_ui_bridge()
        self.status.setText(f"v{bridge.version} · {bridge.readiness} · {bridge.writer} · art={bridge.artifact_count}")
        self.details.setText(f"edit={bridge.edit_summary} · desc={bridge.artifact_descriptor_count}")
