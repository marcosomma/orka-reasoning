import redis
import json

r = redis.from_url('redis://localhost:6380/0')
keys = list(r.scan_iter('orka_memory:*'))
found = {'join_results': [], 'routing_decision': []}
for k in keys:
    try:
        content = r.hget(k, 'content')
        if not content:
            continue
        s = content.decode('utf-8')
        if 'join_results' in s:
            found['join_results'].append({'key': k.decode(), 'preview': s[:800]})
        if 'routing_decision' in s:
            found['routing_decision'].append({'key': k.decode(), 'preview': s[:800]})
    except Exception as e:
        print('ERR', k, e)

print(json.dumps({'counts': {k: len(v) for k,v in found.items()}, 'matches': {k: v[:10] for k,v in found.items()}}, indent=2))