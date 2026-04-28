from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from robot.chain import KinematicChain
from robot_model import RobotModel, ViewState


@dataclass(frozen=True)
class ViewportOverlay:
    """Text metadata for the viewport chrome (title bar, info cards)."""
    title: str
    subtitle: str


# ---------------------------------------------------------------------------
# SkeletonWidget — self-contained 2D bone painter
# ---------------------------------------------------------------------------

_SKELETON_PALETTE = ("#9ba8c6", "#a6b4d2", "#b0bdd8", "#c2cfdf", "#d2ddea")
_JOINT_OUTLINE = "#d7dde9"
_JOINT_FILL = "#bfc8da"


class SkeletonWidget(QWidget):
    """Paints the 2D kinematic skeleton from a list of (x, y) positions.

    Positions are expected in *bone-space* coordinates.  The widget
    auto-scales and auto-centres the skeleton to fit its rect.
    """

    def __init__(self) -> None:
        super().__init__()
        self._positions: list[tuple[float, float]] = []
        self.setMinimumSize(400, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_positions(self, positions: list[tuple[float, float]]) -> None:
        self._positions = positions
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if len(self._positions) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # Auto-fit: find bounding box of bone-space positions
        xs = [p[0] for p in self._positions]
        ys = [p[1] for p in self._positions]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max_x - min_x or 1.0
        span_y = max_y - min_y or 1.0

        pad = 40.0
        scale_x = (rect.width() - pad * 2) / span_x
        scale_y = (rect.height() - pad * 2) / span_y
        scale = min(scale_x, scale_y)

        cx = rect.width() / 2.0
        cy = rect.height() / 2.0
        mid_x = (min_x + max_x) / 2.0
        mid_y = (min_y + max_y) / 2.0

        def tx(pos: tuple[float, float]) -> tuple[float, float]:
            return (
                cx + (pos[0] - mid_x) * scale,
                cy + (pos[1] - mid_y) * scale,
            )

        screen = [tx(p) for p in self._positions]

        # Draw bones
        for idx, (a, b) in enumerate(zip(screen, screen[1:])):
            color_idx = min(idx, len(_SKELETON_PALETTE) - 1)
            painter.setPen(QPen(QColor(_SKELETON_PALETTE[color_idx]), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))

        # Draw joint circles
        painter.setPen(QPen(QColor(_JOINT_OUTLINE), 4))
        painter.setBrush(QColor(_JOINT_FILL))
        for x, y in screen:
            painter.drawEllipse(int(x - 7), int(y - 7), 14, 14)


# ---------------------------------------------------------------------------
# Placeholder3DWidget — stub for a future QOpenGLWidget
# ---------------------------------------------------------------------------

class Placeholder3DWidget(QWidget):
    """Temporary 3D placeholder.  Replace with QOpenGLWidget later."""

    def __init__(self) -> None:
        super().__init__()
        self._joint_values: list[float] = []
        self._model_name = ""
        self.setMinimumSize(400, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_scene(self, model_name: str, joint_values: list[float]) -> None:
        self._model_name = model_name
        self._joint_values = list(joint_values)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#0d1120"))
        painter.setPen(QPen(QColor("#30405f"), 1, Qt.PenStyle.DashLine))
        for x in range(0, rect.width(), 60):
            painter.drawLine(x, 0, x, rect.height())
        for y in range(0, rect.height(), 60):
            painter.drawLine(0, y, rect.width(), y)

        painter.setPen(QPen(QColor("#d6def1"), 1))
        mid_x = rect.width() // 2
        painter.drawText(mid_x - 100, rect.height() // 2 - 14, 200, 28,
                         Qt.AlignmentFlag.AlignCenter, f"3D Preview — {self._model_name}")

        if self._joint_values:
            text = "  ".join(f"{v:.0f}°" for v in self._joint_values)
            painter.setPen(QPen(QColor("#9fb0d0"), 1))
            painter.drawText(mid_x - 180, rect.height() // 2 + 18, 360, 24,
                             Qt.AlignmentFlag.AlignCenter, text)


# ---------------------------------------------------------------------------
# ViewportBackend protocol
# ---------------------------------------------------------------------------

class ViewportBackend(Protocol):
    """Rendering backend that owns a QWidget for the robot scene.

    ``RobotViewport`` embeds this widget as a child and only paints
    viewport chrome (grid, info cards, axis widget, status bar)
    around it.
    """

    def build_widget(self) -> QWidget:
        """Create the persistent render widget.  Called once per backend."""
        ...

    def get_overlay(self) -> ViewportOverlay:
        """Return title / subtitle for the viewport chrome cards."""
        ...

    def update_frame(
        self,
        model: RobotModel,
        view_state: ViewState,
        joint_values: list[float],
    ) -> None:
        """Push updated model, UI state, and joint values to the backend."""
        ...


# ---------------------------------------------------------------------------
# SkeletonViewportBackend
# ---------------------------------------------------------------------------

class SkeletonViewportBackend:
    """2D skeleton backend.  Uses a :class:`SkeletonWidget` for rendering."""

    def __init__(self) -> None:
        self._widget: SkeletonWidget | None = None
        self._overlay = ViewportOverlay(title="", subtitle="")
        self._chain: KinematicChain | None = None

    def build_widget(self) -> QWidget:
        if self._widget is None:
            self._widget = SkeletonWidget()
        return self._widget

    def get_overlay(self) -> ViewportOverlay:
        return self._overlay

    def update_frame(
        self,
        model: RobotModel,
        view_state: ViewState,
        joint_values: list[float],
    ) -> None:
        self._chain = KinematicChain(model)
        pose = self._chain.compute_pose(joint_values)

        if self._widget is not None and pose.positions_3d:
            positions_2d = [(p[0], p[1]) for p in pose.positions_3d]
            self._widget.set_positions(positions_2d)

        title = model.name if model.name else "Robot Workspace"
        subtitle = f"{model.link_count()} links • {model.joint_count()} joints • mode: {view_state.viewport_mode}"
        self._overlay = ViewportOverlay(title=title, subtitle=subtitle)


# ---------------------------------------------------------------------------
# FakeThreeDViewportBackend
# ---------------------------------------------------------------------------

class FakeThreeDViewportBackend:
    """3D preview placeholder.  Swapping the widget for a real QOpenGLWidget
    is the next step after this backend interface stabilises."""

    def __init__(self) -> None:
        self._widget: Placeholder3DWidget | None = None
        self._overlay = ViewportOverlay(title="", subtitle="")

    def build_widget(self) -> QWidget:
        if self._widget is None:
            self._widget = Placeholder3DWidget()
        return self._widget

    def get_overlay(self) -> ViewportOverlay:
        return self._overlay

    def update_frame(
        self,
        model: RobotModel,
        view_state: ViewState,
        joint_values: list[float],
    ) -> None:
        if self._widget is not None:
            self._widget.set_scene(model.name, joint_values)

        title = f"{model.name} • 3D preview"
        subtitle = (
            f"{model.link_count()} links / {model.joint_count()} joints"
            f"  |  selected: {view_state.selected_item}"
            f"  |  mode: {view_state.viewport_mode}"
        )
        self._overlay = ViewportOverlay(title=title, subtitle=subtitle)
