import redis, json
r=redis.from_url('redis://localhost:6380/0')
info = r.ft('orka_enhanced_memory').info()
print(json.dumps(info, indent=2, default=str))
