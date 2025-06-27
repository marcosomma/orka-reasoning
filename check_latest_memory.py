import json

import redis

r = redis.from_url("redis://localhost:6380/0")
key = "orka_memory:8f592f9e618b4fc6a22e9675e416b211"

print("=== Checking Latest Memory ===")
data = r.hgetall(key)
if data:
    print("✅ Key exists")
    metadata = data.get(b"metadata", b"{}").decode()
    print(f"Metadata: {metadata}")
    parsed = json.loads(metadata)
    print(f"log_type: {parsed.get('log_type')}")
    print(f"category: {parsed.get('category')}")
else:
    print("❌ Key not found")
    keys = r.keys("orka_memory:*")
    print(f"Total keys: {len(keys)}")
    if keys:
        latest = keys[-1].decode()
        print(f"Latest: {latest}")
        latest_data = r.hgetall(latest)
        latest_meta = latest_data.get(b"metadata", b"{}").decode()
        print(f"Latest metadata: {latest_meta}")
        if latest_meta != "{}":
            latest_parsed = json.loads(latest_meta)
            print(f"Latest log_type: {latest_parsed.get('log_type')}")

# Test thread-safe client directly
print("\n=== Testing Thread-Safe Client ===")
from orka.memory.redisstack_logger import RedisStackMemoryLogger

logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")
thread_client = logger._get_thread_safe_client()

# Check if thread client sees the same keys
thread_keys = thread_client.keys("orka_memory:*")
print(f"Thread-safe client sees {len(thread_keys)} keys")

if key.encode() in thread_keys or key in thread_keys:
    print("✅ Thread-safe client can see our test memory")
    thread_data = thread_client.hgetall(key)
    thread_meta = thread_data.get(b"metadata", b"{}").decode()
    print(f"Thread client metadata: {thread_meta}")
else:
    print("❌ Thread-safe client cannot see our test memory")
