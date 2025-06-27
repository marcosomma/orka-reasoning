import json

import redis

from orka.memory.redisstack_logger import RedisStackMemoryLogger

target_key = "orka_memory:8f592f9e618b4fc6a22e9675e416b211"

print("=== Final Debug Test ===")

# 1. Direct Redis client
print("1. Direct Redis Client:")
direct_client = redis.from_url("redis://localhost:6380/0")
direct_data = direct_client.hgetall(target_key)
direct_metadata = direct_data.get(b"metadata", b"{}").decode()
print(f"   Metadata: {direct_metadata}")

# 2. Logger's main redis_client
print("\n2. Logger's Main Redis Client:")
logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")
main_data = logger.redis_client.hgetall(target_key)
main_metadata = main_data.get(b"metadata", b"{}").decode()
print(f"   Metadata: {main_metadata}")

# 3. Logger's thread-safe client
print("\n3. Logger's Thread-Safe Client:")
thread_client = logger._get_thread_safe_client()
thread_data = thread_client.hgetall(target_key)
thread_metadata = thread_data.get(b"metadata", b"{}").decode()
print(f"   Metadata: {thread_metadata}")

# 4. Check decode_responses setting
print("\n4. Client Configurations:")
print(f"   Direct client decode_responses: {getattr(direct_client, 'decode_responses', 'unknown')}")
print(
    f"   Main client decode_responses: {getattr(logger.redis_client, 'decode_responses', 'unknown')}",
)
print(f"   Thread client decode_responses: {getattr(thread_client, 'decode_responses', 'unknown')}")

# 5. Test the actual get_recent_stored_memories method
print("\n5. Testing get_recent_stored_memories:")
memories = logger.get_recent_stored_memories(10)
print(f"   Found: {len(memories)} stored memories")

# 6. Manual logic replication with thread-safe client
print("\n6. Manual Logic with Thread-Safe Client:")
keys = thread_client.keys("orka_memory:*")
found_stored = 0

for key in keys:
    memory_data = thread_client.hgetall(key)

    # Try both ways to get metadata
    metadata_bytes = memory_data.get(b"metadata")
    metadata_str = memory_data.get("metadata")

    print(f"   Key: {key}")
    print(f"     metadata (bytes): {metadata_bytes}")
    print(f"     metadata (str): {metadata_str}")

    # Use whichever one exists
    if metadata_bytes:
        metadata_value = (
            metadata_bytes.decode() if isinstance(metadata_bytes, bytes) else str(metadata_bytes)
        )
    elif metadata_str:
        metadata_value = metadata_str
    else:
        metadata_value = "{}"

    try:
        metadata = json.loads(metadata_value)
        log_type = metadata.get("log_type", "log")
        category = metadata.get("category", "log")

        print(f"     log_type: {log_type}, category: {category}")

        if log_type == "memory" or category == "stored":
            print("     ✅ STORED MEMORY!")
            found_stored += 1
        else:
            print("     ❌ Filtered out")

    except Exception as e:
        print(f"     Error: {e}")

    if key.decode() == target_key:
        print("     📌 THIS IS OUR TARGET KEY")
        break

print(f"\nManual search found: {found_stored} stored memories")
