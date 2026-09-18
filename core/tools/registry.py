from __future__ import annotations
from core.models import ToolSpec

class ToolRegistry:
    def __init__(self) -> None: self._tools: dict[str, ToolSpec] = {}
    def register(self, spec: ToolSpec) -> None: self._tools[spec.name] = spec
    def get(self, name: str) -> ToolSpec: return self._tools[name]
    def all(self) -> list[ToolSpec]: return list(self._tools.values())
    def select(self, capabilities: list[str]) -> list[ToolSpec]:
        wanted = set(capabilities)
        scored = []
        for tool in self._tools.values():
            score = len(wanted.intersection(tool.capabilities)) / max(1, len(wanted))
            if score > 0: scored.append((score, tool))
        return [t for _, t in sorted(scored, key=lambda x: (-x[0], x[1].name))]
