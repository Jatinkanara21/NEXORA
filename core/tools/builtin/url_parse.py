from urllib.parse import urlparse, parse_qs

def parse_url(payload: dict) -> dict:
    raw = str(payload.get('url','')).strip()
    p = urlparse(raw)
    if p.scheme not in {'http','https'} or not p.hostname: raise ValueError('Invalid HTTP(S) URL')
    labels = p.hostname.split('.')
    domain = '.'.join(labels[-2:]) if len(labels) >= 2 else p.hostname
    subdomain = '.'.join(labels[:-2]) if len(labels) > 2 else ''
    return {'scheme':p.scheme,'hostname':p.hostname,'port':p.port,'path':p.path,'query':p.query,'query_params':parse_qs(p.query),'fragment':p.fragment,'domain':domain,'subdomain':subdomain}
