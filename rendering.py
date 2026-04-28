from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
from typing import Protocol

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMatrix4x4, QPainter, QPen, QVector3D
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram
from PySide6.QtOpenGLWidgets import QOpenGLWidget
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


# ---------------------------------------------------------------------------
# Mesh3DWidget — real 3D mesh renderer via QOpenGLWidget
# ---------------------------------------------------------------------------

_VERT_SHADER = """
attribute vec3 a_position;
attribute vec3 a_normal;
varying vec3 v_normal;
varying vec3 v_world_pos;
uniform mat4 u_mvp;
uniform mat4 u_model;
void main() {
    gl_Position = u_mvp * vec4(a_position, 1.0);
    v_normal = mat3(u_model) * a_normal;
    v_world_pos = (u_model * vec4(a_position, 1.0)).xyz;
}
"""

_FRAG_SHADER = """
varying vec3 v_normal;
varying vec3 v_world_pos;
uniform vec3 u_light_dir;
uniform vec3 u_color;
uniform float u_ambient;
void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(u_light_dir);
    float diff = max(dot(N, L), 0.0);
    float lighting = u_ambient + diff * (1.0 - u_ambient);
    gl_FragColor = vec4(u_color * lighting, 1.0);
}
"""


# GL constants (PySide6 QOpenGLFunctions may not expose them as attributes)
_GL_COLOR_BUFFER_BIT = 0x00004000
_GL_DEPTH_BUFFER_BIT = 0x00000100
_GL_DEPTH_TEST = 0x0B71
_GL_CULL_FACE = 0x0B44
_GL_TRIANGLES = 0x0004
_GL_UNSIGNED_INT = 0x1405
_GL_FLOAT = 0x1406


