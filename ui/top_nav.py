from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QSizePolicy, QToolButton

from cad.interop import build_interop_snapshot
from ui.workflow_status import build_workflow_status_snapshot


@dataclass(frozen=True)
class NavSection:
    title: str
    subtitle: str


class TopNavigationBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TopNav")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(4)

        self.segments: list[QToolButton] = []
        self._build_segment(layout, NavSection("文件", "File"), self._file_menu())
        self._build_segment(layout, NavSection("CAD", "CAD"), self._cad_menu())
        self._build_segment(layout, NavSection("工作流", "Workflow"), self._workflow_menu())
        self._build_segment(layout, NavSection("视图", "View"), self._view_menu())
        self._build_segment(layout, NavSection("运行", "Run"), self._run_menu())
        self._build_segment(layout, NavSection("终端", "Terminal"), self._terminal_menu())
        self._build_segment(layout, NavSection("帮助", "Help"), self._help_menu())

        layout.addStretch(1)

        self.summary = QLabel("")
        self.summary.setObjectName("TopNavSummary")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.summary)
        self.refresh()

    def _build_segment(self, layout: QHBoxLayout, section: NavSection, menu: QMenu) -> None:
        btn = QToolButton()
        btn.setObjectName("TopNavButton")
        btn.setText(section.title)
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setMenu(menu)
        btn.setToolTip(section.subtitle)
        self.segments.append(btn)
        layout.addWidget(btn)

    def _file_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("打开工作区")
        menu.addAction("导入 URDF")
        menu.addSeparator()
        menu.addAction("导出当前状态")
        return menu

    def _cad_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("CAD 概览")
        workflow = menu.addMenu("CAD 工作流")
        workflow.addAction("工作流状态")
        workflow.addAction("拓扑摘要")
        edit = menu.addMenu("编辑演示")
        edit.addAction("查看句柄")
        edit.addAction("刷新示例")
        return menu

    def _workflow_menu(self) -> QMenu:
        menu = QMenu(self)
        snapshot = build_workflow_status_snapshot()
        menu.addAction(f"连接: {snapshot.device.connection_state}")
        telemetry = menu.addMenu(f"遥测: {snapshot.telemetry.heartbeat}")
        telemetry.addAction("健康状态")
        telemetry.addAction("电源与温度")
        device = menu.addMenu("设备控制台")
        device.addAction("连接设置")
        device.addAction("命令发送")
        return menu

    def _view_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("切换 2D / 3D")
        menu.addAction("重置视图")
        return menu

    def _run_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("运行检查")
        menu.addAction("刷新快照")
        return menu

    def _terminal_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("打开日志")
        menu.addAction("清空输出")
        return menu

    def _help_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("项目说明")
        menu.addAction("版本信息")
        return menu

    def refresh(self) -> None:
        cad = build_interop_snapshot()
        workflow = build_workflow_status_snapshot()
        self.summary.setText(f"CAD {cad.cad_version} · {cad.cad_readiness} | {workflow.compact_summary()}")
