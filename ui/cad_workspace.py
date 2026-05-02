from __future__ import annotations

from cad.interop import build_interop_snapshot
from ui.collapsible import CollapsiblePanel


class CadWorkflowPanel(CollapsiblePanel):
    def __init__(self) -> None:
        super().__init__("Workflow")
        self.refresh()

    def refresh(self) -> None:
        snapshot = build_interop_snapshot()
        self.status.setText(f"v{snapshot.cad_version} · {snapshot.cad_readiness} · {snapshot.cad_writer}")
        self.details.setText(f"art={snapshot.cad_artifacts} · written={snapshot.cad_written_artifacts} · topo={snapshot.cad_topology_nodes} · desc={snapshot.cad_artifact_descriptors}")
