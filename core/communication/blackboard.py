from __future__ import annotations
from copy import deepcopy
from threading import RLock
from typing import Any

class Blackboard:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state: dict[str, Any] = {
            "task": "", "status": "idle", "messages": [], "artifacts": {},
            "events": [], "facts": [], "decisions": [], "errors": []
        }
    def reset(self, task: str) -> None:
        with self._lock:
            self._state = {"task": task, "status": "running", "messages": [], "artifacts": {}, "events": [], "facts": [], "decisions": [], "errors": []}
    def publish_message(self, agent: str, message: dict[str, Any]) -> None:
        with self._lock: self._state["messages"].append({"agent": agent, "message": deepcopy(message)})
    def publish_artifact(self, artifact: Any) -> None:
        with self._lock: self._state["artifacts"][artifact.id] = deepcopy(artifact.data | {"kind": artifact.kind, "producer": artifact.producer})
    def add_event(self, event: str, metadata: dict[str, Any] | None = None) -> None:
        with self._lock: self._state["events"].append({"event": event, "metadata": deepcopy(metadata or {})})
    def add_fact(self, fact: Any) -> None:
        with self._lock: self._state["facts"].append(deepcopy(fact))
    def add_decision(self, decision: Any) -> None:
        with self._lock: self._state["decisions"].append(deepcopy(decision))
    def add_error(self, error: Any) -> None:
        with self._lock: self._state["errors"].append(deepcopy(error))
    def snapshot(self) -> dict[str, Any]:
        with self._lock: return deepcopy(self._state)
