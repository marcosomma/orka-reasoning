import json
import time

from orka.memory.redisstack_logger import RedisStackMemoryLogger

print("=== Debugging get_recent_stored_memories Step by Step ===")

logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")

# Manually replicate the method logic
client = logger.redis_client
pattern = "orka_memory:*"
keys = client.keys(pattern)

print(f"1. Found {len(keys)} total keys")

stored_memories = []
current_time_ms = int(time.time() * 1000)

target_key = "orka_memory:7c71b5e1e28f4178ba4800d71ed01bf0"

for i, key in enumerate(keys):
    key_str = key.decode() if isinstance(key, bytes) else str(key)
    print(f"\n--- Processing Key {i + 1}: {key_str} ---")

    try:
        memory_data = client.hgetall(key)
        if not memory_data:
            print("❌ No data found")
            continue
        print("✅ Data found")

        # Check expiry
        is_expired = logger._is_expired(memory_data)
        print(f"📅 Expired: {is_expired}")
        if is_expired:
            continue

        # Parse metadata (the critical part)
        metadata_value = memory_data.get("metadata", "{}")
        print(f"📋 Raw metadata value: {metadata_value}")
        print(f"📋 Metadata type: {type(metadata_value)}")

        if isinstance(metadata_value, bytes):
            metadata_value = metadata_value.decode()
            print(f"📋 Decoded metadata: {metadata_value}")

        try:
            metadata = json.loads(metadata_value)
            print(f"✅ Parsed metadata: {metadata}")
        except Exception as e:
            print(f"❌ JSON parse error: {e}")
            continue

        # Check filtering condition (the bug is likely here)
        memory_log_type = metadata.get("log_type", "log")
        memory_category = metadata.get("category", "log")

        print(f"🏷️ log_type: '{memory_log_type}'")
        print(f"🏷️ category: '{memory_category}'")

        # The critical condition
        condition_result = memory_log_type != "memory" and memory_category != "stored"
        print(f"🔍 Filter condition (should be False for stored memories): {condition_result}")

        if condition_result:
            print("❌ FILTERED OUT - not a stored memory")
            continue
        else:
            print("✅ STORED MEMORY DETECTED!")
            # This memory should be included
            stored_memories.append(
                {
                    "key": key_str,
                    "content": memory_data.get("content", ""),
                    "metadata": metadata,
                },
            )

    except Exception as e:
        print(f"❌ Error processing key: {e}")
        continue

print("\n🎯 Final Result:")
print(f"  Stored memories found: {len(stored_memories)}")
for mem in stored_memories:
    print(f"    - {mem['key']}: {mem['content'][:50]}...")

# Also test the actual method
print("\n🔬 Testing actual method:")
actual_memories = logger.get_recent_stored_memories(5)
print(f"  Actual method result: {len(actual_memories)} memories")
