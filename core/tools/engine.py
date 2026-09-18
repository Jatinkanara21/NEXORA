from __future__ import annotations
from typing import Any
from core.tools.registry import ToolRegistry

class ToolEngine:
    def __init__(self, registry: ToolRegistry): self.registry = registry
    def execute(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        spec = self.registry.get(name)
        try: return {"status": "completed", "tool": name, "result": spec.handler(payload)}
        except Exception as exc: return {"status": "failed", "tool": name, "error": str(exc)}
