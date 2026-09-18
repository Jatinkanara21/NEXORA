from __future__ import annotations
from pathlib import Path
import re
from core.models import AgentSpec, Artifact

def build_agent(name: str, capabilities: list[str], role: str | None = None, root: str = "agents") -> Path:
    slug = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "dynamic_agent"
    path = Path(root) / f"{slug}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    caps = sorted(set(capabilities))
    role_text = role or f"Dynamic agent for {name}"
    source = f"""from core.models import AgentSpec, Artifact

def run(context, tools):
    observations=[]
    for artifact_id, artifact in context.previous_artifacts.items():
        observations.append({{"artifact_id": artifact_id, "kind": artifact.get("kind", "artifact")}})
    data={{
        "agent": {name!r},
        "role": {role_text!r},
        "capabilities": {caps!r},
        "task": context.task,
        "observations": observations,
        "used_artifacts": list(context.previous_artifacts),
    }}
    return Artifact(id=f"{{context.task_id}}-{slug}", kind="dynamic_agent_analysis", producer={name!r}, data=data)

SPEC=AgentSpec(name={name!r}, role={role_text!r}, capabilities={caps!r}, handler=run)
"""
    path.write_text(source, encoding="utf-8")
    return path
