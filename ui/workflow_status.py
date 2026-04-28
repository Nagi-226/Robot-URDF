from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeviceConsoleStatus:
    connection_state: str
    port: str
    baud_rate: str
    command_ready: bool
    last_command: str = ""
    last_error: str = ""


@dataclass(frozen=True)
class TelemetryStatus:
    heartbeat: str
    joint_count: int
    motion_state: str
    temperature_c: float
    supply_voltage_v: float
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowStatusSnapshot:
    device: DeviceConsoleStatus
    telemetry: TelemetryStatus

    @property
    def telemetry_health(self) -> str:
        if self.device.connection_state != "Connected":
            return "offline"
        if self.telemetry.warnings:
            return "degraded"
        return "nominal"

    def device_lines(self) -> list[str]:
        lines = [
            f"connection={self.device.connection_state}",
            f"port={self.device.port}",
            f"baud={self.device.baud_rate}",
            f"command_ready={self.device.command_ready}",
        ]
        if self.device.last_command:
            lines.append(f"last_command={self.device.last_command}")
        if self.device.last_error:
            lines.append(f"last_error={self.device.last_error}")
        return lines

    def telemetry_lines(self) -> list[str]:
        lines = [
            f"heartbeat={self.telemetry.heartbeat}",
            f"joint_count={self.telemetry.joint_count}",
            f"motion_state={self.telemetry.motion_state}",
            f"temperature_c={self.telemetry.temperature_c:.1f}",
            f"supply_voltage_v={self.telemetry.supply_voltage_v:.1f}",
            f"health={self.telemetry_health}",
        ]
        if self.telemetry.warnings:
            lines.append("warnings=" + "; ".join(self.telemetry.warnings))
        return lines


@dataclass(frozen=True)
class WorkflowStatusDelta:
    connection_changed: bool
    telemetry_changed: bool
    note: str = ""


def build_workflow_status_snapshot(*, connection_state: str = "Disconnected", last_command: str = "", last_error: str = "") -> WorkflowStatusSnapshot:
    device = DeviceConsoleStatus(
        connection_state=connection_state,
        port="COM3",
        baud_rate="115200",
        command_ready=connection_state == "Connected",
        last_command=last_command,
        last_error=last_error,
    )
    telemetry = TelemetryStatus(
        heartbeat="idle" if connection_state != "Connected" else "alive",
        joint_count=6,
        motion_state="standby" if connection_state != "Connected" else "ready",
        temperature_c=31.5,
        supply_voltage_v=24.0,
        warnings=["telemetry bridge not connected"] if connection_state != "Connected" else [],
    )
    return WorkflowStatusSnapshot(device=device, telemetry=telemetry)


def compare_snapshots(previous: WorkflowStatusSnapshot, current: WorkflowStatusSnapshot) -> WorkflowStatusDelta:
    connection_changed = previous.device.connection_state != current.device.connection_state
    telemetry_changed = previous.telemetry != current.telemetry
    note_parts: list[str] = []
    if connection_changed:
        note_parts.append(f"connection: {previous.device.connection_state} -> {current.device.connection_state}")
    if telemetry_changed:
        note_parts.append("telemetry payload updated")
    return WorkflowStatusDelta(connection_changed=connection_changed, telemetry_changed=telemetry_changed, note="; ".join(note_parts))
