from __future__ import annotations
import re

INTENT_RULES = {
    "greeting": (("hello","hi","hey"), 2),
    "help": (("help","what can you do","capabilities"), 3),
    "explain": (("explain","how does","what is"), 3),
    "analyze": (("analyze","analyse","analysis"), 4),
    "summarize": (("summarize","summary","summarise"), 4),
    "research": (("research","investigate"), 3),
    "search": (("search","look up","find"), 2),
    "compare": (("compare","difference","versus"," vs "), 3),
    "calculate": (("calculate","compute"), 4),
    "inspect": (("inspect","parse","structure"), 3),
    "validate": (("validate","check"), 2),
    "verify": (("verify","confirm"), 3),
    "create": (("create","make","generate"), 2),
    "build": (("build","develop","implement"), 2),
    "debug": (("debug","fix error","bug"), 4),
    "review": (("review","audit"), 3),
    "memory_search": (("in memory","memory","remember"), 4),
    "list_agents": (("list agents","available agents"), 5),
    "agent_status": (("agent status","agent health"), 5),
    "stop_task": (("stop task","cancel task"), 5),
}

def detect(text: str) -> dict:
    low = text.lower()
    scores = {name: 0.0 for name in INTENT_RULES}
    for name, (phrases, weight) in INTENT_RULES.items():
        for phrase in phrases:
            if phrase in low:
                scores[name] += weight
    if re.search(r"https?://", text):
        scores["inspect"] += 2
        scores["analyze"] += 2
    if ("{" in text and "}" in text) or ("[" in text and "]" in text):
        scores["inspect"] += 2
        scores["analyze"] += 1
    if re.search(r"d+(?:.d+)?s*(?:[+-*/]|*)s*d+", text):
        scores["calculate"] += 5
    if "%" in text and re.search(r"d", text):
        scores["calculate"] += 2
    if "?" in text:
        scores["explain"] += 1
    best = max(scores, key=scores.get)
    raw = scores[best]
    confidence = 0.15 if raw == 0 else min(0.99, 0.35 + raw * 0.08)
    return {"intent": best, "confidence": round(confidence, 2), "scores": dict(sorted(scores.items(), key=lambda x: -x[1]))}
