import redis
r=redis.from_url('redis://localhost:6380/0')
try:
    queries = ['@node_id:join_results','@node_id:join\_results','@node_id:join','@node_id:results','join_results','join\_results']
    for q in queries:
        try:
            res=r.ft('orka_enhanced_memory').search(q)
            print('Q:',q,'matches', len(res.docs))
            for d in res.docs[:5]:
                print(' id', d.id, 'node', getattr(d,'node_id',None))
        except Exception as e:
            print('Q',q,'error',e)
        print('---')
except Exception as e:
    print('search error', e)
