from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
from typing import Protocol

import numpy as np
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QMatrix4x4, QPainter, QPen, QVector3D, QVector4D
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from robot.chain import KinematicChain
from robot.fk import compute_3d_tree_fk_transforms
from robot_model import RobotModel, ViewState
from studio_io.picking import MeshPicker, PickResult


@dataclass(frozen=True)
class ViewportOverlay:
    """Text metadata for the viewport chrome (title bar, info cards)."""
    title: str
    subtitle: str


# ---------------------------------------------------------------------------
# 3D rendering infrastructure: display records, dual-scale, and lighting
# ---------------------------------------------------------------------------

@dataclass
class DisplayRecord:
    """Per-part rendering record for one link or assembly part.

    Each record tracks a single mesh part with its material and transform
    so the renderer can individually hide/show, highlight, and animate
    parts without rebuilding geometry.
    """
    part_id: str
    link_name: str
    mesh_data: object | None = None  # MeshData reference
    visible: bool = True
    opacity: float = 1.0
    color_override: tuple[float, float, float] | None = None
    world_transform: list[float] | None = None  # 16-element flat matrix


@dataclass
class SceneScale:
    """Dual-scale configuration for CAD vs robot model viewports."""
    mode: str  # "cad" | "urdf" | "robot"
    min_model_radius: float = 1.0
    min_grid_size: float = 280.0
    lighting_scope_radius: float = 140.0
    default_camera_distance: float = 400.0
    near_clip: float = 0.01
    far_clip: float = 2000.0

    @classmethod
    def for_mode(cls, mode: str) -> "SceneScale":
        if mode in ("cad", "assembly"):
            return cls(mode="cad", min_model_radius=1.0, min_grid_size=280.0,
                       lighting_scope_radius=140.0, default_camera_distance=400.0)
        if mode in ("urdf", "robot"):
            return cls(mode="urdf", min_model_radius=0.05, min_grid_size=0.5,
                       lighting_scope_radius=0.25, default_camera_distance=2.0)
        return cls(mode="default")


