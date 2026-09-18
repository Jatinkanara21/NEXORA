from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from time import time

@dataclass
class AgentContext:
    task_id: str
    task: str
    intent: str
    goal: str
    input_data: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    previous_artifacts: dict[str, Any] = field(default_factory=dict)
    blackboard: dict[str, Any] = field(default_factory=dict)
    current_graph_node: dict[str, Any] | None = None
    selected_tools: list[str] = field(default_factory=list)
    available_agents: list[dict[str, Any]] = field(default_factory=list)
    memory_results: list[dict[str, Any]] = field(default_factory=list)
    execution_history: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class Artifact:
    id: str
    kind: str
    producer: str
    data: dict[str, Any]
    created_at: float = field(default_factory=time)

@dataclass
class ToolSpec:
    name: str
    description: str
    capabilities: list[str]
    input_schema: dict[str, Any]
    handler: Any
    safety_constraints: list[str] = field(default_factory=list)

@dataclass
class AgentSpec:
    name: str
    role: str
    capabilities: list[str]
    handler: Any
    enabled: bool = True
    specialization: list[str] = field(default_factory=list)

@dataclass
class GraphNode:
    id: str
    objective: str
    intent: str
    required_capabilities: list[str]
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    attempts: int = 0
    assigned_agent: str | None = None
    selected_tools: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    error: str | None = None

@dataclass
class VerificationResult:
    verified: bool
    checks: list[dict[str, Any]]
    warnings: list[str]
    missing: list[str]
    confidence: float


def serializable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict
        return {k: serializable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serializable(v) for v in value]
    return value
