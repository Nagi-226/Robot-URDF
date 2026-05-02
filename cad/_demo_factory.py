"""Shared demo factory functions — extracted to break the cad.demo ↔ cad.pipeline cycle."""

from __future__ import annotations

from .generator import CadScriptGenerator
from .manifest import CadManifest
from .sample_parts import build_base_mount_part, build_wrist_link_part
from .topology import TopologyGraph


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
