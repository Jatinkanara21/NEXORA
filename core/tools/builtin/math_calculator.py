from __future__ import annotations
import ast, operator, re
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}

def calculate(payload: dict) -> dict:
    raw = str(payload.get('expression','')).strip().replace('%','/100')
    if not re.fullmatch(r'[0-9+\-*/().\s]+', raw): raise ValueError('Expression contains unsupported characters')
    tree = ast.parse(raw, mode='eval')
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int,float)): return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, (ast.Pow,)) and abs(right) > 20: raise ValueError('Power is too large')
            return OPS[type(node.op)](left,right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS: return OPS[type(node.op)](ev(node.operand))
        raise ValueError('Unsupported expression')
    result = ev(tree.body)
    return {'expression': str(payload.get('expression','')), 'normalized': raw, 'result': result}
