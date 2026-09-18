from __future__ import annotations
from dataclasses import dataclass, field
from core.models import GraphNode

@dataclass
class TaskGraph:
    nodes: list[GraphNode] = field(default_factory=list)

    def ready(self) -> list[GraphNode]:
        done = {n.id for n in self.nodes if n.status == "completed"}
        return [n for n in self.nodes if n.status == "pending" and all(dep in done for dep in n.depends_on)]

    def valid(self) -> bool:
        ids = {n.id for n in self.nodes}
        return all(dep in ids for n in self.nodes for dep in n.depends_on)
