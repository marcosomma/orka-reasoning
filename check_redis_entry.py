import json
from datetime import datetime

import redis

# Connect to Redis
r = redis.from_url("redis://localhost:6379")

# Check the specific memory entry
stream_key = "orka:memory:processed_numbers:default"
entries = r.xrange(stream_key)

print(f"🔍 Checking stream: {stream_key}")
print(f"📊 Number of entries: {len(entries)}")

if entries:
    entry_id, entry_data = entries[0]
    print(f"\n📝 Entry ID: {entry_id}")
    print("📋 Entry fields:")

    for key, value in entry_data.items():
        key_str = key.decode() if isinstance(key, bytes) else key
        value_str = value.decode() if isinstance(value, bytes) else value

        if key_str == "payload":
            try:
                payload = json.loads(value_str)
                print(f"  {key_str}: {json.dumps(payload, indent=2)[:200]}...")
            except:
                print(f"  {key_str}: {value_str[:100]}...")
        else:
            print(f"  {key_str}: {value_str}")

    # Check for decay-related fields
    decay_fields = ["orka_expire_time", "orka_memory_type", "orka_importance_score"]
    print("\n⏰ Decay metadata:")
    for field in decay_fields:
        field_bytes = field.encode()
        if field_bytes in entry_data:
            value = entry_data[field_bytes].decode()
            print(f"  ✅ {field}: {value}")
        else:
            print(f"  ❌ {field}: MISSING")

    # Check current time vs expire time
    if b"orka_expire_time" in entry_data:
        expire_time_str = entry_data[b"orka_expire_time"].decode()
        try:
            expire_time = datetime.fromisoformat(expire_time_str)
            current_time = datetime.now(expire_time.tzinfo)

            print("\n🕐 Time analysis:")
            print(f"  Current time: {current_time}")
            print(f"  Expire time:  {expire_time}")
            print(f"  Time diff:    {(expire_time - current_time).total_seconds():.1f}s")

            if current_time > expire_time:
                print("  ⚠️  ENTRY SHOULD BE EXPIRED!")
            else:
                print("  ✅ Entry is still valid")
        except Exception as e:
            print(f"  ❌ Error parsing expire time: {e}")
else:
    print("❌ No entries found")
