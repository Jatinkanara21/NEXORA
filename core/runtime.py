from __future__ import annotations
import importlib.util
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from core.communication.blackboard import Blackboard
from core.intelligence.intent import detect
from core.models import AgentContext, AgentSpec, Artifact, GraphNode
from core.tools.engine import ToolEngine
from core.tools.registry import ToolRegistry
from core.tools.builtin.file_inspect import SafeFileInspector
from core.tools.builtin.json_inspect import inspect_json
from core.tools.builtin.math_calculator import calculate
from core.tools.builtin.pattern_search import pattern_search
from core.tools.builtin.text_analyze import analyze_text
from core.tools.builtin.url_parse import parse_url


def _now() -> float:
    return round(time.time(), 3)


class LocalMemory:
    def __init__(self, path: str = "data/memory.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import json
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.records = data if isinstance(data, list) else []
        except (FileNotFoundError, ValueError):
            self.records = []

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        import json
        terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
        ranked = []
        for record in self.records:
            text = json.dumps(record, ensure_ascii=False).lower()
            tokens = set(re.findall(r"[a-z0-9_]+", text))
            overlap = len(terms & tokens)
            if overlap:
                ranked.append({"score": round(overlap / max(1, len(terms)), 3), "content": record, "source": "memory"})
        return sorted(ranked, key=lambda item: (-item["score"], str(item["content"])))[:limit]

    def add(self, record: dict[str, Any]) -> None:
        import json
        self.records = (self.records + [record])[-500:]
        self.path.write_text(json.dumps(self.records, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


class ExperienceStore:
    def __init__(self, path: str = "data/experiences.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import json
            self.records = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.records, list):
                self.records = []
        except (FileNotFoundError, ValueError):
            self.records = []

    def add(self, record: dict[str, Any]) -> None:
        import json
        self.records = (self.records + [{**record, "timestamp": _now()}])[-1000:]
        self.path.write_text(json.dumps(self.records, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def score(self, agent: str, intent: str) -> float:
        rows = [r for r in self.records if r.get("agent") == agent and r.get("intent") == intent]
        if not rows:
            return 0.5
        return sum(bool(r.get("success")) for r in rows) / len(rows)


class Runtime:
    def __init__(self) -> None:
        self.blackboard = Blackboard()
        self.memory = LocalMemory()
        self.experience = ExperienceStore()
        self.tools = ToolRegistry()
        self.tool_engine = ToolEngine(self.tools)
        self.agents: dict[str, AgentSpec] = {}
        self.tasks: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._register_tools()
        self.discover_agents()

    def _register_tools(self) -> None:
        from core.models import ToolSpec
        self.tools.register(ToolSpec("text_analyze", "Analyze text structure and keywords", ["analyze", "extract", "summarize"], {"text": "string"}, analyze_text, ["text only"]))
        self.tools.register(ToolSpec("math_calculator", "Safe AST math calculator", ["calculate"], {"expression": "string"}, calculate, ["no eval; numeric operators only"]))
        self.tools.register(ToolSpec("url_parse", "Parse HTTP(S) URLs without fetching", ["inspect", "url_parse"], {"url": "string"}, parse_url, ["no network access"]))
        self.tools.register(ToolSpec("json_inspect", "Inspect JSON structure", ["inspect", "json_inspect"], {"json": "string|object"}, inspect_json, ["no code execution"]))
        self.tools.register(ToolSpec("pattern_search", "Search local text for literal or regex patterns", ["analyze", "search"], {"text": "string", "pattern": "string"}, pattern_search, ["regex is local only"]))
        roots = os.environ.get("NEXORA_SAFE_ROOTS", str(Path.cwd())).split(os.pathsep)
        inspector = SafeFileInspector(roots)
        self.tools.register(ToolSpec("file_inspect", "Inspect a file only inside configured safe roots", ["inspect", "file_search"], {"path": "string"}, inspector.inspect, [f"allowed roots: {roots}"]))

    def discover_agents(self) -> dict[str, AgentSpec]:
        discovered: dict[str, AgentSpec] = {}
        root = Path("agents")
        root.mkdir(exist_ok=True)
        for path in sorted(root.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                module_name = f"nexora_dynamic_{path.stem}_{path.stat().st_mtime_ns}"
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(module)
                candidate = getattr(module, "SPEC", None)
                if isinstance(candidate, AgentSpec):
                    discovered[candidate.name] = candidate
            except Exception:
                continue
        discovered.update(self._builtin_agents())
        with self._lock:
            self.agents = discovered
        return discovered

    def _builtin_agents(self) -> dict[str, AgentSpec]:
        def planner(context: AgentContext, tools: ToolRegistry) -> Artifact:
            return Artifact(str(uuid.uuid4()), "plan", "planner", {"intent": context.intent, "operations": context.input_data.get("operations", [])})

        def research(context: AgentContext, tools: ToolRegistry) -> Artifact:
            matches = self.memory.search(context.task)
            return Artifact(str(uuid.uuid4()), "memory_results", "research", {"matches": matches, "count": len(matches)})

        def reasoning(context: AgentContext, tools: ToolRegistry) -> Artifact:
            observations = []
            facts = []
            for aid, item in context.previous_artifacts.items():
                data = item.get("data", item)
                observations.append({"artifact_id": aid, "kind": item.get("kind", "artifact")})
                if isinstance(data, dict) and data.get("result") is not None:
                    facts.append({"artifact_id": aid, "result": data["result"]})
            return Artifact(str(uuid.uuid4()), "reasoning", "reasoning", {
                "facts": facts,
                "observations": observations,
                "relationships": [],
                "conclusions": facts or observations,
                "uncertainties": ["Deterministic reasoning uses only locally produced evidence."],
                "confidence": 0.8 if observations else 0.4,
            })

        def verifier(context: AgentContext, tools: ToolRegistry) -> Artifact:
            required = context.input_data.get("required_artifact_count", 0)
            actual = len(context.previous_artifacts)
            passed = actual >= required
            return Artifact(str(uuid.uuid4()), "verification", "verifier", {
                "verified": passed,
                "checks": [
                    {"check": "required_artifacts_present", "passed": passed, "expected": required, "actual": actual},
                    {"check": "non_empty_task", "passed": bool(context.task.strip())},
                ],
                "warnings": [] if passed else ["One or more required artifacts are missing."],
                "missing": [] if passed else ["required artifacts"],
                "confidence": 0.95 if passed else 0.35,
            })

        def orchestrator(context: AgentContext, tools: ToolRegistry) -> Artifact:
            return Artifact(str(uuid.uuid4()), "orchestration", "orchestrator", {"task_id": context.task_id, "intent": context.intent, "artifact_count": len(context.previous_artifacts)})

        return {
            "planner": AgentSpec("planner", "Task-specific plan generation", ["planning", "decompose", "graph_generation"], planner),
            "research": AgentSpec("research", "Local evidence retrieval", ["search", "memory_search", "evidence"], research),
            "reasoning": AgentSpec("reasoning", "Deterministic reasoning", ["reason", "analyze", "compare", "explain"], reasoning),
            "verifier": AgentSpec("verifier", "Result verification", ["verify", "validate", "consistency_check"], verifier),
            "orchestrator": AgentSpec("orchestrator", "Task coordination", ["orchestrate"], orchestrator),
        }

    def _select_agent(self, node: GraphNode, intent: str) -> AgentSpec:
        best: AgentSpec | None = None
        best_score = float("-inf")
        for agent in self.agents.values():
            if not agent.enabled:
                continue
            score = 4 * len(set(node.required_capabilities) & set(agent.capabilities))
            score += self.experience.score(agent.name, intent)
            objective = node.objective.lower()
            if "verify" in objective and agent.name == "verifier":
                score += 4
            if "search" in objective and agent.name == "research":
                score += 4
            if "plan" in objective and agent.name == "planner":
                score += 4
            if best is None or score > best_score:
                best, best_score = agent, score
        if best is None:
            raise RuntimeError("No enabled agent can execute the task node")
        return best

    def _select_tool(self, node: GraphNode, task: str) -> str | None:
        low = task.lower()
        if "http://" in low or "https://" in low:
            return "url_parse"
        if ("{" in task and "}" in task) or ("[" in task and "]" in task):
            return "json_inspect"
        if node.intent == "calculate":
            return "math_calculator"
        if node.objective.startswith("inspect"):
            return "text_analyze"
        candidates = self.tools.select(node.required_capabilities)
        return candidates[0].name if candidates else None

    def _operations(self, task: str, intent: str) -> list[dict[str, Any]]:
        low = task.lower()
        if intent == "calculate":
            return [{"objective": "calculate expression", "capabilities": ["calculate"]}, {"objective": "verify numeric result", "capabilities": ["verify"]}]
        if "http://" in low or "https://" in low:
            return [{"objective": "inspect URL structure", "capabilities": ["inspect", "url_parse"]}, {"objective": "verify parsed URL", "capabilities": ["verify"]}]
        if ("{" in task and "}" in task) or ("[" in task and "]" in task):
            return [{"objective": "inspect JSON structure", "capabilities": ["inspect", "json_inspect"]}, {"objective": "verify JSON analysis", "capabilities": ["verify"]}]
        if intent == "memory_search":
            return [{"objective": "search local memory", "capabilities": ["memory_search"]}, {"objective": "verify evidence coverage", "capabilities": ["verify"]}]
        if intent in {"analyze", "inspect", "summarize"}:
            return [{"objective": "inspect task input", "capabilities": ["inspect"]}, {"objective": "analyze extracted evidence", "capabilities": ["analyze", "reason"]}, {"objective": "verify analysis", "capabilities": ["verify"]}]
        if intent in {"research", "search", "compare", "review", "validate"}:
            return [{"objective": "search local evidence", "capabilities": ["memory_search", "search"]}, {"objective": "reason over evidence", "capabilities": ["reason", "analyze"]}, {"objective": "verify findings", "capabilities": ["verify"]}]
        return [{"objective": "understand task", "capabilities": ["analyze"]}, {"objective": "synthesize response", "capabilities": ["explain"]}]

    def _run_node(self, task_id: str, node: GraphNode) -> None:
        task_record = self.tasks[task_id]
        task = task_record["task"]
        node.status = "running"
        node.attempts += 1
        self.blackboard.add_event("step_started", {"task_id": task_id, "node": node.id})
        agent = self._select_agent(node, task_record["intent"])
        node.assigned_agent = agent.name
        tool_name = self._select_tool(node, task)
        node.selected_tools = [tool_name] if tool_name else []
        context = AgentContext(
            task_id=task_id,
            task=task,
            intent=task_record["intent"],
            goal=task,
            input_data={"operations": task_record["operations"], "required_artifact_count": max(0, len(node.depends_on))},
            capabilities=node.required_capabilities,
            previous_artifacts=dict(task_record["artifacts"]),
            blackboard=self.blackboard.snapshot(),
            current_graph_node={
                "id": node.id,
                "objective": node.objective,
                "depends_on": node.depends_on,
                "attempts": node.attempts,
            },
            selected_tools=node.selected_tools,
            available_agents=[{"name": a.name, "capabilities": a.capabilities} for a in self.agents.values()],
            memory_results=self.memory.search(task),
            execution_history=self.experience.records[-20:],
        )

        # Tool-first execution for concrete tasks.
        if node.intent == "calculate" and node.objective.startswith("calculate"):
            expr = re.split(r"calculate\s*", task, flags=re.I, maxsplit=1)[-1].strip().rstrip("?")
            result = self.tool_engine.execute("math_calculator", {"expression": expr})
            if result["status"] != "completed":
                raise RuntimeError(result["error"])
            artifact = Artifact(str(uuid.uuid4()), "math_result", "math_calculator", result["result"])
        elif "URL" in node.objective:
            match = re.search(r"https?://[^\s]+", task)
            if not match:
                raise ValueError("No URL found in task")
            result = self.tool_engine.execute("url_parse", {"url": match.group(0).rstrip(".,)")})
            if result["status"] != "completed":
                raise RuntimeError(result["error"])
            artifact = Artifact(str(uuid.uuid4()), "url_analysis", "url_parse", result["result"])
        elif "JSON" in node.objective:
            raw = task.split(":", 1)[-1].strip()
            result = self.tool_engine.execute("json_inspect", {"json": raw})
            if result["status"] != "completed":
                raise RuntimeError(result["error"])
            artifact = Artifact(str(uuid.uuid4()), "json_analysis", "json_inspect", result["result"])
        elif node.objective.startswith("inspect task input"):
            result = self.tool_engine.execute("text_analyze", {"text": task})
            if result["status"] != "completed":
                raise RuntimeError(result["error"])
            artifact = Artifact(str(uuid.uuid4()), "text_analysis", "text_analyze", result["result"])
        else:
            artifact = agent.handler(context, self.tools)

        if not isinstance(artifact, Artifact):
            raise TypeError("Agent handler must return Artifact")
        task_record["artifacts"][artifact.id] = {"kind": artifact.kind, "producer": artifact.producer, "data": artifact.data}
        node.artifact_ids.append(artifact.id)
        node.status = "completed"
        self.blackboard.publish_artifact(artifact)
        self.blackboard.publish_message(agent.name, {"node": node.id, "artifact_id": artifact.id, "tool": tool_name})
        self.blackboard.add_event("artifact_created", {"task_id": task_id, "artifact_id": artifact.id, "kind": artifact.kind})
        self.experience.add({"agent": agent.name, "intent": task_record["intent"], "success": True, "node": node.id, "latency_ms": 0})

    def execute(self, task: str) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        intent_result = detect(task)
        intent = intent_result["intent"]
        operations = self._operations(task, intent)
        nodes = [GraphNode(f"step_{i+1}", op["objective"], intent, op["capabilities"], [f"step_{i}"] if i else []) for i, op in enumerate(operations)]
        with self._lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "task": task,
                "status": "running",
                "intent": intent,
                "intent_confidence": intent_result["confidence"],
                "intent_scores": intent_result["scores"],
                "operations": operations,
                "nodes": nodes,
                "artifacts": {},
                "events": [],
                "blackboard": {},
                "final_answer": "",
                "verification": {},
                "confidence": 0.0,
                "started_at": _now(),
            }
        self.blackboard.reset(task)
        self.blackboard.add_event("goal_created", {"task_id": task_id})
        self.blackboard.add_event("intent_detected", {"task_id": task_id, "intent": intent, "confidence": intent_result["confidence"]})

        pending = set(range(len(nodes)))
        while pending:
            ready = [i for i in pending if all(nodes[int(dep.split("_")[1]) - 1].status == "completed" for dep in nodes[i].depends_on)]
            if not ready:
                break
            with ThreadPoolExecutor(max_workers=max(1, len(ready))) as pool:
                futures = {pool.submit(self._run_node, task_id, nodes[i]): i for i in ready}
                for future, index in [(future, futures[future]) for future in futures]:
                    try:
                        future.result()
                    except Exception as exc:
                        node = nodes[index]
                        node.status = "failed"
                        node.error = str(exc)
                        self.blackboard.add_error({"node": node.id, "error": str(exc)})
                        self.experience.add({"agent": node.assigned_agent or "none", "intent": intent, "success": False, "node": node.id, "failure_reason": str(exc)})
                        alternatives = [a for a in self.agents.values() if a.enabled and a.name != node.assigned_agent and set(node.required_capabilities) & set(a.capabilities)]
                        if alternatives and node.attempts < 2:
                            node.assigned_agent = alternatives[0].name
                            node.status = "pending"
                        else:
                            node.status = "blocked"
            pending = {i for i in pending if nodes[i].status in {"pending", "failed"}}
            if any(node.status == "blocked" for node in nodes):
                break

        completed = all(node.status == "completed" for node in nodes)
        verification_artifacts = [a for a in self.tasks[task_id]["artifacts"].values() if a["kind"] == "verification"]
        verification = verification_artifacts[-1]["data"] if verification_artifacts else {"verified": False, "checks": [], "warnings": ["No verifier artifact produced."], "missing": ["verification"], "confidence": 0.2}
        answer = self._synthesize(task, intent, self.tasks[task_id]["artifacts"])
        self.tasks[task_id].update({
            "status": "completed" if completed and verification.get("verified", False) else "failed",
            "final_answer": answer,
            "verification": verification,
            "confidence": float(verification.get("confidence", 0.2)),
            "blackboard": self.blackboard.snapshot(),
            "finished_at": _now(),
        })
        self.blackboard.add_event("goal_finished", {"task_id": task_id, "status": self.tasks[task_id]["status"]})
        self.memory.add({"task": task, "intent": intent, "answer": answer, "confidence": self.tasks[task_id]["confidence"]})
        return self.tasks[task_id]

    def _synthesize(self, task: str, intent: str, artifacts: dict[str, Any]) -> str:
        out = []
        for item in artifacts.values():
            kind, data = item["kind"], item["data"]
            if kind == "math_result":
                out.append(f"Result: {data['result']}")
            elif kind == "url_analysis":
                fields = ["scheme", "hostname", "port", "path", "query", "fragment", "domain", "subdomain"]
                out.append("URL: " + "; ".join(f"{k}={data.get(k)}" for k in fields))
            elif kind == "json_analysis":
                out.append(f"JSON: root={data.get('root_type')}, depth={data.get('max_depth')}, counts={data.get('counts')}, keys={data.get('top_level_keys')}")
            elif kind == "text_analysis":
                out.append(f"Text: {data.get('words')} words, {data.get('sentences')} sentences; keywords={data.get('keywords')}")
            elif kind == "memory_results":
                out.append(f"Memory search found {data.get('count', 0)} matching record(s).")
            elif kind == "reasoning":
                out.append(f"Reasoning evidence: {data.get('conclusions')}")
        return "\n".join(out) if out else f"No task-specific evidence was produced for: {task}"
