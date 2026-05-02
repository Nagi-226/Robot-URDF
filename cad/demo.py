from __future__ import annotations

from ._demo_factory import build_demo_manifest, build_demo_topology, render_demo_scripts
from .edit_demo import run_edit_demo
from .pipeline import CadRunwayPipeline
from .report import CadRunwayReport
from .summary import summarize_pipeline_result
from .writer_registry import WriterRegistry


def demo_report() -> str:
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
