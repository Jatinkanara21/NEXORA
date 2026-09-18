from __future__ import annotations
import re

def pattern_search(payload: dict) -> dict:
    text=str(payload.get('text','')); pattern=str(payload.get('pattern',''))
    matches=[]
    if pattern.startswith('re:'):
        rx=re.compile(pattern[3:]); matches=[{'match':m.group(0),'start':m.start(),'end':m.end()} for m in rx.finditer(text)]
    else:
        needle=pattern.lower(); start=0
        while needle:
            i=text.lower().find(needle,start)
            if i<0: break
            matches.append({'match':text[i:i+len(needle)],'start':i,'end':i+len(needle)}); start=i+len(needle)
    return {'pattern':pattern,'matches':matches,'count':len(matches)}
