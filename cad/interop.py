from __future__ import annotations

from dataclasses import dataclass

from .ui_bridge import CadUiBridge, get_ui_bridge


@dataclass(frozen=True)
class CadRobotInteropSnapshot:
    cad_version: str
    cad_ready: bool
    cad_readiness: str
    cad_writer: str
    cad_artifacts: int
    cad_written_artifacts: int
    cad_edit_summary: str
    cad_topology_nodes: int
    cad_artifact_descriptors: int


def build_interop_snapshot() -> CadRobotInteropSnapshot:
    bridge: CadUiBridge = get_ui_bridge()
    return CadRobotInteropSnapshot(
        cad_version=bridge.version,
        cad_ready=bridge.ready,
        cad_readiness=bridge.readiness,
        cad_writer=bridge.writer,
        cad_artifacts=int(bridge.artifact_count),
        cad_written_artifacts=int(bridge.written_artifact_count),
        cad_edit_summary=bridge.edit_summary,
        cad_topology_nodes=int(bridge.topology_nodes),
        cad_artifact_descriptors=int(bridge.artifact_descriptor_count),
    )
