import json
from datetime import datetime, timezone

import redis


def debug_memory_storage():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    print("🔍 Memory Storage Debug")
    print("=" * 50)

    # Check all memory-related keys
    memory_keys = [k for k in r.keys("*") if "memory" in k.lower()]
    print(f"📊 Memory-related keys ({len(memory_keys)}):")
    for key in memory_keys:
        print(f"  - {key}")

    print("\n🌊 Checking orka:memory stream:")
    try:
        entries = r.xrevrange("orka:memory", count=10)
        print(f"Found {len(entries)} entries")

        now = datetime.now(timezone.utc)

        for i, (entry_id, fields) in enumerate(entries):
            agent_id = fields.get("agent_id", "N/A")
            event_type = fields.get("event_type", "N/A")
            namespace = fields.get("orka_namespace", fields.get("namespace", "N/A"))
            expire_time = fields.get("orka_expire_time", "N/A")
            memory_type = fields.get("orka_memory_type", "N/A")

            print(f"  Entry {i + 1}: {agent_id} ({event_type}) - namespace: {namespace}")
            print(f"    Memory type: {memory_type}, Expires: {expire_time}")

            # Check if expired
            if expire_time != "N/A":
                try:
                    expire_dt = datetime.fromisoformat(expire_time.replace("Z", "+00:00"))
                    if expire_dt < now:
                        print(
                            f"    ⚠️  EXPIRED! (expired {(now - expire_dt).total_seconds():.1f}s ago)",
                        )
                    else:
                        print(f"    ✅ Valid for {(expire_dt - now).total_seconds():.1f}s more")
                except:
                    print("    ❓ Could not parse expire time")

            # Look for memory writer entries
            if "memory_writer" in agent_id.lower() and event_type == "write":
                print("    🎯 MEMORY WRITE EVENT!")
                if "payload" in fields:
                    try:
                        payload = json.loads(fields["payload"])
                        print(f"    Content: {payload.get('content', 'N/A')[:100]}...")
                        print(f"    Namespace: {payload.get('namespace', 'N/A')}")
                        print(f"    Session: {payload.get('session', 'N/A')}")
                        print(f"    Key: {payload.get('key', 'N/A')}")
                        if "metadata" in payload:
                            metadata = payload["metadata"]
                            print(f"    Metadata keys: {list(metadata.keys())}")
                            print(f"    Number: {metadata.get('number', 'N/A')}")
                    except Exception as e:
                        print(f"    Error parsing payload: {e}")

    except Exception as e:
        print(f"Error reading orka:memory: {e}")

    print("\n🎯 Checking specific namespace streams:")
    namespace_streams = [
        "orka:memory:processed_numbers:default",
        "orka:memory:processed_numbers",
        "processed_numbers:default",
        "processed_numbers",
    ]

    for stream in namespace_streams:
        try:
            entries = r.xrange(stream)
            if entries:
                print(f"  ✅ {stream}: {len(entries)} entries")
                for entry_id, fields in entries[:3]:
                    print(f"    Entry: {entry_id} - {list(fields.keys())}")
            else:
                print(f"  ❌ {stream}: empty or doesn't exist")
        except:
            print(f"  ❌ {stream}: doesn't exist")

    print("\n🔧 Checking vector memory keys:")
    vector_keys = [k for k in r.keys("*") if "vector" in k.lower() or "embedding" in k.lower()]
    for key in vector_keys:
        print(f"  - {key}")

    print("\n⏰ Memory decay analysis:")
    print(f"Current time: {now.isoformat()}")
    print("Configuration shows:")
    print("  - short_term_hours: 0.025 (1.5 minutes)")
    print("  - long_term_hours: 0.05 (3 minutes)")
    print("  - memory_type: short_term")


if __name__ == "__main__":
    debug_memory_storage()
