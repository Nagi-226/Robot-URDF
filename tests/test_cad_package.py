from __future__ import annotations

import pytest

from cad.handles import CadHandle, CadFeature
from cad.part import CadPartScript
from cad.export import ExportArtifact, ExportFormat, ExportPlan
from cad.generator import CadScriptGenerator
from cad.manifest import CadManifest
from cad.topology import TopologyGraph
from cad.sample_parts import build_base_mount_part, build_wrist_link_part
from cad.conventions import CadConvention
from cad.editors import CadEditInstruction, CadFeatureEditor
from cad.report import CadRunwayReport, ReportSection


class TestCadPackage:
    def test_handle_creation(self) -> None:
        h = CadHandle("mount", ".faces(\">Z\").workplane()", "M6 mounting hole")
        assert h.name == "mount"
        assert ".faces" in h.selector
        assert "M6" in h.notes

    def test_feature_with_handle(self) -> None:
        h = CadHandle("hole", ".circle(5)")
        f = CadFeature("bolt_hole", "hole", handle=h, parameters={"diameter": 5.0})
        assert f.handle is h
        assert f.parameters["diameter"] == 5.0
        assert "[hole]" in f.describe()

    def test_feature_without_handle(self) -> None:
        f = CadFeature("base", "box", parameters={"width": 100})
        assert f.handle is None
        assert f.parameters["width"] == 100

    def test_part_script_empty(self) -> None:
        p = CadPartScript("test_link")
        assert "Part: test_link" in p.summary()
        assert "Handles: 0" in p.summary()

    def test_part_script_add_handle(self) -> None:
        p = CadPartScript("test_link")
        p.add_handle("edge", ".edges(\"|Z\")", "2mm fillet")
        assert len(p.handles) == 1
        assert p.handles[0].name == "edge"

    def test_part_script_add_feature_consistent_api(self) -> None:
        p = CadPartScript("test_link")
        h = p.add_handle("mount", ".faces(\">Z\")")
        p.add_feature("hole1", "hole", handle=h, parameters={"diameter": 6.0})
        assert len(p.features) == 1
        assert p.features[0].parameters["diameter"] == 6.0

    def test_part_script_dedup_exports(self) -> None:
        p = CadPartScript("test_link")
        p.add_export("step")
        p.add_export("step")
        assert p.exports == ["step"]

    def test_export_plan_builds_artifacts(self) -> None:
        p = CadPartScript("base_link")
        plan = ExportPlan(part=p)
        plan.add(ExportFormat.STEP)
        plan.add(ExportFormat.STL)
        artifacts = plan.build_artifacts("models/test")
        assert len(artifacts) == 2
        assert artifacts[0].path == "models/test/base_link.step"
        assert artifacts[1].path == "models/test/base_link.stl"

    def test_export_format_enum_complete(self) -> None:
        values = {f.value for f in ExportFormat}
        assert values == {"step", "stl", "dxf", "glb", "topology", "urdf"}


class TestCadScriptGenerator:
    def test_render_empty_part(self) -> None:
        gen = CadScriptGenerator()
        part = CadPartScript("test_link")
        output = gen.render(part)
        assert "Auto-generated CAD script for test_link" in output
        assert "from cad import workspace" in output
        assert 'with workspace("test_link") as w:' in output

    def test_render_part_with_handles(self) -> None:
        gen = CadScriptGenerator()
        part = CadPartScript("test_link")
        part.add_handle("edge", ".edges(\"|Z\")", "2mm fillet")
        output = gen.render(part)
        assert "# @cad handles" in output
        assert "# @cad: edge -> .edges(\"|Z\")" in output

    def test_render_part_with_features(self) -> None:
        gen = CadScriptGenerator()
        part = CadPartScript("test_link")
        part.add_feature("base", "box", parameters={"width": 100})
        output = gen.render(part)
        assert "# Features" in output
        assert "base: box" in output

    def test_render_part_with_exports(self) -> None:
        gen = CadScriptGenerator()
        part = CadPartScript("test_link")
        part.add_export("step")
        part.add_export("stl")
        output = gen.render(part)
        assert "# Exports" in output
        assert "step, stl" in output

    def test_plan_exports_delegates(self) -> None:
        gen = CadScriptGenerator()
        part = CadPartScript("base_link")
        plan = ExportPlan(part=part)
        plan.add(ExportFormat.STEP)
        artifacts = gen.plan_exports(plan, "models/test")
        assert len(artifacts) == 1
        assert artifacts[0].path == "models/test/base_link.step"


