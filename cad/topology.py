from __future__ import annotations

from dataclasses import dataclass, field

from .part import CadPartScript


@dataclass(frozen=True)
class TopologyNode:
    name: str
    kind: str
    parent: str | None = None


@dataclass
class TopologyGraph:
    robot_name: str
    nodes: list[TopologyNode] = field(default_factory=list)

    def add_node(self, name: str, kind: str, parent: str | None = None) -> None:
        self.nodes.append(TopologyNode(name=name, kind=kind, parent=parent))

    def from_part(self, part: CadPartScript) -> None:
        self.add_node(part.part_name, "part")
        for handle in part.handles:
            self.add_node(handle.name, "handle", parent=part.part_name)
        for feature in part.features:
            self.add_node(feature.name, "feature", parent=part.part_name)

    def from_link_joint_graph(
        self,
        links: list[str],
        joints: list[tuple[str, str, str]],
    ) -> None:
        """Build topology from a robot structure description.

        Args:
            links: link names.
            joints: (parent_link, child_link, joint_name) tuples.
        """
        for link in links:
            self.add_node(link, "link")
        for parent, child, name in joints:
            self.add_node(name, "joint", parent=parent)
            if child not in {n.name for n in self.nodes}:
                self.add_node(child, "link", parent=parent)

    def summary(self) -> str:
        return f"TopologyGraph(robot={self.robot_name}, nodes={len(self.nodes)})"
