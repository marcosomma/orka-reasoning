import redis, json
r=redis.from_url('redis://localhost:6380/0')
keys=list(r.scan_iter('orka_memory:*'))
print('found',len(keys),'memory keys')
matches=[]
for key in keys:
    d=r.hgetall(key)
    dd={}
    for kk,vv in d.items():
        kk_dec=kk.decode()
        if isinstance(vv,bytes):
            try:
                v=vv.decode('utf-8')
            except Exception:
                v=None
        else:
            v=vv
        dd[kk_dec]=v
    node_id=dd.get('node_id')
    metadata=dd.get('metadata')
    if node_id=='join_results' or (metadata and 'join_result' in metadata):
        print('MATCH',key.decode())
        print(' node_id:',node_id)
        print(' metadata:',metadata)
        print(' content preview:', (dd.get('content') or '')[:400])
        matches.append(key.decode())
print('total matches',len(matches))