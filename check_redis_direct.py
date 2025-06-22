#!/usr/bin/env python3
"""
Direct Redis inspection to understand memory storage issues.
"""

import asyncio
import os

import redis.asyncio as redis


async def check_redis_direct():
    """Check Redis directly for memory data."""

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=False)

    try:
        print("🔍 Direct Redis Inspection")
        print("=" * 50)

        # Get all keys
        all_keys = await redis_client.keys("*")
        print(f"📊 Total keys: {len(all_keys)}")

        # Look for any memory-related keys
        memory_keys = []
        stream_keys = []

        for key in all_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            if "memory" in key_str.lower():
                memory_keys.append(key_str)
            if key_str.startswith("orka:memory:"):
                stream_keys.append(key_str)

        print(f"🧠 Memory-related keys: {len(memory_keys)}")
        for key in memory_keys[:10]:  # Show first 10
            print(f"  - {key}")

        print(f"🌊 Stream keys: {len(stream_keys)}")
        for key in stream_keys[:10]:  # Show first 10
            print(f"  - {key}")

        # Check the specific stream that should have been created
        expected_stream = "orka:memory:processed_numbers:default"
        print(f"\n🎯 Checking expected stream: {expected_stream}")

        try:
            # Check if stream exists
            stream_info = await redis_client.xinfo_stream(expected_stream)
            print(f"   ✅ Stream exists! Length: {stream_info.get('length', 0)}")

            # Get entries
            entries = await redis_client.xrange(expected_stream)
            print(f"   📝 Entries: {len(entries)}")

            for entry_id, data in entries:
                print(f"   Entry ID: {entry_id}")
                for field, value in data.items():
                    field_str = field.decode() if isinstance(field, bytes) else field
                    value_str = value.decode() if isinstance(value, bytes) else value
                    print(f"     {field_str}: {value_str[:100]}...")

        except Exception as e:
            print(f"   ❌ Stream check failed: {e}")

        # Check for any keys containing "132"
        print("\n🔎 Looking for keys containing '132'...")
        found_132 = []
        for key in all_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            if "132" in key_str:
                found_132.append(key_str)

        print(f"   Found {len(found_132)} keys with '132':")
        for key in found_132:
            print(f"   - {key}")

        # Check the generic memory key
        if "orka:memory" in [k.decode() for k in all_keys]:
            print("\n🔧 Checking generic 'orka:memory' key...")
            try:
                memory_type = await redis_client.type("orka:memory")
                print(f"   Type: {memory_type}")

                if memory_type == "stream":
                    entries = await redis_client.xrange("orka:memory")
                    print(f"   Stream entries: {len(entries)}")
                    for entry_id, data in entries[-5:]:  # Last 5 entries
                        print(f"   Entry: {entry_id}")
                        for field, value in data.items():
                            field_str = field.decode() if isinstance(field, bytes) else field
                            value_str = value.decode() if isinstance(value, bytes) else value
                            if len(value_str) > 100:
                                print(f"     {field_str}: {value_str[:100]}...")
                            else:
                                print(f"     {field_str}: {value_str}")
            except Exception as e:
                print(f"   ❌ Error checking orka:memory: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(check_redis_direct())
