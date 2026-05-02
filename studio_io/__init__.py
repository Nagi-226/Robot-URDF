"""I/O package for serial, CAN, TCP, file import/export, and device adapters.

Named ``studio_io`` to avoid collision with Python's stdlib ``io`` module.
"""

from studio_io.file_io import populate_project_tree_hints
from studio_io.mesh_data import MeshData, MeshPart
from studio_io.mesh_loader import (
    build_primitive_mesh,
    load_glb_mesh,
    load_mesh_auto,
    load_stl_mesh,
)
from studio_io.urdf_io import (
    collect_related_resources,
    convert_summary_to_model,
    parse_urdf_file,
    validate_urdf_path,
)
from studio_io.urdf_mesh_builder import build_urdf_mesh_data, pose_urdf_mesh_parts
from studio_io.urdf_writer import model_to_urdf_dict, write_urdf

__all__ = [
    "MeshData",
    "MeshPart",
    "build_primitive_mesh",
    "build_urdf_mesh_data",
    "collect_related_resources",
    "convert_summary_to_model",
    "load_glb_mesh",
    "load_mesh_auto",
    "load_stl_mesh",
    "model_to_urdf_dict",
    "parse_urdf_file",
    "populate_project_tree_hints",
    "pose_urdf_mesh_parts",
    "validate_urdf_path",
    "write_urdf",
]
