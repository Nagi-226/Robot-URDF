"""Tests for the rendering module (backends, overlays, mesh widget)."""

import sys

import numpy as np
import pytest

_qapp = None
try:
    from PySide6.QtWidgets import QApplication
    _qapp = QApplication.instance() or QApplication(sys.argv)
except Exception:
    pass


def _require_qapp():
    if _qapp is None:
        pytest.skip("QApplication not available")


class TestViewportOverlay:
    def test_construction(self):
        from rendering import ViewportOverlay
        overlay = ViewportOverlay(title="Test", subtitle="sub")
        assert overlay.title == "Test"
        assert overlay.subtitle == "sub"


class TestComputeVertexNormals:
    def test_single_triangle(self):
        from studio_io.mesh_loader import _compute_normals
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = _compute_normals(vertices, faces)
        assert normals.shape == (3, 3)
        # Normal should point in +Z for this winding order
        for n in normals:
            assert n[2] > 0

    def test_cube_normals(self):
        from studio_io.mesh_loader import _compute_normals
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
        ], dtype=np.float32)
        faces = np.array([
            [0, 1, 2], [0, 2, 3],  # -Z
            [4, 6, 5], [4, 7, 6],  # +Z
            [0, 4, 5], [0, 5, 1],  # -Y
            [2, 6, 7], [2, 7, 3],  # +Y
            [1, 5, 6], [1, 6, 2],  # +X
            [0, 3, 7], [0, 7, 4],  # -X
        ], dtype=np.uint32)
        normals = _compute_normals(vertices, faces)
        assert normals.shape == (8, 3)
        assert np.all(np.abs(np.linalg.norm(normals, axis=1) - 1.0) < 1e-5)


class TestSkeletonViewportBackend:
    def test_build_widget_returns_widget(self):
        _require_qapp()
        from rendering import SkeletonViewportBackend
        backend = SkeletonViewportBackend()
        widget = backend.build_widget()
        assert widget is not None

    def test_update_frame_changes_overlay(self):
        _require_qapp()
        from rendering import SkeletonViewportBackend
        from robot_model import RobotModel, ViewState
        backend = SkeletonViewportBackend()
        _widget = backend.build_widget()
        model = RobotModel(name="TestRobot")
        state = ViewState(selected_item="link0")
        backend.update_frame(model, state, [1.0, 2.0])
        overlay = backend.get_overlay()
        assert "TestRobot" in overlay.title


class TestMeshViewportBackend:
    def _triangle_mesh(self):
        from studio_io.mesh_data import MeshData, MeshPart
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ], dtype=np.float32)
        indices = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = np.array([[0.0, 0.0, 1.0]] * 3, dtype=np.float32)
        return MeshData(
            vertices=vertices,
            indices=indices,
            normals=normals,
            parts=[MeshPart(
                id="tri",
                name="triangle",
                vertex_offset=0,
                vertex_count=3,
                triangle_offset=0,
                triangle_count=1,
            )],
        )

    def test_construction(self):
        _require_qapp()
        from rendering import MeshViewportBackend
        backend = MeshViewportBackend()
        assert backend is not None

    def test_mesh_loaded_property_defaults_false(self):
        _require_qapp()
        from rendering import Mesh3DWidget
        widget = Mesh3DWidget()
        assert widget.mesh_loaded is False

    def test_backend_includes_cad_preview_records_without_robot(self):
        _require_qapp()
        from rendering import MeshViewportBackend
        from robot_model import RobotModel

        backend = MeshViewportBackend()
        backend.build_widget()
        records = backend._build_display_records(RobotModel(), [])
        part_ids = {record.part_id for record in records}

        assert {"cad_base_mount", "cad_wrist_link"}.issubset(part_ids)
        assert all(record.mesh_data is not None for record in records)

    def test_tree_highlight_matches_link_name(self):
        _require_qapp()
        from rendering import Mesh3DWidget

        widget = Mesh3DWidget()
        widget.set_highlighted_item("base_link")

        assert widget._emissive_for_part("visual_0", "base_link") > 0.0

    def test_viewport_state_roundtrip_on_widget(self):
        _require_qapp()
        from rendering import Mesh3DWidget

        widget = Mesh3DWidget()
        widget.apply_viewport_state({
            "azimuth": 10.0,
            "elevation": 20.0,
            "distance": 3.0,
            "wireframe": True,
            "highlighted_item": "base_link",
        })
        state = widget.capture_viewport_state()

        assert state["azimuth"] == 10.0
        assert state["elevation"] == 20.0
        assert state["distance"] == 3.0
        assert state["wireframe"] is True
        assert state["highlighted_item"] == "base_link"

    def test_camera_preset_changes_capture_state(self):
        _require_qapp()
        from rendering import Mesh3DWidget

        widget = Mesh3DWidget()
        widget.set_camera_preset("front")
        state = widget.capture_viewport_state()

        assert state["azimuth"] == 0.0
        assert state["elevation"] == 0.0

    def test_display_records_filter_visibility_and_keep_opacity(self):
        _require_qapp()
        from rendering import DisplayRecord, Mesh3DWidget

        widget = Mesh3DWidget()
        visible = DisplayRecord(
            part_id="visible",
            link_name="visible",
            mesh_data=self._triangle_mesh(),
            opacity=0.35,
            color_override=(1.0, 0.2, 0.1),
        )
        hidden = DisplayRecord(
            part_id="hidden",
            link_name="hidden",
            mesh_data=self._triangle_mesh(),
            visible=False,
        )

        widget.set_robot_scene("ReliabilityBot", [], [visible, hidden])

        assert len(widget._part_draw_infos) == 1
        assert widget._part_draw_infos[0]["part_id"] == "visible"
        assert widget._part_draw_infos[0]["opacity"] == 0.35


