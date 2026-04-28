from __future__ import annotations

from .part import CadPartScript
from .export import ExportFormat, ExportPlan


def build_wrist_link_part() -> tuple[CadPartScript, ExportPlan]:
    part = CadPartScript(part_name="wrist_link")
    mount_face = part.add_handle(
        name="shaft_mount",
        selector='faces(">Y")',
        notes="Primary mounting face for the wrist shaft connection",
    )
    round_edge = part.add_handle(
        name="edge_rounding",
        selector='edges("|Z")',
        notes="Outer edge rounding handle for the wrist shell",
    )
    part.add_feature("base_block", "box", parameters={"width": 60, "height": 50, "depth": 30})
    part.add_feature("mount_bore", "circle_extrude", handle=mount_face, parameters={"radius": 15, "depth": 20})
    part.add_feature("fillet_pass", "fillet", handle=round_edge, parameters={"radius": 2})
    part.set_source(
        """body = w.box(60, 50, 30)
body = body.edges("|Z").fillet(2)  # @cad: edge_rounding
body = body.faces(">Y").workplane()  # @cad: shaft_mount
body = body.circle(15).extrude(20)
"""
    )
    part.add_export(ExportFormat.STEP.value)
    part.add_export(ExportFormat.STL.value)
    part.add_export(ExportFormat.DXF.value)
    plan = ExportPlan(part=part)
    plan.add(ExportFormat.STEP)
    plan.add(ExportFormat.STL)
    plan.add(ExportFormat.DXF)
    plan.add(ExportFormat.GLB)
    plan.add(ExportFormat.TOPOLOGY)
    return part, plan


def build_base_mount_part() -> tuple[CadPartScript, ExportPlan]:
    part = CadPartScript(part_name="base_mount")
    plate = part.add_handle(
        name="mount_plate",
        selector='faces(">Z")',
        notes="Top plate used for robot base mounting",
    )
    hole_pattern = part.add_handle(
        name="bolt_pattern",
        selector='faces(">Z").workplane()',
        notes="Bolt hole pattern on the base plate",
    )
    part.add_feature("base_plate", "box", parameters={"width": 120, "height": 120, "depth": 8})
    part.add_feature("corner_relief", "fillet", handle=plate, parameters={"radius": 4})
    part.add_feature("mount_holes", "hole_pattern", handle=hole_pattern, parameters={"count": 4, "diameter": 6, "pitch": 90})
    part.set_source(
        """body = w.box(120, 120, 8)
body = body.edges("|Z").fillet(4)  # @cad: mount_plate
body = body.faces(">Z").workplane()  # @cad: bolt_pattern
body = body.rarray(90, 90, 2, 2).hole(6)
"""
    )
    part.add_export(ExportFormat.STEP.value)
    part.add_export(ExportFormat.STL.value)
    plan = ExportPlan(part=part)
    plan.add(ExportFormat.STEP)
    plan.add(ExportFormat.STL)
    plan.add(ExportFormat.TOPOLOGY)
    return part, plan