@dataclass
class LightingPreset:
    """Scene lighting configuration for the 3D viewport."""
    ambient_color: tuple[float, float, float] = (0.12, 0.14, 0.20)
    ambient_intensity: float = 0.35
    key_light_dir: tuple[float, float, float] = (0.55, 0.75, 0.35)
    key_light_intensity: float = 0.60
    fill_light_dir: tuple[float, float, float] = (0.20, 0.15, -0.55)
    fill_light_intensity: float = 0.20
    rim_light_dir: tuple[float, float, float] = (-0.50, 0.35, 0.30)
    rim_light_intensity: float = 0.15
    hemisphere_sky: tuple[float, float, float] = (0.35, 0.42, 0.58)
    hemisphere_ground: tuple[float, float, float] = (0.05, 0.06, 0.10)
    hemisphere_intensity: float = 0.84


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
        subtitle = f"{model.link_count} links • {model.joint_count} joints • mode: {view_state.viewport_mode}"
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
uniform vec3 u_color;
uniform vec3 u_ambient_color;
uniform float u_ambient_intensity;
uniform vec3 u_key_light_dir;
uniform float u_key_light_intensity;
uniform vec3 u_fill_light_dir;
uniform float u_fill_light_intensity;
uniform vec3 u_rim_light_dir;
uniform float u_rim_light_intensity;
uniform vec3 u_hemisphere_sky;
uniform vec3 u_hemisphere_ground;
uniform float u_hemisphere_intensity;
uniform float u_emissive;
void main() {
    vec3 N = normalize(v_normal);
    vec3 key = vec3(max(dot(N, normalize(u_key_light_dir)), 0.0)) * u_key_light_intensity;
    vec3 fill = vec3(max(dot(N, normalize(u_fill_light_dir)), 0.0)) * u_fill_light_intensity;
    vec3 rim = vec3(pow(max(dot(N, normalize(u_rim_light_dir)), 0.0), 2.0)) * u_rim_light_intensity;
    vec3 hemi = mix(u_hemisphere_ground, u_hemisphere_sky, clamp(N.y * 0.5 + 0.5, 0.0, 1.0)) * u_hemisphere_intensity;
    vec3 ambient = u_ambient_color * u_ambient_intensity;
    vec3 lighting = ambient + key + fill + rim + hemi;
    vec3 color = min(u_color * lighting + u_color * u_emissive, vec3(1.0));
    gl_FragColor = vec4(color, 1.0);
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
_GL_FRONT_AND_BACK = 0x0408
_GL_LINE = 0x1B01
_GL_FILL = 0x1B02


class Mesh3DWidget(QOpenGLWidget):
    """Real 3D mesh viewer using OpenGL 2.1 / ES 2.0.

    Loads mesh files (STL, OBJ, PLY, etc.) via trimesh and renders with
    a simple diffuse-lighting shader.  Mouse-drag orbits the camera;
    scroll-wheel zooms.
    """

    _MESH_COLOR = (0.29, 0.35, 0.50)   # blue-grey engineering tone
    _AMBIENT = 0.22
    _LIGHT_DIR = (0.55, 0.75, 0.35)
    selection_changed = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model_name = ""
        self._joint_values: list[float] = []
        self._mesh_loaded = False
        self._buffers_dirty = False
        self._display_records: list[DisplayRecord] = []
        self._part_draw_infos: list[dict] = []
        self._picker = MeshPicker()
        self._hover_pick: PickResult | None = None
        self._selected_pick: PickResult | None = None
        self._press_pos = None
        self._press_pick: PickResult | None = None
        self._lighting = LightingPreset()
        self._wireframe = False
        self._highlighted_item = ""

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

    @property
    def mesh_loaded(self) -> bool:
        return self._mesh_loaded

    # ------------------------------------------------------------------
    # Public API
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
                from studio_io.mesh_loader import _compute_normals
                vn = _compute_normals(self._vertices, self._faces)

            # Flatten per-face for glDrawArrays
            indices = self._faces.flatten().astype(np.int32)
            self._flat_vertices = self._vertices[indices].astype(np.float32)
            self._flat_normals = vn[indices].astype(np.float32)
            self._draw_count = self._faces.size
            self._install_picker_mesh(self._vertices, self._faces, vn)

            self._update_scene_bounds(self._vertices)

            self._mesh_loaded = True
            self._buffers_dirty = True
            self.update()
        except Exception:
            import traceback
            traceback.print_exc()

    def set_scene(self, model_name: str, joint_values: list[float]) -> None:
        self._model_name = model_name
        self._joint_values = list(joint_values)
        self._display_records: list[DisplayRecord] = []
        self.update()

    def set_robot_scene(
        self,
        model_name: str,
        joint_values: list[float],
        display_records: list[DisplayRecord],
    ) -> None:
        """Set the 3D scene with per-link display records and FK transforms."""
        self._model_name = model_name
        self._joint_values = list(joint_values)
        self._display_records = display_records
        self._build_part_draw_infos()
        self.update()

    def _build_part_draw_infos(self) -> None:
        """Build per-part draw info list from display records with mesh data.

        Combines all mesh data into unified VBOs for a single upload,
        then tracks per-part draw ranges and model matrices.
        """
        self._part_draw_infos = []
        records_with_mesh = [r for r in self._display_records if r.mesh_data is not None]
        if not records_with_mesh:
            return

        all_verts = []
        all_faces = []
        vertex_offset = 0
        merge_vertex_offset = 0
        merge_triangle_offset = 0
        merge_parts = []

        for i, rec in enumerate(records_with_mesh):
            md = rec.mesh_data
            if md is None or not hasattr(md, 'vertices'):
                continue
            all_verts.append(md.vertices)
            all_faces.append(md.indices + merge_vertex_offset)

            self._part_draw_infos.append({
                "part_index": i,
                "part_id": rec.part_id,
                "link_name": rec.link_name,
                "color_override": rec.color_override,
                "vertex_start": vertex_offset,
                "vertex_count": md.indices.size,
                "world_transform": rec.world_transform,
            })
            merge_parts.append((
                rec.part_id,
                rec.link_name or rec.part_id,
                merge_vertex_offset,
                len(md.vertices),
                merge_triangle_offset,
                len(md.indices),
                rec.world_transform,
            ))
            vertex_offset += md.indices.size
            merge_vertex_offset += len(md.vertices)
            merge_triangle_offset += len(md.indices)

        if not all_verts:
            return

        import numpy as np
        merged_verts = np.vstack(all_verts).astype(np.float32)
        merged_faces = np.vstack(all_faces).astype(np.uint32)

        # Flatten for glDrawArrays
        indices_flat = merged_faces.flatten().astype(np.int32)
        self._flat_vertices = merged_verts[indices_flat].astype(np.float32)

        # Normals
        from studio_io.mesh_loader import _compute_normals
        merged_normals = _compute_normals(merged_verts, merged_faces)
        self._flat_normals = merged_normals[indices_flat].astype(np.float32)

        self._draw_count = merged_faces.size
        self._vertices = merged_verts
        self._faces = merged_faces
        self._mesh_loaded = True
        self._buffers_dirty = True
        self._install_picker_mesh(merged_verts, merged_faces, merged_normals, merge_parts)

        self._update_scene_bounds(merged_verts)

    def _update_scene_bounds(self, vertices: np.ndarray) -> None:
        """Track scene bounds without resetting a user-adjusted camera."""
        if vertices is None or len(vertices) == 0:
            return
        lo = vertices.min(axis=0)
        hi = vertices.max(axis=0)
        center = (lo + hi) / 2.0
        extent = float((hi - lo).max())
        signature = tuple(float(round(v, 6)) for v in (*lo.tolist(), *hi.tolist()))
        bounds_changed = signature != self._scene_bounds_signature
        self._scene_bounds_signature = signature
        self._scene_extent = max(extent, 1e-4)
        self._center = QVector3D(float(center[0]), float(center[1]), float(center[2]))
        if bounds_changed and not self._camera_user_modified:
            self._distance = max(self._scene_extent * 1.8, 0.001)

    def _install_picker_mesh(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: np.ndarray,
        part_specs: list[tuple[str, str, int, int, int, int, list[float] | None]] | None = None,
    ) -> None:
        """Refresh CPU-side pick proxies from the currently rendered mesh."""
        from studio_io.mesh_data import MeshData, MeshPart
        from studio_io.mesh_loader import build_edge_indices

        edge_indices = build_edge_indices(faces)
        pick_vertices = vertices.copy()
        if part_specs:
            parts = [
                MeshPart(
                    id=part_id,
                    name=name,
                    link_name=name,
                    vertex_offset=vertex_offset,
                    vertex_count=vertex_count,
                    triangle_offset=triangle_offset,
                    triangle_count=triangle_count,
                )
                for (
                    part_id, name, vertex_offset, vertex_count,
                    triangle_offset, triangle_count, _transform,
                ) in part_specs
            ]
            for (
                _part_id, _name, vertex_offset, vertex_count,
                _triangle_offset, _triangle_count, transform,
            ) in part_specs:
                if transform and len(transform) == 16:
                    pick_vertices[vertex_offset:vertex_offset + vertex_count] = self._transform_points(
                        pick_vertices[vertex_offset:vertex_offset + vertex_count],
                        transform,
                    )
        else:
            parts = [
                MeshPart(
                    id="__model__",
                    name=self._model_name or "mesh",
                    vertex_offset=0,
                    vertex_count=len(vertices),
                    triangle_offset=0,
                    triangle_count=len(faces),
                    edge_index_offset=0,
                    edge_index_count=len(edge_indices),
                )
            ]

        mesh_data = MeshData(
            vertices=pick_vertices,
            indices=faces,
            normals=normals,
            edge_indices=edge_indices,
            parts=parts,
            bounds_min=tuple(float(v) for v in vertices.min(axis=0)),
            bounds_max=tuple(float(v) for v in vertices.max(axis=0)),
            source_format="viewport",
        )
        self._picker.set_mesh_data(mesh_data)

    @staticmethod
    def _transform_points(vertices: np.ndarray, matrix: list[float]) -> np.ndarray:
        transformed = np.empty_like(vertices, dtype=np.float32)
        for idx, (x, y, z) in enumerate(vertices):
            transformed[idx] = (
                matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3],
                matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7],
                matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11],
            )
        return transformed

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
        if self._wireframe and hasattr(funcs, "glPolygonMode"):
            funcs.glPolygonMode(_GL_FRONT_AND_BACK, _GL_LINE)

        # Bind vertex attributes (shared for all draw calls)
        self._program.enableAttributeArray('a_position')
        self._vbo_vertices.bind()
        self._program.setAttributeBuffer('a_position', _GL_FLOAT, 0, 3, 0)

        self._program.enableAttributeArray('a_normal')
        self._vbo_normals.bind()
        self._program.setAttributeBuffer('a_normal', _GL_FLOAT, 0, 3, 0)

        # Shared projection and view
        proj, view = self._camera_matrices()

        self._apply_lighting_uniforms()

        # Multi-mesh rendering path: each DisplayRecord is a separate draw call
        if self._display_records and self._part_draw_infos:
            self._draw_multi_mesh(proj, view, funcs)
        else:
            # Single-mesh legacy path
            model = QMatrix4x4()
            mvp = proj * view * model
            self._program.setUniformValue('u_mvp', mvp)
            self._program.setUniformValue('u_model', model)
            self._program.setUniformValue('u_color', QVector3D(*self._MESH_COLOR))
            self._program.setUniformValue(self._program.uniformLocation('u_emissive'), 0.0)
            funcs.glDrawArrays(_GL_TRIANGLES, 0, self._draw_count)

        self._draw_pick_feedback(proj, view, funcs)

        self._program.disableAttributeArray('a_position')
        self._program.disableAttributeArray('a_normal')
        self._program.release()
        if self._wireframe and hasattr(funcs, "glPolygonMode"):
            funcs.glPolygonMode(_GL_FRONT_AND_BACK, _GL_FILL)

    def _apply_lighting_uniforms(self) -> None:
        preset = self._lighting
        self._program.setUniformValue('u_ambient_color', QVector3D(*preset.ambient_color))
        self._program.setUniformValue(self._program.uniformLocation('u_ambient_intensity'), preset.ambient_intensity)
        self._program.setUniformValue('u_key_light_dir', QVector3D(*preset.key_light_dir).normalized())
        self._program.setUniformValue(self._program.uniformLocation('u_key_light_intensity'), preset.key_light_intensity)
        self._program.setUniformValue('u_fill_light_dir', QVector3D(*preset.fill_light_dir).normalized())
        self._program.setUniformValue(self._program.uniformLocation('u_fill_light_intensity'), preset.fill_light_intensity)
        self._program.setUniformValue('u_rim_light_dir', QVector3D(*preset.rim_light_dir).normalized())
        self._program.setUniformValue(self._program.uniformLocation('u_rim_light_intensity'), preset.rim_light_intensity)
        self._program.setUniformValue('u_hemisphere_sky', QVector3D(*preset.hemisphere_sky))
        self._program.setUniformValue('u_hemisphere_ground', QVector3D(*preset.hemisphere_ground))
        self._program.setUniformValue(self._program.uniformLocation('u_hemisphere_intensity'), preset.hemisphere_intensity)

    def _draw_multi_mesh(self, proj, view, funcs) -> None:
        """Draw each DisplayRecord as a separate draw call with its own
        world transform and color."""
        link_colors = [
            (0.29, 0.35, 0.50),  # blue-grey
            (0.35, 0.50, 0.29),  # green-grey
            (0.50, 0.29, 0.35),  # rose-grey
            (0.29, 0.50, 0.50),  # teal-grey
            (0.50, 0.35, 0.29),  # warm-grey
            (0.40, 0.40, 0.50),  # lavender-grey
            (0.50, 0.40, 0.29),  # amber-grey
            (0.29, 0.40, 0.50),  # slate
        ]
        for di in self._part_draw_infos:
            color_idx = di.get("part_index", 0) % len(link_colors)
            col = di.get("color_override") or link_colors[color_idx]

            # Build model matrix from world_transform (16-element flat row-major)
            transform = di.get("world_transform")
            if transform and len(transform) == 16:
                model = QMatrix4x4(*transform)
            else:
                model = QMatrix4x4()

            mvp = proj * view * model
            self._program.setUniformValue('u_mvp', mvp)
            self._program.setUniformValue('u_model', model)
            self._program.setUniformValue('u_color', QVector3D(*col))
            self._program.setUniformValue(
                self._program.uniformLocation('u_emissive'),
                self._emissive_for_part(di.get("part_id", ""), di.get("link_name", "")),
            )

            funcs.glDrawArrays(_GL_TRIANGLES, di["vertex_start"], di["vertex_count"])

    def _emissive_for_part(self, part_id: str, link_name: str = "") -> float:
        selected_part = self._pick_part_id(self._selected_pick)
        hover_part = self._pick_part_id(self._hover_pick)
        if part_id and part_id == selected_part:
            return 0.32
        if part_id and part_id == hover_part:
            return 0.16
        highlight = self._highlighted_item.strip()
        if highlight and (
            highlight in part_id or part_id in highlight
            or highlight in link_name or link_name in highlight
        ):
            return 0.22
        return 0.0

    def _draw_pick_feedback(self, proj, view, funcs) -> None:
        """Draw selected and hovered faces again with an emissive color."""
        for result, color, emissive in (
            (self._hover_pick, (0.55, 0.78, 0.88), 0.35),
            (self._selected_pick, (0.95, 0.78, 0.34), 0.55),
        ):
            face = result.face if result else None
            if face is None:
                continue
            draw_start = self._draw_start_for_face(face.part_id, face.face_index)
            if draw_start is None:
                continue
            model = self._model_matrix_for_part(face.part_id)
            mvp = proj * view * model
            self._program.setUniformValue('u_mvp', mvp)
            self._program.setUniformValue('u_model', model)
            self._program.setUniformValue('u_color', QVector3D(*color))
            self._program.setUniformValue(self._program.uniformLocation('u_emissive'), emissive)
            funcs.glDrawArrays(_GL_TRIANGLES, draw_start, 3)

    def _draw_start_for_face(self, part_id: str, face_index: int) -> int | None:
        if self._part_draw_infos:
            for di in self._part_draw_infos:
                if di.get("part_id") == part_id:
                    draw_start = int(di["vertex_start"]) + int(face_index) * 3
                    draw_end = int(di["vertex_start"]) + int(di["vertex_count"])
                    return draw_start if draw_start + 3 <= draw_end else None
            return None
        draw_start = int(face_index) * 3
        return draw_start if draw_start + 3 <= self._draw_count else None

    def _model_matrix_for_part(self, part_id: str) -> QMatrix4x4:
        if self._part_draw_infos:
            for di in self._part_draw_infos:
                if di.get("part_id") == part_id:
                    transform = di.get("world_transform")
                    if transform and len(transform) == 16:
                        return QMatrix4x4(*transform)
        return QMatrix4x4()

    @staticmethod
    def _pick_part_id(result: PickResult | None) -> str:
        if result is None:
            return ""
        if result.vertex is not None:
            return result.vertex.part_id
        if result.edge is not None:
            return result.edge.part_id
        if result.face is not None:
            return result.face.part_id
        return ""

    def _camera_matrices(self) -> tuple[QMatrix4x4, QMatrix4x4]:
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
        return proj, view

    def _pick_at(self, x: float, y: float) -> PickResult:
        if not self._mesh_loaded or self.width() <= 0 or self.height() <= 0:
            return PickResult()
        proj, view = self._camera_matrices()
        inv, invertible = (proj * view).inverted()
        if not invertible:
            return PickResult()

        ndc_x = (2.0 * x) / max(self.width(), 1) - 1.0
        ndc_y = 1.0 - (2.0 * y) / max(self.height(), 1)
        near = inv * QVector4D(ndc_x, ndc_y, -1.0, 1.0)
        far = inv * QVector4D(ndc_x, ndc_y, 1.0, 1.0)
        if abs(near.w()) < 1e-12 or abs(far.w()) < 1e-12:
            return PickResult()
        near_np = np.array(
            [near.x() / near.w(), near.y() / near.w(), near.z() / near.w()],
            dtype=np.float64,
        )
        far_np = np.array(
            [far.x() / far.w(), far.y() / far.w(), far.z() / far.w()],
            dtype=np.float64,
        )
        ray_dir = far_np - near_np
        norm = np.linalg.norm(ray_dir)
        if norm <= 1e-12:
            return PickResult()
        return self._picker.pick(near_np, ray_dir / norm)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._mesh_loaded:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._draw_viewport_chrome(painter)
            painter.end()
            return
        if not self._mesh_loaded:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#d6def1"), 1))
            rect = self.rect()
            mid_x = rect.width() // 2
            painter.drawText(mid_x - 120, rect.height() // 2 - 14, 240, 28,
                             Qt.AlignmentFlag.AlignCenter,
                             f"3D Preview - {self._model_name}")
            if self._joint_values:
                text = "  ".join(f"{v:.0f} deg" for v in self._joint_values)
                painter.setPen(QPen(QColor("#9fb0d0"), 1))
                painter.drawText(mid_x - 180, rect.height() // 2 + 18, 360, 24,
                                 Qt.AlignmentFlag.AlignCenter, text)
            painter.end()

    def _draw_viewport_chrome(self, painter: QPainter) -> None:
        proj, view = self._camera_matrices()
        mvp = proj * view
        grid_radius = max(self._scene_extent, 0.25)
        step = max(grid_radius / 5.0, 0.05)
        limit = step * 5

        painter.setPen(QPen(QColor(72, 92, 126, 96), 1))
        for idx in range(-5, 6):
            x = idx * step
            self._draw_projected_line(painter, mvp, (x, 0.0, -limit), (x, 0.0, limit))
            z = idx * step
            self._draw_projected_line(painter, mvp, (-limit, 0.0, z), (limit, 0.0, z))

        axis_len = max(grid_radius * 0.65, 0.2)
        axes = [
            ((axis_len, 0.0, 0.0), QColor("#f25f5c"), "X"),
            ((0.0, axis_len, 0.0), QColor("#51c77a"), "Y"),
            ((0.0, 0.0, axis_len), QColor("#5bb7ff"), "Z"),
        ]
        origin = (0.0, 0.0, 0.0)
        for end, color, label in axes:
            painter.setPen(QPen(color, 2))
            end_point = self._draw_projected_line(painter, mvp, origin, end)
            if end_point is not None:
                painter.drawText(end_point + QPointF(4.0, -4.0), label)

    def _draw_projected_line(
        self,
        painter: QPainter,
        mvp: QMatrix4x4,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
    ) -> QPointF | None:
        p0 = self._project_world_point(mvp, start)
        p1 = self._project_world_point(mvp, end)
        if p0 is None or p1 is None:
            return None
        painter.drawLine(p0, p1)
        return p1

    def _project_world_point(
        self,
        mvp: QMatrix4x4,
        point: tuple[float, float, float],
    ) -> QPointF | None:
        clip = mvp * QVector4D(float(point[0]), float(point[1]), float(point[2]), 1.0)
        if abs(clip.w()) < 1e-9:
            return None
        ndc_x = clip.x() / clip.w()
        ndc_y = clip.y() / clip.w()
        if not (-4.0 <= ndc_x <= 4.0 and -4.0 <= ndc_y <= 4.0):
            return None
        return QPointF(
            (ndc_x + 1.0) * 0.5 * self.width(),
            (1.0 - ndc_y) * 0.5 * self.height(),
        )

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = event.pos()
            self._press_pos = event.pos()
            self._press_pick = self._pick_at(event.position().x(), event.position().y())
            self._dragging = False

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._last_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            dx = event.pos().x() - self._last_pos.x()
            dy = event.pos().y() - self._last_pos.y()
            if self._press_pos is not None:
                moved = (
                    (event.pos().x() - self._press_pos.x()) ** 2
                    + (event.pos().y() - self._press_pos.y()) ** 2
                ) ** 0.5
                self._dragging = self._dragging or moved > 4.0
            if self._dragging:
                self._azimuth += dx * 0.4
                self._elevation += dy * 0.4
                self._elevation = max(-89.0, min(89.0, self._elevation))
                self._camera_user_modified = True
            self._last_pos = event.pos()
            self.update()
            return

        hover_pick = self._pick_at(event.position().x(), event.position().y())
        self._hover_pick = hover_pick if hover_pick.best_kind else None
        if self._hover_pick is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._dragging:
                pick = self._press_pick or self._pick_at(event.position().x(), event.position().y())
                self._selected_pick = pick if pick.best_kind else None
                self._hover_pick = self._selected_pick
                self.selection_changed.emit(self._pick_payload(self._selected_pick))
                self.update()
            self._dragging = False
            self._last_pos = None
            self._press_pos = None
            self._press_pick = None

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_pick = None
        self.unsetCursor()
        self.update()

    @staticmethod
    def _pick_payload(result: PickResult | None) -> dict:
        if result is None or not result.best_kind:
            return {"kind": "", "part_id": ""}
        payload = {"kind": result.best_kind, "part_id": Mesh3DWidget._pick_part_id(result)}
        if result.face is not None:
            payload.update({
                "face_index": result.face.face_index,
                "face_part_id": result.face.part_id,
                "face_point": result.face.world_point,
            })
        if result.edge is not None:
            payload.update({
                "edge_index": result.edge.edge_index,
                "edge_part_id": result.edge.part_id,
                "edge_point": result.edge.world_point,
            })
        if result.vertex is not None:
            payload.update({
                "vertex_index": result.vertex.vertex_index,
                "vertex_part_id": result.vertex.part_id,
                "vertex_point": result.vertex.world_point,
            })
        return payload

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        self._distance *= (1.0 - delta * 0.0008)
        self._distance = max(0.0005, min(10.0, self._distance))
        self._camera_user_modified = True
        self.update()

    # ------------------------------------------------------------------
    # Camera presets
    # ------------------------------------------------------------------

    _PRESETS = {
        "isometric": (45.0, 35.264, 1.0),
        "front": (0.0, 0.0, 1.0),
        "back": (180.0, 0.0, 1.0),
        "top": (0.0, 89.0, 1.0),
        "bottom": (0.0, -89.0, 1.0),
        "right": (90.0, 0.0, 1.0),
        "left": (-90.0, 0.0, 1.0),
    }

    def set_camera_preset(self, preset_name: str) -> None:
        """Jump camera to a named preset view."""
        preset = self._PRESETS.get(preset_name)
        if preset is None:
            return
        self._azimuth = preset[0]
        self._elevation = preset[1]
        self._distance = self._distance * preset[2]
        self._camera_user_modified = True
        self.update()

    def reset_camera(self) -> None:
        self._azimuth = 45.0
        self._elevation = 25.0
        self._distance = max(self._scene_extent * 1.8, 0.001)
        self._camera_user_modified = False
        self.update()

    def set_wireframe(self, enabled: bool) -> None:
        self._wireframe = bool(enabled)
        self.update()

    def set_highlighted_item(self, item_text: str) -> None:
        self._highlighted_item = str(item_text or "")
        self.update()

    def export_screenshot(self, path: str | Path) -> bool:
        image = self.grabFramebuffer()
        return bool(image.save(str(path)))

    def capture_viewport_state(self) -> dict:
        return {
            "azimuth": self._azimuth,
            "elevation": self._elevation,
            "distance": self._distance,
            "wireframe": self._wireframe,
            "highlighted_item": self._highlighted_item,
        }

    def apply_viewport_state(self, state: dict) -> None:
        if not isinstance(state, dict) or not state:
            return
        self._azimuth = float(state.get("azimuth", self._azimuth))
        self._elevation = float(state.get("elevation", self._elevation))
        self._distance = float(state.get("distance", self._distance))
        self._wireframe = bool(state.get("wireframe", self._wireframe))
        self._highlighted_item = str(state.get("highlighted_item", self._highlighted_item))
        self._camera_user_modified = True
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

