#!/usr/bin/env python3
"""Debug script to check Redis keys when using Kafka backend."""

from datetime import datetime

import redis


def main():
    # Connect to Redis
    r = redis.from_url("redis://localhost:6379/0", decode_responses=True)

    print("🔍 Checking Redis keys for Kafka backend")
    print("=" * 50)

    # Get all keys
    all_keys = r.keys("*")
    print(f"📊 Total keys in Redis: {len(all_keys)}")

    # Filter memory-related keys
    memory_keys = [k for k in all_keys if "memory" in k.lower()]
    print(f"🧠 Memory-related keys: {len(memory_keys)}")
    for key in memory_keys:
        print(f"  - {key}")

    # Filter orka keys
    orka_keys = [k for k in all_keys if k.startswith("orka:")]
    print(f"🎯 OrKa keys: {len(orka_keys)}")
    for key in orka_keys:
        print(f"  - {key}")

    # Check specific stream key
    stream_key = "orka:memory"
    print(f"\n🌊 Checking stream: {stream_key}")

    if r.exists(stream_key):
        try:
            stream_type = r.type(stream_key)
            print(f"   Type: {stream_type}")

            if stream_type == "stream":
                # Get stream info
                stream_info = r.xinfo_stream(stream_key)
                print(f"   Length: {stream_info.get('length', 0)}")

                # Get recent entries
                entries = r.xrevrange(stream_key, count=5)
                print(f"   Recent entries: {len(entries)}")

                for i, (entry_id, fields) in enumerate(entries):
                    print(f"   Entry {i + 1}: {entry_id}")
                    print(f"     Agent: {fields.get('agent_id', 'N/A')}")
                    print(f"     Event: {fields.get('event_type', 'N/A')}")
                    print(f"     Memory Type: {fields.get('orka_memory_type', 'N/A')}")
                    print(f"     Memory Category: {fields.get('orka_memory_category', 'N/A')}")
                    print(f"     Expire Time: {fields.get('orka_expire_time', 'N/A')}")

                    # Check if expired
                    expire_time_str = fields.get("orka_expire_time")
                    if expire_time_str:
                        try:
                            expire_time = datetime.fromisoformat(expire_time_str)
                            now = datetime.now(expire_time.tzinfo)
                            if expire_time < now:
                                print("     ⚠️  EXPIRED!")
                            else:
                                remaining = (expire_time - now).total_seconds()
                                print(f"     ✅ Valid for {remaining:.1f}s")
                        except:
                            print("     ❓ Invalid expire time format")
                    print()
        except Exception as e:
            print(f"   ❌ Error checking stream: {e}")
    else:
        print("   ❌ Stream does not exist")

    # Check for any stream keys and show their field names
    stream_keys = [k for k in all_keys if r.type(k) == "stream"]
    print(f"\n🌊 All stream keys: {len(stream_keys)}")
    for key in stream_keys:
        try:
            info = r.xinfo_stream(key)
            length = info.get("length", 0)
            print(f"  - {key}: {length} entries")

            # Show field names from the first entry
            entries = r.xrange(key, count=1)
            if entries:
                entry_id, fields = entries[0]
                print("    📋 Fields in first entry:")
                for field_name, field_value in fields.items():
                    if len(field_value) > 100:
                        print(f"      {field_name}: {field_value[:100]}...")
                    else:
                        print(f"      {field_name}: {field_value}")
                print()
        except Exception as e:
            print(f"  - {key}: error getting info - {e}")


if __name__ == "__main__":
    main()
