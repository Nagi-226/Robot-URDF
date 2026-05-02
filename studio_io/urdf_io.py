"""URDF file parsing, validation, and resource collection."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from robot_model import RobotJoint, RobotLink, RobotModel

URDF_HINTS = [".urdf", ".xacro", ".xml"]
RESOURCE_SUFFIXES = {".stl", ".dae", ".obj", ".step", ".stp", ".json", ".yaml", ".yml", ".launch", ".py", ".cfg", ".ini"}
PROJECT_HINTS = ["models", "assets", "configs", "logs", "firmware", "urdf"]


def validate_urdf_path(path: Path) -> list[str]:
    issues: list[str] = []
    if not path.exists():
        issues.append("file not found")
        return issues
    if path.suffix.lower() not in URDF_HINTS:
        issues.append("unexpected file extension")
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        issues.append("unable to read file")
        return issues
    if "<robot" not in text:
        issues.append("missing <robot> root tag")
    if "link" not in text:
        issues.append("no link definitions found")
    if "joint" not in text:
        issues.append("no joint definitions found")
    return issues


def _parse_origin(element: ET.Element) -> dict:
    origin = element.find("origin")
    if origin is not None:
        xyz = origin.attrib.get("xyz", "0 0 0")
        rpy = origin.attrib.get("rpy", "0 0 0")
        return {
            "xyz": [float(v) for v in xyz.split()],
            "rpy": [float(v) for v in rpy.split()],
        }
    return {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]}


def _parse_axis(element: ET.Element) -> list[float]:
    axis = element.find("axis")
    if axis is not None:
        xyz = axis.attrib.get("xyz", "0 0 0")
        return [float(v) for v in xyz.split()]
    return [0.0, 0.0, 1.0]


def _parse_limit(element: ET.Element) -> dict | None:
    limit = element.find("limit")
    if limit is None:
        return None
    return {
        "lower": float(limit.attrib.get("lower", "0")),
        "upper": float(limit.attrib.get("upper", "0")),
        "effort": float(limit.attrib.get("effort", "0")),
        "velocity": float(limit.attrib.get("velocity", "0")),
    }


def parse_urdf_file(path: Path) -> dict | None:
    """Parse a URDF file and return a summary dict. Returns None on failure."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None

    robot_name = root.attrib.get("name", path.stem)
    links = [node.attrib.get("name", "unnamed_link") for node in root.findall(".//link")]
    joints: list[tuple[str, str, str]] = []
    joint_specs: list[dict] = []
    warnings: list[str] = []
    for joint in root.findall(".//joint"):
        name = joint.attrib.get("name", "unnamed_joint")
        jtype = joint.attrib.get("type", "revolute")
        parent = joint.find("parent")
        child = joint.find("child")
        parent_name = parent.attrib.get("link", "unknown") if parent is not None else "unknown"
        child_name = child.attrib.get("link", "unknown") if child is not None else "unknown"
        joints.append((name, parent_name, child_name))
        if parent is None or child is None:
            warnings.append(f"joint '{name}' is missing parent or child link")

        limits = _parse_limit(joint)
        origin = _parse_origin(joint)
        axis = _parse_axis(joint)
        lower = limits["lower"] if limits else -180.0
        upper = limits["upper"] if limits else 180.0
        joint_specs.append({
            "name": name,
            "type": jtype,
            "parent": parent_name,
            "child": child_name,
            "lower": lower,
            "upper": upper,
            "default": max(lower, min(0.0, upper)),
            "axis": axis,
            "origin_xyz": origin["xyz"],
            "origin_rpy": origin["rpy"],
        })

    if not links:
        warnings.append("no link definitions were parsed")
    if not joints:
        warnings.append("no joint definitions were parsed")

    return {
        "robot_name": robot_name,
        "links": links,
        "joints": joints,
        "joint_specs": joint_specs,
        "warnings": warnings,
    }


def collect_related_resources(path: Path) -> list[str]:
    root = path.parent
    resources: list[str] = [path.name]
    for candidate in sorted(root.iterdir() if root.exists() else []):
        if candidate == path:
            continue
        if candidate.is_dir() and candidate.name.lower() in PROJECT_HINTS:
            resources.append(f"{candidate.name}/")
            continue
        if candidate.suffix.lower() in RESOURCE_SUFFIXES or candidate.name.lower().endswith(".urdf"):
            resources.append(candidate.name)
    if len(resources) == 1:
        resources.append("No adjacent robot assets found")
    return resources


def convert_summary_to_model(summary: dict | None) -> RobotModel:
    if summary is None:
        return RobotModel()
    joint_specs = {s["name"]: s for s in summary.get("joint_specs", [])}
    _joints = []
    for name, parent, child in summary["joints"]:
        spec = joint_specs.get(name, {})
        origin = tuple(spec.get("origin_xyz", (0.0, 0.0, 0.0)))
        rpy = tuple(spec.get("origin_rpy", (0.0, 0.0, 0.0)))
        axis = tuple(spec.get("axis", (0.0, 0.0, 1.0)))
        _joints.append(RobotJoint(
            name=name, parent=parent, child=child,
            origin_xyz=origin, origin_rpy=rpy, axis_xyz=axis,
        ))
    return RobotModel(
        name=summary["robot_name"],
        links=[RobotLink(name=link) for link in summary["links"]],
        joints=_joints,
        warnings=list(summary.get("warnings", [])),
    )