# ---------------------------------------------------------------------------
# MeshViewportBackend — real 3D mesh rendering backend
# ---------------------------------------------------------------------------

_SAMPLE_MESH = Path(__file__).resolve().parent / "models" / "sample_bracket.stl"


class MeshViewportBackend:
    """Real 3D mesh viewport backend.

    Uses :class:`Mesh3DWidget` for OpenGL mesh rendering with orbit
    camera controls.  Loads mesh data via the unified studio_io loader.
    """

    def __init__(self) -> None:
        self._widget: Mesh3DWidget | None = None
        self._overlay = ViewportOverlay(title="", subtitle="")
        self._mesh_ready = False
        self._urdf_mesh_data = None
        self._urdf_mesh_path = ""
        self._cad_preview_records: list[DisplayRecord] = []
        self._last_saved_viewport_state: dict | None = None

    def build_widget(self) -> QWidget:
        if self._widget is None:
            self._widget = Mesh3DWidget()
            self._load_viewport_state()
            self._load_cad_preview_records()
            self._load_sample_mesh()
        return self._widget

    def _load_viewport_state(self) -> None:
        if self._widget is None:
            return
        try:
            from studio_io.viewport_state import load_viewport_state
            state = load_viewport_state()
            self._widget.apply_viewport_state(state)
            self._last_saved_viewport_state = self._widget.capture_viewport_state()
        except Exception:
            pass

    def _save_viewport_state(self) -> None:
        if self._widget is None:
            return
        try:
            from studio_io.viewport_state import save_viewport_state
            state = self._widget.capture_viewport_state()
            if state == self._last_saved_viewport_state:
                return
            save_viewport_state(state)
            self._last_saved_viewport_state = dict(state)
        except Exception:
            pass

    def _load_cad_preview_records(self) -> None:
        try:
            from cad.sample_parts import build_base_mount_part, build_wrist_link_part
            from studio_io.cad_mesh_bridge import cad_part_to_mesh_data
        except Exception:
            return
        records: list[DisplayRecord] = []
        specs = [
            (build_base_mount_part, "cad_base_mount", (-0.45, -0.28, 0.0), (0.75, 0.58, 0.34)),
            (build_wrist_link_part, "cad_wrist_link", (-0.20, -0.28, 0.0), (0.34, 0.66, 0.74)),
        ]
        for build_fn, part_id, offset, color in specs:
            try:
                part, _plan = build_fn()
                mesh = cad_part_to_mesh_data(part)
            except Exception:
                continue
            if mesh is None:
                continue
            scale = 0.003
            transform = [
                scale, 0.0,   0.0,   offset[0],
                0.0,   scale, 0.0,   offset[1],
                0.0,   0.0,   scale, offset[2],
                0.0,   0.0,   0.0,   1.0,
            ]
            records.append(DisplayRecord(
                part_id=part_id,
                link_name=part.part_name,
                mesh_data=mesh,
                visible=True,
                color_override=color,
                world_transform=transform,
            ))
        self._cad_preview_records = records

    def _load_sample_mesh(self) -> None:
        if not self._widget or not _SAMPLE_MESH.is_file():
            return
        try:
            from studio_io.mesh_loader import load_stl_mesh
            mesh_data = load_stl_mesh(str(_SAMPLE_MESH))
            if mesh_data is not None and len(mesh_data.vertices) > 0:
                import numpy as np
                flat_verts = mesh_data.vertices[mesh_data.indices.flatten()].astype(np.float32)
                flat_norms = mesh_data.normals[mesh_data.indices.flatten()].astype(np.float32)
                self._widget._vertices = mesh_data.vertices.copy()
                self._widget._faces = mesh_data.indices.copy()
                self._widget._flat_vertices = flat_verts
                self._widget._flat_normals = flat_norms
                self._widget._draw_count = mesh_data.indices.size
                self._widget._install_picker_mesh(
                    mesh_data.vertices.copy(),
                    mesh_data.indices.copy(),
                    mesh_data.normals.copy(),
                )
                self._widget._update_scene_bounds(mesh_data.vertices)
                self._widget._mesh_loaded = True
                self._widget._buffers_dirty = True
                self._mesh_ready = True
                self._widget.update()
        except Exception:
            # Fallback: use legacy direct trimesh loading
            if _SAMPLE_MESH.is_file():
                self._widget.load_mesh(str(_SAMPLE_MESH))
                self._mesh_ready = self._widget.mesh_loaded

    def get_overlay(self) -> ViewportOverlay:
        return self._overlay

    def update_frame(
        self,
        model: RobotModel,
        view_state: ViewState,
        joint_values: list[float],
    ) -> None:
        if self._widget is not None:
            self._ensure_urdf_mesh(view_state.model_path)
            records = self._build_display_records(model, joint_values)
            if records and any(record.mesh_data is not None for record in records):
                self._widget.set_robot_scene(model.name, joint_values, records)
            else:
                self._widget.set_scene(model.name, joint_values)

        title = f"{model.name} • 3D mesh view"
        mesh_status = "mesh loaded" if (
            self._widget is not None and self._widget.mesh_loaded
        ) else "no mesh"
        subtitle = (
            f"{model.link_count} links / {model.joint_count} joints"
            f"  |  selected: {view_state.selected_item}"
            f"  |  mode: {view_state.viewport_mode}"
            f"  |  {mesh_status}"
        )
        self._overlay = ViewportOverlay(title=title, subtitle=subtitle)
        self._save_viewport_state()

    def _ensure_urdf_mesh(self, model_path: str) -> None:
        path = Path(model_path)
        if self._urdf_mesh_path == str(path):
            return
        self._urdf_mesh_path = str(path)
        self._urdf_mesh_data = None
        self._mesh_ready = False
        if path.suffix.lower() not in {".urdf", ".xacro", ".xml"} or not path.is_file():
            return
        try:
            from studio_io.urdf_mesh_builder import build_urdf_mesh_data
            self._urdf_mesh_data = build_urdf_mesh_data(path)
            self._mesh_ready = self._urdf_mesh_data is not None
        except Exception:
            self._urdf_mesh_data = None

    def _build_display_records(
        self, model: RobotModel, joint_values: list[float],
    ) -> list:
        """Build per-link DisplayRecords with FK-computed world transforms."""
        if self._urdf_mesh_data is not None:
            records = self._build_urdf_display_records(model, joint_values)
            if records:
                return records + list(self._cad_preview_records)
        if not model.joints or not model.links:
            return list(self._cad_preview_records)
        chain = KinematicChain(model)
        pose = chain.compute_pose(joint_values)
        if not pose.positions_3d or len(pose.positions_3d) < len(pose.link_names):
            return []

        records = []
        for i, link_name in enumerate(pose.link_names):
            pos = pose.positions_3d[i]
            transform = [
                1.0, 0.0, 0.0, pos[0],
                0.0, 1.0, 0.0, pos[1],
                0.0, 0.0, 1.0, pos[2],
                0.0, 0.0, 0.0, 1.0,
            ]
            records.append(DisplayRecord(
                part_id=f"link_{i}",
                link_name=link_name,
                visible=True,
                world_transform=transform,
            ))
        return records + list(self._cad_preview_records)

    def _build_urdf_display_records(
        self, model: RobotModel, joint_values: list[float],
    ) -> list[DisplayRecord]:
        mesh_data = self._urdf_mesh_data
        if mesh_data is None or not getattr(mesh_data, "parts", None):
            return []
        link_transforms = self._compute_link_world_transforms(model, joint_values)
        try:
            from studio_io.urdf_mesh_builder import pose_urdf_mesh_parts
            posed_parts = pose_urdf_mesh_parts(mesh_data, link_transforms)
        except Exception:
            posed_parts = [
                {"part": part, "world_transform": part.transform}
                for part in mesh_data.parts
            ]

        palette = [
            (0.34, 0.46, 0.64),
            (0.38, 0.56, 0.42),
            (0.58, 0.40, 0.36),
            (0.34, 0.56, 0.58),
            (0.62, 0.52, 0.34),
            (0.48, 0.46, 0.62),
        ]
        records: list[DisplayRecord] = []
        for index, entry in enumerate(posed_parts):
            part = entry["part"]
            part_mesh = self._mesh_data_for_part(mesh_data, part)
            if part_mesh is None:
                continue
            records.append(DisplayRecord(
                part_id=part.id,
                link_name=part.link_name or part.name,
                mesh_data=part_mesh,
                visible=True,
                color_override=part.color or palette[index % len(palette)],
                world_transform=entry.get("world_transform"),
            ))
        return records

    def _mesh_data_for_part(self, mesh_data, part):
        from studio_io.mesh_data import MeshData, MeshPart
        from studio_io.mesh_loader import build_edge_indices

        v_start = int(part.vertex_offset)
        v_end = v_start + int(part.vertex_count)
        t_start = int(part.triangle_offset)
        t_end = t_start + int(part.triangle_count)
        if v_end <= v_start or t_end <= t_start:
            return None

        vertices = mesh_data.vertices[v_start:v_end].copy()
        indices = mesh_data.indices[t_start:t_end].copy() - v_start
        normals = mesh_data.normals[v_start:v_end].copy()
        edge_indices = build_edge_indices(indices)
        local_part = MeshPart(
            id=part.id,
            name=part.name,
            link_name=part.link_name,
            vertex_offset=0,
            vertex_count=len(vertices),
            triangle_offset=0,
            triangle_count=len(indices),
            edge_index_offset=0,
            edge_index_count=len(edge_indices),
            bounds_min=part.bounds_min,
            bounds_max=part.bounds_max,
        )
        return MeshData(
            vertices=vertices,
            indices=indices.astype(np.uint32),
            normals=normals,
            edge_indices=edge_indices,
            parts=[local_part],
            bounds_min=part.bounds_min,
            bounds_max=part.bounds_max,
            source_format="urdf-part",
        )

    def _compute_link_world_transforms(
        self, model: RobotModel, joint_values: list[float],
    ) -> dict[str, list[float]]:
        if not model.links:
            return {}
        child_links = {joint.child for joint in model.joints}
        root_link = next((link.name for link in model.links if link.name not in child_links), model.links[0].name)
        if not model.joints:
            return {root_link: [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ]}
        return compute_3d_tree_fk_transforms(
            [joint.name for joint in model.joints],
            joint_values,
            [joint.parent for joint in model.joints],
            [joint.child for joint in model.joints],
            [joint.origin_xyz for joint in model.joints],
            [joint.origin_rpy for joint in model.joints],
            [joint.axis_xyz for joint in model.joints],
            root_link,
        )
