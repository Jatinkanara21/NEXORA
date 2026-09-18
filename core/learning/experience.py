from __future__ import annotations
import json
import time
from pathlib import Path

class ExperienceStore:
    def __init__(self, path: str = "data/experiences.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.records = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.records, list):
                self.records = []
        except (FileNotFoundError, ValueError):
            self.records = []

    def record(self, item: dict) -> None:
        self.records = (self.records + [{**item, "timestamp": time.time()}])[-1000:]
        self.path.write_text(json.dumps(self.records, indent=2, default=str), encoding="utf-8")

    def agent_success_rate(self, agent: str, intent: str | None = None) -> float:
        rows = [r for r in self.records if r.get("agent") == agent and (intent is None or r.get("intent") == intent)]
        return 0.5 if not rows else sum(bool(r.get("success")) for r in rows) / len(rows)
