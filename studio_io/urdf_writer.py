"""URDF export from CAD assembly data.

Produces a valid URDF XML file with links, joints, and mesh references
from a robot model's link/joint graph.
"""

from __future__ import annotations

from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET


def _format_origin(xyz: tuple[float, float, float], rpy: tuple[float, float, float]) -> str:
    return f"{xyz[0]:.6g} {xyz[1]:.6g} {xyz[2]:.6g}"


def _format_axis(axis: tuple[float, float, float]) -> str:
    return f"{axis[0]:.6g} {axis[1]:.6g} {axis[2]:.6g}"


def write_urdf(
    path: str | Path,
    robot_name: str,
    links: list[str],
    joints: list[dict],
    mesh_dir: str = "meshes",
) -> bool:
    """Write a URDF file from link and joint definitions.

    Args:
        path: Output URDF file path.
        robot_name: Name of the robot.
        links: List of link names.
        joints: List of joint dicts, each with keys:
            name, type, parent, child,
            origin_xyz (optional), origin_rpy (optional),
            axis_xyz (optional),
            lower, upper (optional, radians).
        mesh_dir: Relative directory for mesh file references.

    Returns True on success.
    """
    robot = ET.Element("robot", name=robot_name)

    for link_name in links:
        link = ET.SubElement(robot, "link", name=link_name)
        visual = ET.SubElement(link, "visual")
        geometry = ET.SubElement(visual, "geometry")
        ET.SubElement(geometry, "mesh", filename=f"{mesh_dir}/{link_name}.stl")
        ET.SubElement(visual, "origin", xyz="0 0 0", rpy="0 0 0")

    for j in joints:
        joint = ET.SubElement(
            robot, "joint",
            name=j["name"],
            type=j.get("type", "revolute"),
        )
        ET.SubElement(joint, "parent", link=j["parent"])
        ET.SubElement(joint, "child", link=j["child"])

        origin_xyz = j.get("origin_xyz", (0.0, 0.0, 0.0))
        origin_rpy = j.get("origin_rpy", (0.0, 0.0, 0.0))
        ET.SubElement(joint, "origin",
                      xyz=_format_origin(origin_xyz, origin_rpy),
                      rpy=_format_origin(origin_rpy, origin_xyz))

        axis = j.get("axis_xyz", (0.0, 0.0, 1.0))
        ET.SubElement(joint, "axis", xyz=_format_axis(axis))

        lower = j.get("lower", 0.0)
        upper = j.get("upper", 0.0)
        ET.SubElement(joint, "limit",
                      lower=f"{lower:.6g}",
                      upper=f"{upper:.6g}",
                      effort=str(j.get("effort", "0")),
                      velocity=str(j.get("velocity", "0")))

    raw = ET.tostring(robot, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    try:
        Path(path).write_text(pretty, encoding="utf-8")
        return True
    except OSError:
        return False


def model_to_urdf_dict(robot_model) -> dict:
    """Extract link/joint dicts from a RobotModel for use with write_urdf."""
    from robot_model import RobotModel
    model: RobotModel = robot_model
    links = [link.name for link in model.links]
    joints = []
    for j in model.joints:
        joints.append({
            "name": j.name,
            "type": "revolute",
            "parent": j.parent,
            "child": j.child,
            "origin_xyz": j.origin_xyz,
            "origin_rpy": j.origin_rpy,
            "axis_xyz": j.axis_xyz,
            "lower": -3.1416,
            "upper": 3.1416,
            "effort": "10",
            "velocity": "2.0",
        })
    return {"links": links, "joints": joints}