class TestCadManifest:
    def test_empty_manifest(self) -> None:
        m = CadManifest("test_robot")
        assert m.robot_name == "test_robot"
        assert m.parts == []
        assert m.plans == []

    def test_add_part_with_plan(self) -> None:
        m = CadManifest("test_robot")
        part = CadPartScript("base_link")
        plan = ExportPlan(part=part)
        plan.add(ExportFormat.STEP)
        m.add_part(part, plan)
        assert len(m.parts) == 1
        assert len(m.plans) == 1

    def test_add_part_without_plan_auto_creates_plan(self) -> None:
        m = CadManifest("test_robot")
        part = CadPartScript("base_link")
        part.add_export("step")
        part.add_export("stl")
        m.add_part(part)  # no plan provided
        assert len(m.parts) == 1
        assert len(m.plans) == 1  # auto-created from part.exports
        assert m.plans[0].part is part
        assert ExportFormat.STEP in m.plans[0].formats

    def test_add_part_without_exports_no_plan(self) -> None:
        m = CadManifest("test_robot")
        part = CadPartScript("base_link")
        m.add_part(part)  # no plan, no exports
        assert len(m.parts) == 1
        assert len(m.plans) == 0  # nothing to auto-create

    def test_build_artifacts_from_all_plans(self) -> None:
        m = CadManifest("test_robot")
        p1 = CadPartScript("base_link")
        p1.add_export("step")
        m.add_part(p1)  # auto-plan
        p2 = CadPartScript("shoulder_link")
        plan2 = ExportPlan(part=p2)
        plan2.add(ExportFormat.STL)
        m.add_part(p2, plan2)
        artifacts = m.build_artifacts("models/test")
        assert len(artifacts) == 2
        paths = {a.path for a in artifacts}
        assert "models/test/base_link.step" in paths
        assert "models/test/shoulder_link.stl" in paths

    def test_summary(self) -> None:
        m = CadManifest("test_robot")
        assert "test_robot" in m.summary()
        assert "parts=0" in m.summary()


class TestTopologyGraph:
    def test_empty_graph(self) -> None:
        g = TopologyGraph("test_robot")
        assert g.robot_name == "test_robot"
        assert g.nodes == []

    def test_add_node(self) -> None:
        g = TopologyGraph("test_robot")
        g.add_node("base_link", "link")
        assert len(g.nodes) == 1
        assert g.nodes[0].name == "base_link"
        assert g.nodes[0].parent is None

    def test_add_node_with_parent(self) -> None:
        g = TopologyGraph("test_robot")
        g.add_node("base_link", "link")
        g.add_node("shoulder_joint", "joint", parent="base_link")
        assert g.nodes[1].parent == "base_link"

    def test_from_part(self) -> None:
        part = CadPartScript("wrist_link")
        part.add_handle("edge", ".edges(\"|Z\")")
        part.add_feature("fillet", "fillet", parameters={"radius": 2})
        g = TopologyGraph("test_robot")
        g.from_part(part)
        node_names = {n.name for n in g.nodes}
        assert "wrist_link" in node_names
        assert "edge" in node_names
        assert "fillet" in node_names

    def test_from_link_joint_graph(self) -> None:
        g = TopologyGraph("test_robot")
        links = ["base_link", "shoulder_link", "elbow_link"]
        joints = [
            ("base_link", "shoulder_link", "shoulder_joint"),
            ("shoulder_link", "elbow_link", "elbow_joint"),
        ]
        g.from_link_joint_graph(links, joints)
        node_names = {n.name for n in g.nodes}
        kinds = {n.name: n.kind for n in g.nodes}
        assert "base_link" in node_names
        assert "shoulder_joint" in node_names
        assert "elbow_joint" in node_names
        assert kinds["shoulder_joint"] == "joint"
        assert kinds["base_link"] == "link"

    def test_summary(self) -> None:
        g = TopologyGraph("test_robot")
        g.add_node("base_link", "link")
        assert "nodes=1" in g.summary()


class TestSampleParts:
    def test_wrist_link_part(self) -> None:
        part, plan = build_wrist_link_part()
        assert part.part_name == "wrist_link"
        assert len(part.handles) == 2
        assert len(part.features) == 3
        assert "step" in part.exports
        assert len(plan.formats) == 5  # STEP, STL, DXF, GLB, TOPOLOGY

    def test_base_mount_part(self) -> None:
        part, plan = build_base_mount_part()
        assert part.part_name == "base_mount"
        assert len(part.handles) == 2
        assert len(part.features) == 3
        assert "step" in part.exports
        assert ExportFormat.TOPOLOGY in plan.formats

    def test_source_is_body_only_no_workspace_wrapper(self) -> None:
        """Source must be body-only — no import or with-workspace wrapper."""
        for build_fn in (build_wrist_link_part, build_base_mount_part):
            part, _ = build_fn()
            assert "from cad import workspace" not in part.source
            assert "with workspace" not in part.source


