from __future__ import annotations

from dataclasses import dataclass, field


class ConnectionState:
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    FAULT = "Fault"


class ConnectionHealth:
    READY = "ready"
    BUSY = "busy"
    CONNECTING = "connecting"
    FAULT = "fault"
    OFFLINE = "offline"

    _HEALTH_MAP = {
        (ConnectionState.CONNECTED, True): READY,
        (ConnectionState.CONNECTED, False): BUSY,
        (ConnectionState.CONNECTING, False): CONNECTING,
        (ConnectionState.FAULT, False): FAULT,
    }

    @classmethod
    def derive(cls, connection_state: str, command_ready: bool) -> str:
        return cls._HEALTH_MAP.get((connection_state, command_ready), cls.OFFLINE)


class MotionState:
    STANDBY = "standby"
    IDLE = "idle"
    READY = "ready"
    ACTIVE = "active"
    HOMING = "homing"
    ALARM = "alarm"

    _HEALTHY = {STANDBY, IDLE, READY}

    @classmethod
    def is_healthy(cls, state: str) -> bool:
        return state.lower() in cls._HEALTHY


@dataclass(frozen=True)
class DeviceConsoleStatus:
    connection_state: str
    port: str
    baud_rate: str
    command_ready: bool
    last_command: str = ""
    last_error: str = ""

    @property
    def connection_health(self) -> str:
        return ConnectionHealth.derive(self.connection_state, self.command_ready)


@dataclass(frozen=True)
class TelemetryStatus:
    heartbeat: str
    joint_count: int
    motion_state: str
    temperature_c: float
    supply_voltage_v: float
    warnings: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        warning_count = len(self.warnings)
        warning_text = "no warnings" if warning_count == 0 else f"{warning_count} warning(s)"
        return f"{self.motion_state} · {self.temperature_c:.1f}°C · {self.supply_voltage_v:.1f}V · {warning_text}"


@dataclass(frozen=True)
class WorkflowStatusSnapshot:
    device: DeviceConsoleStatus
    telemetry: TelemetryStatus

    def device_lines(self) -> list[str]:
        lines = [
            f"connection={self.device.connection_state}",
            f"connection_health={self.device.connection_health}",
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
            f"summary={self.telemetry.summary}",
        ]
        if self.telemetry.warnings:
            lines.append("warnings=" + "; ".join(self.telemetry.warnings))
        return lines

    @property
    def telemetry_health(self) -> str:
        connection = self.device.connection_health
        if connection in {ConnectionHealth.OFFLINE, ConnectionHealth.FAULT, ConnectionHealth.CONNECTING}:
            return connection
        if self.telemetry.warnings:
            return "degraded"
        if not MotionState.is_healthy(self.telemetry.motion_state):
            return "active"
        return "nominal"

    def compact_summary(self) -> str:
        return f"conn={self.device.connection_health} · telem={self.telemetry_health} · motion={self.telemetry.motion_state}"


@dataclass(frozen=True)
class WorkflowStatusDelta:
    connection_changed: bool
    telemetry_changed: bool
    note: str = ""


_DEVICE_FIELDS = ("connection_state", "port", "baud_rate", "command_ready", "last_command", "last_error")
_TELEMETRY_FIELDS = ("heartbeat", "joint_count", "motion_state", "temperature_c", "supply_voltage_v", "warnings")


def build_workflow_status_snapshot(
    *,
    connection_state: str = ConnectionState.DISCONNECTED,
    last_command: str = "",
    last_error: str = "",
    heartbeat: str = "idle",
    motion_state: str = MotionState.STANDBY,
    temperature_c: float = 31.5,
    supply_voltage_v: float = 24.0,
    warnings: list[str] | None = None,
) -> WorkflowStatusSnapshot:
    connected = connection_state == ConnectionState.CONNECTED
    if warnings is None:
        warnings = ["telemetry bridge not connected"] if not connected else []
    device = DeviceConsoleStatus(
        connection_state=connection_state,
        port="COM3",
        baud_rate="115200",
        command_ready=connected,
        last_command=last_command,
        last_error=last_error,
    )
    telemetry = TelemetryStatus(
        heartbeat=heartbeat,
        joint_count=6,
        motion_state=motion_state,
        temperature_c=temperature_c,
        supply_voltage_v=supply_voltage_v,
        warnings=list(warnings),
    )
    return WorkflowStatusSnapshot(device=device, telemetry=telemetry)


def compare_snapshots(previous: WorkflowStatusSnapshot, current: WorkflowStatusSnapshot) -> WorkflowStatusDelta:
    connection_changed = previous.device.connection_state != current.device.connection_state
    telemetry_changed = previous.telemetry != current.telemetry
    note_parts: list[str] = []

    if connection_changed:
        note_parts.append(f"connection: {previous.device.connection_state} -> {current.device.connection_state}")

    if telemetry_changed:
        prev_t = previous.telemetry
        curr_t = current.telemetry
        for field in _TELEMETRY_FIELDS:
            pv = getattr(prev_t, field)
            cv = getattr(curr_t, field)
            if pv != cv:
                note_parts.append(f"{field}: {pv} -> {cv}")

    return WorkflowStatusDelta(
        connection_changed=connection_changed,
        telemetry_changed=telemetry_changed,
        note="; ".join(note_parts),
    )
