import json

import redis

r = redis.from_url("redis://localhost:6380/0")
key = "orka_memory:7c71b5e1e28f4178ba4800d71ed01bf0"

print("=== Checking Memory Key ===")
print(f"Key: {key}")

data = r.hgetall(key)
if data:
    print("✅ Key exists")

    # Check all fields
    for field, value in data.items():
        field_str = field.decode() if isinstance(field, bytes) else str(field)
        if field_str == "metadata":
            print("📋 Metadata field found")
            if isinstance(value, bytes):
                metadata_str = value.decode()
            else:
                metadata_str = str(value)

            print(f"Raw metadata: {metadata_str}")

            try:
                metadata = json.loads(metadata_str)
                print("✅ Parsed metadata successfully")
                print(f"  log_type: {metadata.get('log_type')}")
                print(f"  category: {metadata.get('category')}")
                print(f"  namespace: {metadata.get('namespace')}")
                print(f"  test: {metadata.get('test')}")
            except Exception as e:
                print(f"❌ Error parsing metadata: {e}")
        else:
            val_str = value.decode()[:50] if isinstance(value, bytes) else str(value)[:50]
            print(f"  {field_str}: {val_str}...")

else:
    print("❌ Key not found")

    # Check all keys to see if it was created with a different name
    keys = r.keys("orka_memory:*")
    print(f"Total keys: {len(keys)}")
    if keys:
        latest_key = keys[-1]
        print(f"Latest key: {latest_key.decode()}")
        latest_data = r.hgetall(latest_key)
        if b"metadata" in latest_data:
            latest_metadata = latest_data[b"metadata"].decode()
            print(f"Latest metadata: {latest_metadata}")
