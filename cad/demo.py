from __future__ import annotations

from .edit_demo import run_edit_demo
from .generator import CadScriptGenerator
from .manifest import CadManifest
from .report import CadRunwayReport
from .sample_parts import build_base_mount_part, build_wrist_link_part
from .summary import summarize_pipeline_result
from .topology import TopologyGraph
from .writer_registry import WriterRegistry


def build_demo_manifest() -> CadManifest:
    manifest = CadManifest(robot_name="demo_robot")
    wrist_part, wrist_plan = build_wrist_link_part()
    base_part, base_plan = build_base_mount_part()
    manifest.add_part(wrist_part, wrist_plan)
    manifest.add_part(base_part, base_plan)
    return manifest


def render_demo_scripts() -> dict[str, str]:
    generator = CadScriptGenerator()
    manifest = build_demo_manifest()
    rendered: dict[str, str] = {}
    for part in manifest.parts:
        rendered[part.part_name] = generator.render(part)
    return rendered


def build_demo_topology() -> str:
    manifest = build_demo_manifest()
    graph = TopologyGraph(robot_name=manifest.robot_name)
    for part in manifest.parts:
        graph.from_part(part)
    return graph.summary()


def demo_report() -> str:
    from .pipeline import CadRunwayPipeline  # deferred to break circular import

    manifest = build_demo_manifest()
    topology = build_demo_topology()
    scripts = render_demo_scripts()
    edit_demo = run_edit_demo()
    pipeline = CadRunwayPipeline(writer=WriterRegistry().get("placeholder"), write_placeholders=True)
    pipeline_result = pipeline.run(manifest)
    summary = summarize_pipeline_result(pipeline_result)

    report = CadRunwayReport()
    report.add_section("manifest", manifest.summary())
    report.add_section("topology", topology)
    report.add_section("pipeline", *summary.render().splitlines())
    report.add_section("pipeline-dict", *[f"{k}={v}" for k, v in summary.as_dict().items()])
    report.add_section("edit-summary", pipeline_result.edit_summary)
    report.add_section("edit-demo", f"part={edit_demo.part_name}", f"handle={edit_demo.handle_name}", f"applied={edit_demo.applied}")
    report.add_section("edit-demo:before-summary", edit_demo.before_summary)
    report.add_section("edit-demo:after-summary", edit_demo.after_summary)
    report.add_section("edit-demo:before-script", edit_demo.before_script.strip())
    report.add_section("edit-demo:after-script", edit_demo.after_script.strip())
    report.add_section("script:wrist_link", scripts["wrist_link"].strip())
    report.add_section("script:base_mount", scripts["base_mount"].strip())
    return report.render()
