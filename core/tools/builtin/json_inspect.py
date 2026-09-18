import json

def inspect_json(payload: dict) -> dict:
    raw = payload.get('json')
    value = raw if not isinstance(raw,str) else json.loads(raw)
    counts={'objects':0,'arrays':0,'primitives':0}
    def walk(v, depth=1):
        counts['objects' if isinstance(v,dict) else 'arrays' if isinstance(v,list) else 'primitives'] += 1
        if isinstance(v,dict):
            for x in v.values(): walk(x, depth+1)
        elif isinstance(v,list):
            for x in v: walk(x, depth+1)
    walk(value)
    def max_depth(v,d=1):
        if isinstance(v,dict): return max([d]+[max_depth(x,d+1) for x in v.values()])
        if isinstance(v,list): return max([d]+[max_depth(x,d+1) for x in v])
        return d
    return {'valid':True,'root_type':type(value).__name__,'top_level_keys':list(value.keys()) if isinstance(value,dict) else [],'array_lengths':[len(v) for v in value.values() if isinstance(value,dict) and isinstance(v,list)] if isinstance(value,dict) else [len(value)] if isinstance(value,list) else [],'counts':counts,'max_depth':max_depth(value)}
