from __future__ import annotations
from core.models import ToolSpec

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def select(self, capabilities: list[str]) -> list[ToolSpec]:
        wanted = set(capabilities)
        scored = []
        for tool in self._tools.values():
            overlap = wanted.intersection(tool.capabilities)
            if overlap:
                score = len(overlap) / max(1, len(wanted))
                scored.append((score, tool))
        return [tool for _, tool in sorted(scored, key=lambda pair: (-pair[0], pair[1].name))]
