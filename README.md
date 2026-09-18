# NEXORA

NEXORA is a local-first deterministic multi-agent intelligence framework. It performs task understanding, intent detection, capability matching, dynamic planning, dependency-aware execution, artifact exchange, verification, synthesis, memory and learning without external AI models or APIs.

## Guarantees
- No OpenAI/Gemini/Claude/Ollama/Hugging Face inference or cloud AI APIs.
- Python standard library only for the runtime.
- Safe local tools with explicit filesystem boundaries.
- Dynamic agent discovery from `agents/`.
- Dynamic tool discovery from the tool registry.
- Structured artifacts and shared blackboard state.
- Adaptive retries/replanning and persistent execution history.

## Architecture
```text
User → Understanding → Intent → Capabilities → Tools → Planner → Task Graph
    → Agents ↔ Blackboard → Artifacts → Verification → Synthesis → Memory/Learning
```

## Run
```powershell
python nexora_server.py
```
Open `http://127.0.0.1:8000`.

## Local execution examples
- `Explain NEXORA`
- `Calculate 500 * 18%`
- `Analyze this URL: https://example.com/test?a=10`
- `Analyze this text: NEXORA connects agents, tools, memory and verification.`
- `Find information about agents in memory.`
- `Inspect this JSON: {"agents": ["planner", "reasoning"]}`

## Dynamic agents
Create an agent through `POST /api/agents/create` with a name and capabilities. The next discovery cycle loads it automatically; no central registration edit is required.

## Security
Shell execution and arbitrary Python execution are intentionally absent. File inspection is restricted to configured safe directories. Math expressions are parsed with `ast`, never `eval()`.