class TestViewportStatePersistence:
    def test_save_and_load_viewport_state(self):
        from pathlib import Path
        from studio_io.viewport_state import load_viewport_state, save_viewport_state

        state_path = Path(".pytest-cache") / "viewport_state_test.json"
        try:
            save_viewport_state({
                "azimuth": 12,
                "elevation": 34,
                "distance": 5,
                "wireframe": True,
                "highlighted_item": "cad_base_mount",
            }, state_path)

            loaded = load_viewport_state(state_path)
            assert loaded["azimuth"] == 12.0
            assert loaded["elevation"] == 34.0
            assert loaded["distance"] == 5.0
            assert loaded["wireframe"] is True
            assert loaded["highlighted_item"] == "cad_base_mount"
        finally:
            state_path.unlink(missing_ok=True)


class TestMeshPicking:
    def _triangle_mesh(self):
        from studio_io.mesh_data import MeshData, MeshPart
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ], dtype=np.float32)
        indices = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = np.array([[0.0, 0.0, 1.0]] * 3, dtype=np.float32)
        return MeshData(
            vertices=vertices,
            indices=indices,
            normals=normals,
            parts=[MeshPart(
                id="tri",
                name="triangle",
                vertex_offset=0,
                vertex_count=3,
                triangle_offset=0,
                triangle_count=1,
            )],
        )

    def test_edge_indices_built_from_triangles(self):
        from studio_io.mesh_loader import build_edge_indices
        edges = build_edge_indices(np.array([[0, 1, 2]], dtype=np.uint32))
        assert edges.shape == (3, 2)
        assert {tuple(edge) for edge in edges.tolist()} == {
            (0, 1), (0, 2), (1, 2),
        }

    def test_picker_prioritizes_edge_over_face(self):
        from studio_io.picking import MeshPicker
        picker = MeshPicker()
        picker.set_mesh_data(self._triangle_mesh())
        result = picker.pick(
            np.array([0.5, 0.0, 1.0], dtype=np.float64),
            np.array([0.0, 0.0, -1.0], dtype=np.float64),
        )
        assert result.face is not None
        assert result.edge is not None
        assert result.best_kind == "edge"

    def test_picker_prioritizes_vertex_over_edge_and_face(self):
        from studio_io.picking import MeshPicker
        picker = MeshPicker()
        picker.set_mesh_data(self._triangle_mesh())
        result = picker.pick(
            np.array([0.0, 0.0, 1.0], dtype=np.float64),
            np.array([0.0, 0.0, -1.0], dtype=np.float64),
        )
        assert result.face is not None
        assert result.edge is not None
        assert result.vertex is not None
        assert result.best_kind == "vertex"


class TestUrdfMeshBuilder:
    def test_simple_arm_primitives_build_mesh_data(self):
        from pathlib import Path
        from studio_io.urdf_mesh_builder import build_urdf_mesh_data

        mesh_data = build_urdf_mesh_data(Path("models/simple_arm.urdf"))
        assert mesh_data is not None
        assert mesh_data.source_format == "urdf"
        assert len(mesh_data.parts) == 5
        assert mesh_data.edge_indices is not None
        assert len(mesh_data.edge_indices) > 0

    def test_extended_primitives_build_mesh_data(self):
        from studio_io.mesh_loader import build_primitive_mesh

        for primitive in ("cone", "capsule"):
            mesh_data = build_primitive_mesh(
                primitive,
                {"radius": 0.2, "length": 1.0},
                name=f"test_{primitive}",
            )
            assert mesh_data is not None
            assert mesh_data.vertex_count > 0
            assert mesh_data.triangle_count > 0
            assert mesh_data.edge_indices is not None

    def test_package_uri_mesh_resolution(self):
        import shutil
        from pathlib import Path
        from studio_io.urdf_mesh_builder import build_urdf_mesh_data

        tmp_root = Path(".pytest-cache") / "package_uri_mesh_resolution"
        if tmp_root.exists():
            shutil.rmtree(tmp_root)
        package_dir = tmp_root / "src" / "demo_robot"
        mesh_dir = package_dir / "meshes"
        urdf_dir = package_dir / "urdf"
        try:
            mesh_dir.mkdir(parents=True)
            urdf_dir.mkdir(parents=True)
            (mesh_dir / "tri.stl").write_text(
                "\n".join([
                    "solid tri",
                    "facet normal 0 0 1",
                    "outer loop",
                    "vertex 0 0 0",
                    "vertex 1 0 0",
                    "vertex 0 1 0",
                    "endloop",
                    "endfacet",
                    "endsolid tri",
                ]),
                encoding="utf-8",
            )
            urdf_path = urdf_dir / "robot.urdf"
            urdf_path.write_text(
                """<robot name="pkg_bot">
  <material name="amber"><color rgba="1.0 0.5 0.2 0.4"/></material>
  <link name="base">
    <visual>
      <geometry><mesh filename="package://demo_robot/meshes/tri.stl"/></geometry>
      <material name="amber"/>
    </visual>
  </link>
</robot>""",
                encoding="utf-8",
            )

            mesh_data = build_urdf_mesh_data(urdf_path)

            assert mesh_data is not None
            assert mesh_data.parts[0].color == (1.0, 0.5, 0.2)
            assert mesh_data.parts[0].opacity == 0.4
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)
