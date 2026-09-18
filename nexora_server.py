from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from core.runtime import Runtime

RUNTIME=Runtime()

HTML="""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>NEXORA</title>
<style>body{margin:0;background:#0b0e14;color:#eef;font:14px system-ui}main{max-width:1200px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.card{background:#111722;border:1px solid #293348;border-radius:16px;padding:16px}.row{display:flex;gap:8px}input{flex:1}input,button{padding:12px;border-radius:10px;border:1px solid #33405a;background:#0c111a;color:#fff}button{cursor:pointer}pre{white-space:pre-wrap;max-height:500px;overflow:auto}.muted{color:#96a0b8}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style></head>
<body><main><h1>NEXORA</h1><div class='muted'>Local deterministic multi-agent execution</div><div class='card' style='margin-top:16px'><div class='row'><input id='task' placeholder='Enter a real task'><button onclick='runTask()'>Run</button></div></div>
<div class='grid' style='margin-top:14px'><div class='card'><h2>Execution</h2><pre id='execution'>Ready.</pre></div><div class='card'><h2>Final Answer</h2><pre id='answer'>No result yet.</pre></div>
<div class='card'><h2>Agents</h2><pre id='agents'>Loading…</pre></div><div class='card'><h2>Tools</h2><pre id='tools'>Loading…</pre></div><div class='card'><h2>Blackboard</h2><pre id='blackboard'>No task yet.</pre></div><div class='card'><h2>Verification</h2><pre id='verification'>No task yet.</pre></div></div>
<script>
async function getJson(url,opts){return await (await fetch(url,opts)).json()}
async function load(){document.getElementById('agents').textContent=JSON.stringify(await getJson('/api/agents'),null,2);document.getElementById('tools').textContent=JSON.stringify(await getJson('/api/tools'),null,2)}
async function runTask(){const task=document.getElementById('task').value.trim();if(!task)return;const start=await getJson('/api/task',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task})});let id=start.task_id;for(let i=0;i<100;i++){const x=await getJson('/api/tasks/'+id);document.getElementById('execution').textContent=JSON.stringify({task_id:x.task_id,status:x.status,intent:x.intent,intent_confidence:x.intent_confidence,nodes:x.nodes,artifacts:Object.keys(x.artifacts||{})},null,2);document.getElementById('blackboard').textContent=JSON.stringify(x.blackboard||{},null,2);document.getElementById('verification').textContent=JSON.stringify(x.verification||{},null,2);document.getElementById('answer').textContent=x.final_answer||'Running…';if(['completed','failed'].includes(x.status))break;await new Promise(r=>setTimeout(r,100))}}
load()
</script></main></body></html>"""

def clean(value):
    from dataclasses import asdict, is_dataclass
    if is_dataclass(value): return asdict(value)
    if isinstance(value,list): return [clean(v) for v in value]
    if isinstance(value,dict): return {str(k):clean(v) for k,v in value.items()}
    return value

class Handler(BaseHTTPRequestHandler):
    def send_json(self,obj,status=200):
        data=json.dumps(clean(obj),ensure_ascii=False,default=str).encode()
        self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(HTML.encode()); return
        if path=='/api/status': return self.send_json({'name':'NEXORA','platform':'PC / Windows','mode':'local','external_ai':False,'dynamic_agents':True,'dynamic_tools':True,'adaptive_replanning':True,'local_memory':True,'verification':True,'learning':True})
        if path=='/api/health': return self.send_json({'ok':True,'agents':len(RUNTIME.agents),'tools':len(RUNTIME.tools.all())})
        if path=='/api/agents': return self.send_json([{'name':a.name,'role':a.role,'capabilities':a.capabilities,'enabled':a.enabled,'specialization':a.specialization} for a in RUNTIME.agents.values()])
        if path=='/api/tools': return self.send_json([{'name':t.name,'description':t.description,'capabilities':t.capabilities,'input_schema':t.input_schema,'safety_constraints':t.safety_constraints} for t in RUNTIME.tools.all()])
        if path=='/api/memory': return self.send_json(RUNTIME.memory.records)
        if path=='/api/tasks': return self.send_json(list(RUNTIME.tasks.values()))
        if path.startswith('/api/tasks/'):
            task=RUNTIME.tasks.get(path.rsplit('/',1)[-1]); return self.send_json(task if task else {'error':'task not found'},200 if task else 404)
        self.send_error(404)
    def do_POST(self):
        length=int(self.headers.get('Content-Length','0')); payload=json.loads(self.rfile.read(length) or '{}'); path=urlparse(self.path).path
        if path=='/api/task':
            task=str(payload.get('task','')).strip()
            if not task:return self.send_json({'error':'task is required'},400)
            task_id=RUNTIME.create_task(task); return self.send_json({'task_id':task_id,'status':'running'},202)
        if path=='/api/agents/create':
            from core.agents.builder import build_agent
            name=str(payload.get('name','')).strip(); caps=[str(x) for x in payload.get('capabilities',[])]
            if not name or not caps:return self.send_json({'error':'name and capabilities are required'},400)
            created=build_agent(name,caps,payload.get('role')); RUNTIME.discover_agents(); return self.send_json({'created':str(created),'agent_names':sorted(RUNTIME.agents)},201)
        self.send_error(404)

if __name__=='__main__':
    print('NEXORA listening on http://127.0.0.1:8000')
    ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
