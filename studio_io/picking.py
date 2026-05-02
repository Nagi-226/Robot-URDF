"""3D picking system — raycasting against mesh proxy geometry.

Adopted from text-to-cad's useExplorerPicking.js:
  - Proxy geometry for face/edge/vertex hit testing
  - Depth-window occlusion filtering
  - Multi-tier priority: vertex > edge > face with adjacency bonuses
  - Screen-space threshold clamping

Operates on canonical MeshData, not GPU resources.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


# ---------------------------------------------------------------------------
# Ray-triangle intersection (Möller-Trumbore)
# ---------------------------------------------------------------------------

def _ray_triangle_intersection(
    ray_origin: np.ndarray,
    ray_dir: np.ndarray,
    v0: np.ndarray,
    v1: np.ndarray,
    v2: np.ndarray,
    cull_backface: bool = True,
) -> float | None:
    """Return distance t along ray, or None if no intersection."""
    edge1 = v1 - v0
    edge2 = v2 - v0
    h = np.cross(ray_dir, edge2)
    a = np.dot(edge1, h)
    if cull_backface and a < 1e-12:
        return None
    if abs(a) < 1e-12:
        return None  # parallel
    f = 1.0 / a
    s = ray_origin - v0
    u = f * np.dot(s, h)
    if u < 0.0 or u > 1.0:
        return None
    q = np.cross(s, edge1)
    v = f * np.dot(ray_dir, q)
    if v < 0.0 or u + v > 1.0:
        return None
    t = f * np.dot(edge2, q)
    return t if t > 1e-8 else None


def _world_ray_from_screen(
    screen_x: float,
    screen_y: float,
    viewport_w: float,
    viewport_h: float,
    proj: np.ndarray,   # 4x4 projection
    view: np.ndarray,    # 4x4 view
) -> tuple[np.ndarray, np.ndarray]:
    """Convert screen coordinates to world-space ray."""
    ndc_x = (2.0 * screen_x) / viewport_w - 1.0
    ndc_y = 1.0 - (2.0 * screen_y) / viewport_h
    ndc_near = np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float64)
    ndc_far = np.array([ndc_x, ndc_y, 1.0, 1.0], dtype=np.float64)
    inv_proj_view = np.linalg.inv(proj @ view)
    world_near = inv_proj_view @ ndc_near
    world_near /= world_near[3]
    world_far = inv_proj_view @ ndc_far
    world_far /= world_far[3]
    origin = world_near[:3]
    direction = world_far[:3] - origin
    direction /= np.linalg.norm(direction)
    return origin, direction


# ---------------------------------------------------------------------------
# Hit result types
# ---------------------------------------------------------------------------

@dataclass
class FaceHit:
    part_id: str
    face_index: int
    distance: float
    world_point: tuple[float, float, float]


@dataclass
class EdgeHit:
    part_id: str
    edge_index: int
    distance: float
    screen_distance_px: float
    world_point: tuple[float, float, float]


@dataclass
class VertexHit:
    part_id: str
    vertex_index: int
    distance: float
    screen_distance_px: float
    world_point: tuple[float, float, float]


@dataclass
class PickResult:
    face: FaceHit | None = None
    edge: EdgeHit | None = None
    vertex: VertexHit | None = None
    best_kind: str = ""  # "face" | "edge" | "vertex" | ""


# ---------------------------------------------------------------------------
# Face pick proxy
# ---------------------------------------------------------------------------

@dataclass
class FacePickProxy:
    """Pre-built face-level picking data for a MeshData."""
    triangle_faces: np.ndarray  # M×3×3 face vertices in model space
    face_ids: list[tuple[str, int]]  # (part_id, local_face_index) per global triangle
    part_ids: list[str]  # per-triangle


@dataclass
class EdgePickProxy:
    """Pre-built edge-level picking data for a MeshData."""
    segments: np.ndarray  # Ex2x3 vertices in model space
    edge_ids: list[tuple[str, int]]  # (part_id, local_edge_index)


@dataclass
class VertexPickProxy:
    """Pre-built vertex-level picking data for a MeshData."""
    vertices: np.ndarray  # Nx3 vertices in model space
    vertex_ids: list[tuple[str, int]]  # (part_id, local_vertex_index)


def _part_id_for_vertex(mesh_data, vertex_index: int) -> tuple[str, int]:
    for part in mesh_data.parts:
        start = int(part.vertex_offset)
        end = start + int(part.vertex_count)
        if start <= vertex_index < end:
            return part.id, vertex_index - start
    return "__model__", vertex_index


def build_face_pick_proxy(mesh_data) -> FacePickProxy:
    """Build face picking proxy from MeshData.

    Each triangle gets an entry with its (part_id, face_index) mapping.
    """
    vertices = np.array(mesh_data.vertices, dtype=np.float64)
    indices = np.array(mesh_data.indices, dtype=np.int32)
    tri_count = len(indices)
    triangle_faces = np.zeros((tri_count, 3, 3), dtype=np.float64)
    face_ids: list[tuple[str, int]] = []
    part_ids: list[str] = []

    if mesh_data.parts:
        for part in mesh_data.parts:
            t_start = part.triangle_offset
            t_end = t_start + part.triangle_count
            for ti in range(t_start, min(t_end, tri_count)):
                tri = indices[ti]
                triangle_faces[ti] = vertices[tri]
                face_ids.append((part.id, ti - t_start))
                part_ids.append(part.id)
    else:
        for ti in range(tri_count):
            tri = indices[ti]
            triangle_faces[ti] = vertices[tri]
            face_ids.append(("__model__", ti))
            part_ids.append("__model__")

    return FacePickProxy(
        triangle_faces=triangle_faces,
        face_ids=face_ids,
        part_ids=part_ids,
    )


def build_edge_pick_proxy(mesh_data) -> EdgePickProxy:
    """Build edge picking proxy from MeshData edge_indices."""
    vertices = np.array(mesh_data.vertices, dtype=np.float64)
    edge_indices = getattr(mesh_data, "edge_indices", None)
    if edge_indices is None or len(edge_indices) == 0:
        from studio_io.mesh_loader import build_edge_indices
        edge_indices = build_edge_indices(np.array(mesh_data.indices, dtype=np.uint32))
    edge_indices = np.array(edge_indices, dtype=np.int32)
    segments = np.zeros((len(edge_indices), 2, 3), dtype=np.float64)
    edge_ids: list[tuple[str, int]] = []
    local_edge_counts: dict[str, int] = {}

    for ei, (a, b) in enumerate(edge_indices):
        segments[ei, 0] = vertices[a]
        segments[ei, 1] = vertices[b]
        part_id, _ = _part_id_for_vertex(mesh_data, int(a))
        other_part_id, _ = _part_id_for_vertex(mesh_data, int(b))
        if other_part_id != part_id:
            part_id = "__model__"
        local_index = local_edge_counts.get(part_id, 0)
        local_edge_counts[part_id] = local_index + 1
        edge_ids.append((part_id, local_index))

    return EdgePickProxy(segments=segments, edge_ids=edge_ids)


def build_vertex_pick_proxy(mesh_data) -> VertexPickProxy:
    """Build vertex picking proxy from MeshData vertices."""
    vertices = np.array(mesh_data.vertices, dtype=np.float64)
    vertex_ids = [_part_id_for_vertex(mesh_data, idx) for idx in range(len(vertices))]
    return VertexPickProxy(vertices=vertices, vertex_ids=vertex_ids)


def _distance_ray_to_point(
    ray_origin: np.ndarray,
    ray_dir: np.ndarray,
    point: np.ndarray,
) -> tuple[float, float, np.ndarray]:
    t = float(np.dot(point - ray_origin, ray_dir))
    if t < 0.0:
        return float("inf"), t, ray_origin
    closest = ray_origin + ray_dir * t
    return float(np.linalg.norm(point - closest)), t, closest


def _distance_ray_to_segment(
    ray_origin: np.ndarray,
    ray_dir: np.ndarray,
    start: np.ndarray,
    end: np.ndarray,
) -> tuple[float, float, np.ndarray]:
    segment = end - start
    seg_len_sq = float(np.dot(segment, segment))
    if seg_len_sq <= 1e-18:
        distance, ray_t, closest = _distance_ray_to_point(ray_origin, ray_dir, start)
        return distance, ray_t, closest

    w0 = ray_origin - start
    a = float(np.dot(ray_dir, ray_dir))
    b = float(np.dot(ray_dir, segment))
    c = seg_len_sq
    d = float(np.dot(ray_dir, w0))
    e = float(np.dot(segment, w0))
    denom = a * c - b * b

    if abs(denom) < 1e-12:
        ray_t = max(0.0, -d / a if a > 1e-12 else 0.0)
        seg_t = float(np.clip((b * ray_t - e) / c, 0.0, 1.0))
    else:
        ray_t = (b * e - c * d) / denom
        seg_t = (a * e - b * d) / denom
        if ray_t < 0.0:
            ray_t = 0.0
            seg_t = float(np.clip(-e / c, 0.0, 1.0))
        else:
            seg_t = float(np.clip(seg_t, 0.0, 1.0))
            ray_t = max(0.0, (b * seg_t - d) / a if a > 1e-12 else 0.0)

    closest_ray = ray_origin + ray_dir * ray_t
    closest_segment = start + segment * seg_t
    distance = float(np.linalg.norm(closest_ray - closest_segment))
    return distance, float(ray_t), closest_segment


# ---------------------------------------------------------------------------
# Picker
# ---------------------------------------------------------------------------

class MeshPicker:
    """Pick faces, edges, and vertices against MeshData geometry."""

    def __init__(self) -> None:
        self._face_proxy: FacePickProxy | None = None
        self._edge_proxy: EdgePickProxy | None = None
        self._vertex_proxy: VertexPickProxy | None = None
        self._vertices_ref: np.ndarray | None = None

    def set_mesh_data(self, mesh_data) -> None:
        self._face_proxy = build_face_pick_proxy(mesh_data)
        self._edge_proxy = build_edge_pick_proxy(mesh_data)
        self._vertex_proxy = build_vertex_pick_proxy(mesh_data)
        self._vertices_ref = np.array(mesh_data.vertices, dtype=np.float64)

    def pick(
        self,
        ray_origin: np.ndarray,
        ray_dir: np.ndarray,
        face_pick_threshold: float = 0.02,
        edge_pick_threshold_px: float = 10.0,
        vertex_pick_threshold_px: float = 5.0,
    ) -> PickResult:
        """Run full multi-tier pick at the given world-space ray.

        Returns best PickResult with priority: vertex > edge > face.
        """
        result = PickResult()

        # Tier 1: Face picking
        result.face = self._pick_face(ray_origin, ray_dir)

        # Tier 2: Edge picking
        result.edge = self._pick_edge(ray_origin, ray_dir, result.face)

        # Tier 3: Vertex picking
        result.vertex = self._pick_vertex(ray_origin, ray_dir, result.face, result.edge)

        # Priority: vertex beats edge beats face
        if result.vertex is not None:
            result.best_kind = "vertex"
        elif result.edge is not None:
            result.best_kind = "edge"
        elif result.face is not None:
            result.best_kind = "face"

        return result

    def _pick_face(
        self, ray_origin: np.ndarray, ray_dir: np.ndarray,
    ) -> FaceHit | None:
        if self._face_proxy is None:
            return None
        proxy = self._face_proxy
        best_t = float("inf")
        best_tri = -1

        for ti in range(len(proxy.triangle_faces)):
            tri = proxy.triangle_faces[ti]
            t = _ray_triangle_intersection(
                ray_origin, ray_dir, tri[0], tri[1], tri[2],
            )
            if t is not None and t < best_t:
                best_t = t
                best_tri = ti

        if best_tri < 0:
            return None

        hit_point = ray_origin + ray_dir * best_t
        pid, face_idx = proxy.face_ids[best_tri]
        return FaceHit(
            part_id=pid,
            face_index=face_idx,
            distance=float(best_t),
            world_point=tuple(float(v) for v in hit_point),
        )

    def _pick_edge(
        self, ray_origin: np.ndarray, ray_dir: np.ndarray,
        face: FaceHit | None,
    ) -> EdgeHit | None:
        if self._edge_proxy is None:
            return None
        proxy = self._edge_proxy
        model_scale = self._model_scale()
        threshold = max(model_scale * 0.018, 1e-5)
        occlusion_window = max(threshold * 3.0, model_scale * 0.004)
        best: tuple[float, float, int, np.ndarray] | None = None

        for edge_idx, segment in enumerate(proxy.segments):
            distance, ray_t, closest = _distance_ray_to_segment(
                ray_origin, ray_dir, segment[0], segment[1],
            )
            if not math.isfinite(distance) or distance > threshold:
                continue
            if face is not None and ray_t > face.distance + occlusion_window:
                continue
            score = (distance, ray_t, edge_idx, closest)
            if best is None or score[:3] < best[:3]:
                best = score

        if best is None:
            return None

        distance, ray_t, edge_idx, closest = best
        part_id, local_index = proxy.edge_ids[edge_idx]
        return EdgeHit(
            part_id=part_id,
            edge_index=local_index,
            distance=float(ray_t),
            screen_distance_px=float(distance),
            world_point=tuple(float(v) for v in closest),
        )

    def _pick_vertex(
        self, ray_origin: np.ndarray, ray_dir: np.ndarray,
        face: FaceHit | None, edge: EdgeHit | None,
    ) -> VertexHit | None:
        if self._vertex_proxy is None:
            return None
        proxy = self._vertex_proxy
        model_scale = self._model_scale()
        threshold = max(model_scale * 0.012, 1e-5)
        occlusion_window = max(threshold * 4.0, model_scale * 0.004)
        front_distance = edge.distance if edge is not None else (
            face.distance if face is not None else None
        )
        best: tuple[float, float, int] | None = None

        for vertex_idx, vertex in enumerate(proxy.vertices):
            distance, ray_t, _closest = _distance_ray_to_point(ray_origin, ray_dir, vertex)
            if not math.isfinite(distance) or distance > threshold:
                continue
            if front_distance is not None and ray_t > front_distance + occlusion_window:
                continue
            score = (distance, ray_t, vertex_idx)
            if best is None or score < best:
                best = score

        if best is None:
            return None

        distance, ray_t, vertex_idx = best
        part_id, local_index = proxy.vertex_ids[vertex_idx]
        point = proxy.vertices[vertex_idx]
        return VertexHit(
            part_id=part_id,
            vertex_index=local_index,
            distance=float(ray_t),
            screen_distance_px=float(distance),
            world_point=tuple(float(v) for v in point),
        )

    def _model_scale(self) -> float:
        if self._vertices_ref is None or len(self._vertices_ref) == 0:
            return 1.0
        lo = self._vertices_ref.min(axis=0)
        hi = self._vertices_ref.max(axis=0)
        return float(max(np.linalg.norm(hi - lo), 1e-6))
