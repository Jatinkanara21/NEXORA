from __future__ import annotations
import re
from collections import Counter
URL_RE = re.compile(r'https?://[^\s<>()]+')
EMAIL_RE = re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b')

def analyze_text(payload: dict) -> dict:
    text = str(payload.get('text', ''))
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_'’-]*", text.lower())
    stop = {'the','a','an','and','or','is','are','to','of','in','on','for','with','this','that','it','as','be','by'}
    freq = Counter(w for w in words if w not in stop and len(w) > 2)
    questions = [s for s in sentences if '?' in s]
    commands = [s for s in sentences if re.match(r'^(analyze|inspect|calculate|find|explain|create|build|show|list|verify)\b', s, re.I)]
    return {'characters': len(text), 'words': len(words), 'sentences': len(sentences), 'keywords':[w for w,_ in freq.most_common(10)], 'questions':len(questions), 'questions_text':questions, 'commands':commands, 'urls':URL_RE.findall(text), 'emails':EMAIL_RE.findall(text), 'repeated_terms':[{'term':w,'count':c} for w,c in freq.items() if c>1]}
