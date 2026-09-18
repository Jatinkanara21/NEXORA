from __future__ import annotations
import re
class TextEngine:
    def extract(self, text: str) -> dict:
        urls=re.findall(r'https?://[^\s<>()]+', text); emails=re.findall(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b', text)
        numbers=re.findall(r'(?<!\w)\d+(?:\.\d+)?%?', text)
        return {'urls':urls,'emails':emails,'numbers':numbers}