class Mesh3DWidget(QOpenGLWidget):
    """Real 3D mesh viewer using OpenGL 2.1 / ES 2.0.

    Loads mesh files (STL, OBJ, PLY, etc.) via trimesh and renders with
    a simple diffuse-lighting shader.  Mouse-drag orbits the camera;
    scroll-wheel zooms.
    """

    _MESH_COLOR = (0.29, 0.35, 0.50)   # blue-grey engineering tone
    _AMBIENT = 0.22
    _LIGHT_DIR = (0.55, 0.75, 0.35)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model_name = ""
        self._joint_values: list[float] = []
        self._mesh_loaded = False
        self._buffers_dirty = False

        # Camera — orbit around mesh centre
        self._azimuth = 45.0
        self._elevation = 25.0
        self._distance = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._center = QVector3D(0, 0, 0)

        # Mouse
        self._last_pos = None
        self._dragging = False

        # Mesh data (set before OpenGL buffers are created)
        self._vertices: np.ndarray | None = None
        self._faces: np.ndarray | None = None
        self._flat_vertices: np.ndarray | None = None
        self._flat_normals: np.ndarray | None = None

        # GPU resources (created in initializeGL / _upload_buffers)
        self._program: QOpenGLShaderProgram | None = None
        self._vbo_vertices: QOpenGLBuffer | None = None
        self._vbo_normals: QOpenGLBuffer | None = None
        self._draw_count = 0

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Public API (mirrors Placeholder3DWidget)
    # ------------------------------------------------------------------

    def load_mesh(self, path: str) -> None:
        """Load a 3D mesh file via trimesh and prepare for rendering."""
        try:
            import trimesh
        except ImportError:
            return

        try:
            mesh = trimesh.load(path)
            if isinstance(mesh, trimesh.Scene):
                geoms = list(mesh.geometry.values())
                mesh = trimesh.util.concatenate(geoms) if geoms else None
            if mesh is None or len(mesh.vertices) == 0:
                return

            self._vertices = np.array(mesh.vertices, dtype=np.float32)
            self._faces = np.array(mesh.faces, dtype=np.uint32)

            # Vertex normals (trimesh may need scipy; fall back to our own)
            try:
                if hasattr(mesh, 'vertex_normals'):
                    vn = mesh.vertex_normals
                    if vn is not None:
                        vn = np.array(vn, dtype=np.float32)
                    else:
                        raise ValueError("no normals")
                else:
                    raise ValueError("no normals property")
            except Exception:
                vn = _compute_vertex_normals(self._vertices, self._faces)

            # Flatten per-face for glDrawArrays
            indices = self._faces.flatten().astype(np.int32)
            self._flat_vertices = self._vertices[indices].astype(np.float32)
            self._flat_normals = vn[indices].astype(np.float32)
            self._draw_count = self._faces.size

            # Auto-fit camera from original vertices
            lo = self._vertices.min(axis=0)
            hi = self._vertices.max(axis=0)
            center = (lo + hi) / 2.0
            self._center = QVector3D(float(center[0]), float(center[1]), float(center[2]))
            extent = float((hi - lo).max())
            self._distance = extent * 1.8 if extent > 0 else 1.0

            self._mesh_loaded = True
            self._buffers_dirty = True
            self.update()
        except Exception:
            pass

    def set_scene(self, model_name: str, joint_values: list[float]) -> None:
        self._model_name = model_name
        self._joint_values = list(joint_values)
        self.update()

    # ------------------------------------------------------------------
    # OpenGL lifecycle
    # ------------------------------------------------------------------

    def initializeGL(self) -> None:  # noqa: N802
        funcs = self.context().functions()
        funcs.glClearColor(0.05, 0.067, 0.125, 1.0)  # #0d1120
        funcs.glEnable(_GL_DEPTH_TEST)
        funcs.glEnable(_GL_CULL_FACE)

        self._program = QOpenGLShaderProgram()
        self._program.addShaderFromSourceCode(QOpenGLShader.Vertex, _VERT_SHADER)
        self._program.addShaderFromSourceCode(QOpenGLShader.Fragment, _FRAG_SHADER)
        self._program.link()

    def resizeGL(self, w: int, h: int) -> None:  # noqa: N802
        funcs = self.context().functions()
        funcs.glViewport(0, 0, w, h)

    def paintGL(self) -> None:  # noqa: N802
        funcs = self.context().functions()
        funcs.glClear(_GL_COLOR_BUFFER_BIT | _GL_DEPTH_BUFFER_BIT)

        if self._buffers_dirty:
            self._upload_buffers()

        if not self._mesh_loaded or self._program is None:
            return

        self._program.bind()

        # Bind vertex attributes
        self._program.enableAttributeArray('a_position')
        self._vbo_vertices.bind()
        self._program.setAttributeBuffer('a_position', _GL_FLOAT, 0, 3, 0)

        self._program.enableAttributeArray('a_normal')
        self._vbo_normals.bind()
        self._program.setAttributeBuffer('a_normal', _GL_FLOAT, 0, 3, 0)

        # Matrices
        proj = QMatrix4x4()
        proj.perspective(45.0, self.width() / max(self.height(), 1), 0.0001, 20.0)

        elev_rad = radians(self._elevation)
        az_rad = radians(self._azimuth)
        eye = QVector3D(
            self._center.x() + self._distance * cos(elev_rad) * sin(az_rad),
            self._center.y() + self._distance * sin(elev_rad),
            self._center.z() + self._distance * cos(elev_rad) * cos(az_rad),
        )
        view = QMatrix4x4()
        view.lookAt(eye, self._center, QVector3D(0, 1, 0))
        model = QMatrix4x4()
        mvp = proj * view * model

        self._program.setUniformValue('u_mvp', mvp)
        self._program.setUniformValue('u_model', model)
        light = QVector3D(*self._LIGHT_DIR).normalized()
        self._program.setUniformValue('u_light_dir', light)
        self._program.setUniformValue('u_color', QVector3D(*self._MESH_COLOR))
        # PySide6 lacks setUniformValue(str, float); use location-based call
        amb_loc = self._program.uniformLocation('u_ambient')
        self._program.setUniformValue(amb_loc, self._AMBIENT)

        funcs.glDrawArrays(_GL_TRIANGLES, 0, self._draw_count)

        self._program.disableAttributeArray('a_position')
        self._program.disableAttributeArray('a_normal')
        self._program.release()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._mesh_loaded:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#d6def1"), 1))
            rect = self.rect()
            mid_x = rect.width() // 2
            painter.drawText(mid_x - 120, rect.height() // 2 - 14, 240, 28,
                             Qt.AlignmentFlag.AlignCenter,
                             f"3D Preview — {self._model_name}")
            if self._joint_values:
                text = "  ".join(f"{v:.0f}°" for v in self._joint_values)
                painter.setPen(QPen(QColor("#9fb0d0"), 1))
                painter.drawText(mid_x - 180, rect.height() // 2 + 18, 360, 24,
                                 Qt.AlignmentFlag.AlignCenter, text)
            painter.end()

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = event.pos()
            self._dragging = True

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging and self._last_pos is not None:
            dx = event.pos().x() - self._last_pos.x()
            dy = event.pos().y() - self._last_pos.y()
            self._azimuth += dx * 0.4
            self._elevation += dy * 0.4
            self._elevation = max(-89.0, min(89.0, self._elevation))
            self._last_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._last_pos = None

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        self._distance *= (1.0 - delta * 0.0008)
        self._distance = max(0.0005, min(10.0, self._distance))
        self.update()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _upload_buffers(self) -> None:
        if self._flat_vertices is None or self._flat_normals is None:
            return

        # Release old buffers
        for buf in (self._vbo_vertices, self._vbo_normals):
            if buf is not None:
                buf.destroy()

        self._vbo_vertices = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self._vbo_vertices.create()
        self._vbo_vertices.bind()
        self._vbo_vertices.allocate(self._flat_vertices.tobytes(),
                                     self._flat_vertices.nbytes)

        self._vbo_normals = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self._vbo_normals.create()
        self._vbo_normals.bind()
        self._vbo_normals.allocate(self._flat_normals.tobytes(),
                                    self._flat_normals.nbytes)

        self._buffers_dirty = False


