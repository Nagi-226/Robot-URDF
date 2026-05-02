"""Centralised i18n manager for Robot URDF Studio.

Provides en/zh translations and a language-changed signal so all UI surfaces
can react without restarting the application.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


_LANG_EN: dict[str, str] = {}
_LANG_ZH: dict[str, str] = {}


def _build_dicts() -> None:
    """Populate both language dictionaries from a single definition table."""
    table: list[tuple[str, str, str]] = [
        # ── Top-nav button labels ──
        ("nav.file",          "File",          "文件"),
        ("nav.file.tip",      "File",          "文件"),
        ("nav.cad",           "CAD",           "CAD"),
        ("nav.cad.tip",       "CAD",           "CAD"),
        ("nav.device",        "Device",        "设备"),
        ("nav.device.tip",    "Device",        "设备"),
        ("nav.view",          "View",          "视图"),
        ("nav.view.tip",      "View",          "视图"),
        ("nav.run",           "Run",           "运行"),
        ("nav.run.tip",       "Run",           "运行"),
        ("nav.logs",          "Logs",          "日志"),
        ("nav.logs.tip",      "Logs",          "日志"),
        ("nav.about",         "About",         "关于"),
        ("nav.about.tip",     "About",         "关于"),

        # ── File menu ──
        ("file.open_workspace",   "Open Workspace",   "打开工作区"),
        ("file.import_urdf",      "Import URDF",      "导入 URDF"),
        ("file.export_state",     "Export State",     "导出当前状态"),

        # ── CAD menu ──
        ("cad.overview",           "CAD Overview",      "CAD 概览"),
        ("cad.workflow",           "CAD Workflow",      "CAD 工作流"),
        ("cad.workflow_status",    "Workflow Status",   "工作流状态"),
        ("cad.topology_summary",   "Topology Summary",  "拓扑摘要"),
        ("cad.edit_demo",          "Edit Demo",         "编辑演示"),
        ("cad.view_handles",       "View Handles",      "查看句柄"),
        ("cad.refresh_samples",    "Refresh Samples",   "刷新示例"),

        # ── Device menu ──
        ("device.connection_fmt",   "Connection: {}",        "连接: {}"),
        ("device.health_fmt",       "Health: {}",            "健康: {}"),
        ("device.console",          "Device Console",        "设备控制台"),
        ("device.connect_settings", "Connection Settings",   "连接设置"),
        ("device.send_command",     "Send Command",          "命令发送"),
        ("device.reconnect",        "Reconnect",             "重连"),

        # ── View menu ──
        ("view.toggle_2d3d",    "Toggle 2D / 3D",   "切换 2D / 3D"),
        ("view.reset_view",     "Reset View",       "重置视图"),
        ("view.language",       "Language",         "语言"),
        ("view.language_en",    "English",          "English"),
        ("view.language_zh",    "中文",             "中文"),

        # ── Run menu ──
        ("run.checks",           "Run Checks",       "运行检查"),
        ("run.refresh_snapshot", "Refresh Snapshot", "刷新快照"),

        # ── Logs menu ──
        ("logs.telemetry_fmt",   "Telemetry: {}",     "遥测: {}"),
        ("logs.health_status",   "Health Status",     "健康状态"),
        ("logs.power_temp",      "Power & Temp",      "电源与温度"),
        ("logs.open_logs",       "Open Logs",         "打开日志"),
        ("logs.clear_output",    "Clear Output",      "清空输出"),

        # ── About menu ──
        ("about.project_info",  "Project Info",  "项目说明"),
        ("about.version_info",  "Version Info",  "版本信息"),

        # ── General ──
        ("stub", "Not yet implemented", "尚未实现"),

        # ── Connection states ──
        ("conn.connected",      "Connected",             "已连接"),
        ("conn.connected_to",   "Connected to {} @ {}",  "已连接 {} @ {}"),
        ("conn.disconnected",   "Disconnected",          "未连接"),
        ("conn.connecting",     "Connecting",            "连接中"),
        ("conn.fault",          "Fault",                 "故障"),

        # ── Health labels ──
        ("health.active",    "active",    "活跃"),
        ("health.idle",      "idle",      "空闲"),
        ("health.nominal",   "nominal",   "正常"),
        ("health.degraded",  "degraded",  "降级"),
        ("health.offline",   "offline",   "离线"),
        ("health.fault",     "fault",     "故障"),

        # ── Shell UI ──
        ("shell.joint_control",     "Joint control",      "关节控制"),
        ("shell.runtime",           "Runtime",            "运行时"),
        ("shell.io",                "I/O",                "I/O"),
        ("shell.tasks",             "Tasks",              "任务"),
        ("shell.home",              "Home",               "Home"),
        ("shell.reach",             "Reach",              "Reach"),
        ("shell.inspect",           "Inspect",            "Inspect"),
        ("shell.reset",             "Reset",              "重置"),
        ("shell.copy",              "Copy",               "复制"),
        ("shell.toggle_2d3d",       "2D / 3D",            "2D / 3D"),
        ("shell.selection_details", "Selection details",  "选择详情"),
        ("shell.select_hint",       "Select a project tree node or URDF item", "选择一个项目树节点或 URDF 项"),
        ("shell.tip_tree",          "Tip: use the tree to inspect URDF structure and workspace resources.", "提示：使用树形结构查看 URDF 结构和工作区资源。"),
        ("shell.urdf_resources",    "URDF resources",     "URDF 资源"),
        ("shell.no_urdf",           "No URDF loaded yet", "尚未加载 URDF"),
        ("shell.urdf_structure",    "URDF structure",     "URDF 结构"),
        ("shell.project",           "Project",            "项目"),
        ("shell.project_body",      "Load assets, workspace folders, and build targets.", "加载资源、工作区文件夹和构建目标。"),
        ("shell.recent",            "Recent",             "最近"),
        ("shell.tree",              "Tree",               "树形"),
        ("shell.browse",            "Browse",             "浏览"),
        ("shell.open",              "Open",               "打开"),
        ("shell.import",            "Import",             "导入"),
        ("shell.workspace_path",    "Workspace path",     "工作区路径"),
        ("shell.urdf_xacro",        "URDF / Xacro",       "URDF / Xacro"),
        ("shell.links_card",        "Links",              "连接"),
        ("shell.links_body",        "Serial, CAN, and TCP status.", "串口、CAN 和 TCP 状态。"),
        ("shell.workflow_card",     "Workflow",           "工作流"),
        ("shell.workflow_body",     "Planning, logs, flashing, and test execution.", "规划、日志、烧录和测试执行。"),
        ("shell.telemetry_card",    "Telemetry",          "遥测"),
        ("shell.telemetry_body",    "Joint states, temperature, voltage, heartbeat.", "关节状态、温度、电压、心跳。"),
        ("shell.planner_card",      "Planner",            "规划器"),
        ("shell.planner_body",      "Path preview, queue, and motion validation.", "路径预览、队列和运动验证。"),
        ("shell.serial_card",       "Serial",             "串口"),
        ("shell.serial_body",       "COM ports, baud rate, reconnect, and log capture.", "COM 端口、波特率、重连和日志捕获。"),
        ("shell.connect",           "Connect",            "连接"),
        ("shell.disconnect",        "Disconnect",         "断开"),
        ("shell.send",              "Send",               "发送"),
        ("shell.send_placeholder",  "Send command, e.g. ping", "发送命令，例如 ping"),
        ("shell.telemetry_title",   "Telemetry",          "遥测"),
        ("shell.network_card",      "Network",            "网络"),
        ("shell.network_body",      "TCP/UDP bridge support for controllers and simulators.", "控制器和模拟器的 TCP/UDP 桥接支持。"),
        ("shell.flash_card",        "Flash",              "烧录"),
        ("shell.flash_body",        "Firmware upload and device tooling hooks.", "固件上传和设备工具钩子。"),
        ("shell.actions_card",      "Actions",            "操作"),
        ("shell.actions_body",      "Open workspace, import URDF, connect device, run checks.", "打开工作区、导入 URDF、连接设备、运行检查。"),
        ("shell.logs_card",         "Logs",               "日志"),
        ("shell.logs_body",         "Timestamped event stream for debugging.", "带时间戳的事件流，用于调试。"),
        ("shell.status_card",       "Status",             "状态"),
        ("shell.status_body",       "Connection health, errors, and motion state.", "连接健康、错误和运动状态。"),
        ("shell.temp",              "Temp",               "温度"),
        ("shell.voltage",           "Voltage",            "电压"),
        ("shell.health",            "Health",             "健康"),
        ("shell.warnings_label",    "Warnings",           "警告"),
        ("shell.heartbeat",         "Heartbeat",          "心跳"),
        ("shell.motion",            "Motion",             "运动"),
        ("shell.warnings_none",     "none",               "无"),
        ("shell.warnings_active",   "{} active",          "{} 个活跃"),
        ("shell.workspace_ready",     "Workspace ready",    "工作区就绪"),
        ("shell.3d_shell",            "3D shell",           "3D 外壳"),
        ("shell.joint_count",         "Joint count",        "关节数"),
        ("shell.axis_controls",       "axis controls",      "轴控制"),
        ("shell.selection",           "Selection",          "选择"),
        ("shell.view_mode",           "View mode",          "视图模式"),
        ("shell.model",               "Model",              "模型"),
        ("shell.urdf_model",          "URDF model",         "URDF 模型"),
        ("shell.links_unit",          "links",              "个链接"),
        ("shell.joints_unit",         "joints",             "个关节"),
        ("shell.viewport_footer",     "Viewport shell prepared for real 3D backend", "视口外壳已为真实 3D 后端准备就绪"),
        ("shell.no_parsed_urdf",      "No parsed URDF structure", "无解析的 URDF 结构"),
        ("shell.validation_passed",   "Validation passed",  "验证通过"),
        ("shell.validation_warnings", "Validation warnings: {}", "验证警告: {}"),
        ("shell.detail_selected_item","Selected item",      "选中项"),
        ("shell.detail_category",     "Category",           "类别"),
        ("shell.detail_loaded_robot", "Loaded robot",       "已加载机器人"),
        ("shell.detail_link_count",   "Link count",         "链接数"),
        ("shell.detail_joint_count",  "Joint count",        "关节数"),
        ("shell.detail_warnings",     "Warnings",           "警告数"),
        ("shell.detail_live_selection","Live selection details", "实时选择详情"),
        ("shell.pick_selection_title",  "3D pick selection",   "3D 拾取选择"),
        ("shell.pick_kind",             "3D pick",             "3D 拾取"),
        ("shell.pick_part",             "Part",                "部件"),
        ("shell.pick_face_index",       "Face index",          "面索引"),
        ("shell.pick_edge_index",       "Edge index",          "边索引"),
        ("shell.pick_vertex_index",     "Vertex index",        "顶点索引"),
        ("shell.pick_face_point",       "Face point",          "面坐标"),
        ("shell.pick_edge_point",       "Edge point",          "边坐标"),
        ("shell.pick_vertex_point",     "Vertex point",        "顶点坐标"),

        # ── Robot model / summary ──
        ("robot.robot",         "robot",          "机器人"),
        ("robot.links",         "links",          "链接"),
        ("robot.joints",        "joints",         "关节"),
        ("robot.warnings",      "warnings",       "警告"),
        ("robot.no_model",      "No model loaded","无模型加载"),
        ("robot.workspace_name","Robot Workspace","机器人工作区"),
        ("robot.no_selection",  "No selection",   "无选择"),

        # ── App chrome ──
        ("app.title",           "Robot URDF Studio",    "Robot URDF Studio"),
        ("app.subtitle",        "Industrial workbench for robot models, device control, and packaging-ready Win11 delivery.",
         "机器人模型、设备控制和 Win11 打包交付的工业级工作台。"),
        ("app.ready",           "Ready",                "就绪"),
        ("app.stub_action",     "Not yet implemented: {}", "尚未实现: {}"),
        ("app.log_placeholder", "Event log and telemetry output", "事件日志和遥测输出"),

        # ── Tags ──
        ("tag.urdf",      "URDF",       "URDF"),
        ("tag.cad",       "CAD",        "CAD"),
        ("tag.io",        "I/O",        "I/O"),
        ("tag.packaging", "packaging",  "打包"),

        # ── Log messages ──
        ("log.joint_panel_rebuilt",     "Joint panel rebuilt: {} joints",             "关节面板已重建: {} 个关节"),
        ("log.workspace_selected",      "Workspace selected: {}",                     "已选择工作区: {}"),
        ("log.urdf_import_cancelled",   "URDF import cancelled",                      "URDF 导入已取消"),
        ("log.urdf_parse_failed",       "URDF parsing failed for: {}",                "URDF 解析失败: {}"),
        ("log.urdf_validation_warnings","URDF validation warnings: {}",               "URDF 验证警告: {}"),
        ("log.urdf_parsed",             "URDF parsed: {} ({} links, {} joints)",      "URDF 已解析: {} ({} 个链接, {} 个关节)"),
        ("log.urdf_import_ok",          "URDF imported successfully: {}",             "URDF 导入成功: {}"),
        ("log.recent_project_opened",   "Recent project opened: {}",                  "最近项目已打开: {}"),
        ("log.open_workspace_empty",    "Open workspace requested with empty path",   "打开工作区请求路径为空"),
        ("log.workspace_opened",        "Workspace opened: {}",                       "工作区已打开: {}"),
        ("log.workspace_not_found",     "Workspace path not found: {}",               "工作区路径未找到: {}"),
        ("log.connected_to",            "Connected to {} @ {}",                       "已连接 {} @ {}"),
        ("log.device_disconnected",     "Device disconnected",                        "设备已断开"),
        ("log.send_empty",              "Send command requested with empty payload",  "发送命令请求载荷为空"),
        ("log.tx_command",              "TX > {}",                                    "发送 > {}"),
        ("log.tree_item_selected",      "Tree item selected: {}",                     "树节点已选中: {}"),
        ("log.viewport_3d",             "Viewport backend: 3D mesh",                  "视口后端: 3D 网格"),
        ("log.viewport_2d",             "Viewport backend: 2D skeleton",              "视口后端: 2D 骨架"),
        ("log.viewport_reset",          "Viewport camera reset",                      "视口相机已重置"),
        ("log.viewport_screenshot_saved", "Viewport screenshot saved: {}",            "视口截图已保存: {}"),
        ("log.viewport_screenshot_failed", "Viewport screenshot failed: {}",          "视口截图失败: {}"),
        ("log.snapshot_updated",        "Workflow snapshot updated: {}",              "工作流快照已更新: {}"),
        ("log.pose_mismatch",           "Pose '{}' has {} values but {} joints exist — skipping", "姿态 '{}' 有 {} 个值但存在 {} 个关节 — 跳过"),
        ("log.pose_applied",            "Pose applied: {}",                           "姿态已应用: {}"),
        ("log.no_home_preset",          "No 'Home' preset found",                     "未找到 'Home' 预设"),
        ("log.angles_copied",           "Joint angles copied to clipboard",           "关节角度已复制到剪贴板"),
    ]

    for key, en, zh in table:
        _LANG_EN[key] = en
        _LANG_ZH[key] = zh


_build_dicts()


class I18nManager(QObject):
    """Singleton-ish language manager that emits ``language_changed``."""

    language_changed = Signal(str)  # carries the new lang code "en" | "zh"

    _instance: I18nManager | None = None

    def __init__(self) -> None:
        if I18nManager._instance is not None:
            raise RuntimeError("Use I18nManager.instance()")
        super().__init__()
        self._lang: str = "zh"
        I18nManager._instance = self

    @classmethod
    def instance(cls) -> I18nManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def lang(self) -> str:
        return self._lang

    def set_language(self, lang: str) -> None:
        if lang not in ("en", "zh"):
            return
        if lang == self._lang:
            return
        self._lang = lang
        self.language_changed.emit(lang)

    def tr(self, key: str, *fmt_args: object) -> str:
        """Return the translation for *key* in the current language.

        If *fmt_args* are provided the result is formatted with them.
        """
        if self._lang == "zh":
            text = _LANG_ZH.get(key)
        else:
            text = _LANG_EN.get(key)
        if text is None:
            text = key
        if fmt_args:
            text = text.format(*fmt_args)
        return text


# Module-level convenience so callers don't need instance() every time.
_i18n = I18nManager.instance()


def tr(key: str, *fmt_args: object) -> str:
    return _i18n.tr(key, *fmt_args)


def set_language(lang: str) -> None:
    _i18n.set_language(lang)


def current_lang() -> str:
    return _i18n.lang
