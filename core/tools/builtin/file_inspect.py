from __future__ import annotations
from pathlib import Path
import json, ast

class SafeFileInspector:
    def __init__(self, roots): self.roots=[Path(r).resolve() for r in roots]
    def _safe(self, path):
        p=Path(path).resolve()
        if not any(p == r or r in p.parents for r in self.roots): raise PermissionError('Path is outside configured safe directories')
        return p
    def inspect(self, payload):
        p=self._safe(str(payload['path']))
        if not p.is_file(): raise FileNotFoundError(str(p))
        data=p.read_text(encoding='utf-8', errors='replace'); suffix=p.suffix.lower()
        result={'path':str(p),'extension':suffix,'bytes':p.stat().st_size,'lines':len(data.splitlines())}
        if suffix=='.json':
            try: result['json']=json.loads(data)
            except json.JSONDecodeError as exc: result['error']=f'invalid JSON: {exc}'
        elif suffix=='.py':
            try: result['python_ast_nodes']=sum(1 for _ in ast.walk(ast.parse(data)))
            except SyntaxError as exc: result['error']=f'python syntax error: {exc.msg} at line {exc.lineno}'
        result['head']=data[:2000]
        return result