def _compute_vertex_normals(
    vertices: np.ndarray, faces: np.ndarray
) -> np.ndarray:
    """Compute smooth per-vertex normals from face data."""
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    fn = np.cross(v1 - v0, v2 - v1)
    length = np.linalg.norm(fn, axis=1, keepdims=True)
    length[length == 0] = 1.0
    fn = fn / length

    vn = np.zeros_like(vertices)
    for i in range(3):
        np.add.at(vn, faces[:, i], fn)

    vn_len = np.linalg.norm(vn, axis=1, keepdims=True)
    vn_len[vn_len == 0] = 1.0
    return (vn / vn_len).astype(np.float32)


# ---------------------------------------------------------------------------
# MeshViewportBackend — real 3D mesh rendering backend
# ---------------------------------------------------------------------------

_SAMPLE_MESH = Path(__file__).resolve().parent / "models" / "sample_bracket.stl"


class MeshViewportBackend:
    """Real 3D mesh viewport backend.

    Uses :class:`Mesh3DWidget` for OpenGL mesh rendering with orbit
    camera controls.  Falls back to placeholder text if no mesh file
    is found or trimesh is not installed.
    """

    def __init__(self) -> None:
        self._widget: Mesh3DWidget | None = None
        self._overlay = ViewportOverlay(title="", subtitle="")

    def build_widget(self) -> QWidget:
        if self._widget is None:
            self._widget = Mesh3DWidget()
            if _SAMPLE_MESH.is_file():
                self._widget.load_mesh(str(_SAMPLE_MESH))
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

        title = f"{model.name} • 3D mesh view"
        mesh_status = "mesh loaded" if (
            self._widget is not None and self._widget._mesh_loaded
        ) else "no mesh"
        subtitle = (
            f"{model.link_count()} links / {model.joint_count()} joints"
            f"  |  selected: {view_state.selected_item}"
            f"  |  mode: {view_state.viewport_mode}"
            f"  |  {mesh_status}"
        )
        self._overlay = ViewportOverlay(title=title, subtitle=subtitle)
