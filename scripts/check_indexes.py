import redis
r=redis.from_url('redis://localhost:6380/0')
for name in ['orka_enhanced_memory','memory_entries']:
    try:
        info = r.ft(name).info()
        print(f"Index {name} exists: fields={list(info.keys())[:5]}")
    except Exception as e:
        print(f"Index {name} check error: {e}")