class TestCadConvention:
    def test_default_convention(self) -> None:
        c = CadConvention()
        assert c.handle_prefix == "@cad"
        assert c.handle_separator == ":"

    def test_format_handle_comment(self) -> None:
        c = CadConvention()
        result = c.format_handle_comment("edge", '.edges("|Z")', "2mm fillet")
        assert "# @cad: edge -> .edges(\"|Z\")  # 2mm fillet" in result

    def test_format_handle_comment_no_notes(self) -> None:
        c = CadConvention()
        result = c.format_handle_comment("hole", ".circle(5)")
        assert "# @cad: hole -> .circle(5)" == result

    def test_custom_convention(self) -> None:
        c = CadConvention(handle_prefix="@@handle", handle_separator="=")
        result = c.format_handle_comment("mount", ".faces(\">Z\")")
        assert "@@handle=" in result


class TestCadFeatureEditor:
    def test_find_handle_exists(self) -> None:
        part = CadPartScript("test")
        h = part.add_handle("edge", ".edges(\"|Z\")")
        editor = CadFeatureEditor()
        found = editor.find_handle(part, "edge")
        assert found is h

    def test_find_handle_missing(self) -> None:
        part = CadPartScript("test")
        editor = CadFeatureEditor()
        assert editor.find_handle(part, "nonexistent") is None

    def test_apply_edit(self) -> None:
        part = CadPartScript("test")
        h = part.add_handle("mount", '.faces(">Z")')
        part.add_feature("hole1", "hole", handle=h, parameters={"diameter": 6.0})
        editor = CadFeatureEditor()
        result = editor.apply(
            part,
            CadEditInstruction("mount", "diameter", 8.0, "Upsize bolt"),
        )
        assert result is True
        assert part.features[0].parameters["diameter"] == 8.0

    def test_apply_edit_missing_handle(self) -> None:
        part = CadPartScript("test")
        editor = CadFeatureEditor()
        result = editor.apply(
            part,
            CadEditInstruction("no_such_handle", "diameter", 8.0),
        )
        assert result is False

    def test_annotate_handle(self) -> None:
        editor = CadFeatureEditor()
        h = CadHandle("edge", ".edges(\"|Z\")", "original note")
        annotated = editor.annotate_handle(h, "addendum")
        assert "original note" in annotated.notes
        assert "addendum" in annotated.notes
        assert annotated.name == h.name
        assert annotated.selector == h.selector


class TestCadEditBridge:
    def test_pick_to_handle_mapping_resolves_cad_part(self) -> None:
        from cad.edit_bridge import PickToHandleMapping

        part, _plan = build_base_mount_part()
        mapping = PickToHandleMapping.resolve("cad_base_mount", 0, part.handles)

        assert mapping is not None
        assert mapping.pick_part_id == "cad_base_mount"
        assert mapping.handle in part.handles

    def test_edit_history_undo_redo(self) -> None:
        from cad.edit_bridge import EditAction, EditHistory

        history = EditHistory(max_depth=2)
        first = EditAction("mount", "selection", 0.0, 1.0)
        second = EditAction("edge", "selection", 0.0, 2.0)
        history.push(first)
        history.push(second)

        assert history.undo() is second
        assert history.redo() is second
        assert history.can_undo is True


class TestCadRunwayReport:
    def test_empty_report(self) -> None:
        r = CadRunwayReport()
        assert r.render() == "\n"

    def test_single_section(self) -> None:
        r = CadRunwayReport()
        r.add_section("header", "line 1", "line 2")
        output = r.render()
        assert "[header]" in output
        assert "line 1\nline 2" in output

    def test_multi_section(self) -> None:
        r = CadRunwayReport()
        r.add_section("manifest", "parts=2")
        r.add_section("topology", "nodes=5")
        output = r.render()
        assert "[manifest]" in output
        assert "[topology]" in output
        assert "parts=2" in output
        assert "nodes=5" in output

    def test_report_section_render(self) -> None:
        s = ReportSection("test", ["a", "b", "c"])
        output = s.render()
        assert "[test]\na\nb\nc" == output


class TestCadMeshBridge:
    def test_sample_part_converts_to_preview_mesh(self) -> None:
        from studio_io.cad_mesh_bridge import cad_part_to_mesh_data

        part, _plan = build_base_mount_part()
        mesh_data = cad_part_to_mesh_data(part)
        assert mesh_data is not None
        assert mesh_data.source_format == "cad-preview"
        assert mesh_data.parts[0].id == "base_mount"
        assert mesh_data.edge_indices is not None
