import json
import time

import redis

# Connect to RedisStack
r = redis.from_url("redis://localhost:6380/0")

# Get all memory keys
keys = r.keys("orka_memory:*")
print(f"Total keys found: {len(keys)}")

if not keys:
    print("No keys found! Exiting.")
    exit()

# First, let's check the first key manually
first_key = keys[0]
print(f"\n=== DEBUG: First key: {first_key} ===")
data = r.hgetall(first_key)
print(f"Raw data type: {type(data)}")
print(f"Raw data: {data}")

# Sort keys by creation time (newer first) to see recent entries
keys_with_time = []
for key in keys:
    try:
        data = r.hgetall(key)
        print(f"Checking key: {key}, data available: {bool(data)}")

        if data and b"timestamp" in data:
            try:
                timestamp = int(data[b"timestamp"])
                keys_with_time.append((key, timestamp))
                print(f"  Added key with timestamp: {timestamp}")
            except Exception as e:
                print(f"  Error parsing timestamp: {e}")
                keys_with_time.append((key, 0))
        elif data:
            # Check for string keys instead of bytes
            timestamp_val = None
            for k, v in data.items():
                if k == b"timestamp" or k == "timestamp":
                    timestamp_val = v
                    break

            if timestamp_val:
                try:
                    timestamp = int(timestamp_val)
                    keys_with_time.append((key, timestamp))
                    print(f"  Added key with timestamp (string key): {timestamp}")
                except:
                    keys_with_time.append((key, 0))
            else:
                keys_with_time.append((key, 0))
                print("  Added key with timestamp 0 (no timestamp field)")
        else:
            print(f"  No data for key: {key}")
    except Exception as e:
        print(f"Error processing key {key}: {e}")

if not keys_with_time:
    print("No keys with data found!")
    exit()

keys_with_time.sort(key=lambda x: x[1], reverse=True)

# Count by classification
stored_count = 0
log_count = 0

print("\n=== CHECKING MOST RECENT 5 ENTRIES ===")
# Check most recent entries
for i, (key, timestamp) in enumerate(keys_with_time[:5]):
    data = r.hgetall(key)
    if data:
        try:
            print(f"\nKey {i + 1}: {key}")

            # Handle both string and byte keys
            content = None
            metadata = None
            node_id = None

            for k, v in data.items():
                key_str = k.decode() if isinstance(k, bytes) else str(k)
                val_str = v.decode() if isinstance(v, bytes) else str(v)

                if key_str == "content":
                    content = val_str[:200]
                elif key_str == "metadata":
                    metadata = val_str
                elif key_str == "node_id":
                    node_id = val_str

            print(
                f"  timestamp: {timestamp} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp / 1000)) if timestamp > 0 else 'no timestamp'})",
            )
            print(f"  node_id: {node_id}")
            print(f"  content: {content}...")
            print(f"  raw_metadata: {metadata}")

            # Parse metadata
            if metadata:
                try:
                    metadata_dict = json.loads(metadata)
                    log_type = metadata_dict.get("log_type", "not set")
                    category = metadata_dict.get("category", "not set")
                    event_type = metadata_dict.get("event_type", "not set")

                    print("  parsed metadata:")
                    print(f"    log_type: {log_type}")
                    print(f"    category: {category}")
                    print(f"    event_type: {event_type}")

                    # Count classification
                    if log_type == "memory" or category == "stored":
                        stored_count += 1
                        print("    ✅ CLASSIFIED AS STORED MEMORY")
                    else:
                        log_count += 1
                        print("    📋 CLASSIFIED AS ORCHESTRATION LOG")

                except json.JSONDecodeError as e:
                    print(f"  ERROR parsing metadata JSON: {e}")
                    log_count += 1
                    print("    📋 CLASSIFIED AS ORCHESTRATION LOG (JSON error)")
            else:
                log_count += 1
                print("    📋 CLASSIFIED AS ORCHESTRATION LOG (no metadata)")

        except Exception as e:
            print(f"Key {i + 1}: {key} - Error parsing: {e}")

print("\n=== SUMMARY ===")
print("Recent 5 entries:")
print(f"  Stored memories: {stored_count}")
print(f"  Orchestration logs: {log_count}")

# Let's also search for specific patterns
print("\n=== SEARCHING FOR SPECIFIC PATTERNS ===")
memory_entries = 0
write_events = 0
for key in keys:
    data = r.hgetall(key)
    if data and "metadata" in data:
        try:
            metadata = json.loads(data["metadata"])
            if metadata.get("log_type") == "memory":
                memory_entries += 1
            if metadata.get("event_type") == "write":
                write_events += 1
        except:
            pass

print(f"Total entries with log_type=memory: {memory_entries}")
print(f"Total entries with event_type=write: {write_events}")

# Check for memory-writer nodes
print("\n=== CHECKING FOR MEMORY-WRITER NODES ===")
memory_writer_entries = 0
for key in keys:
    data = r.hgetall(key)
    if data:
        node_id = (
            data.get("node_id", b"").decode()
            if isinstance(data.get("node_id"), bytes)
            else str(data.get("node_id", ""))
        )
        if "memory-writer" in node_id.lower():
            memory_writer_entries += 1
            print(f"Found memory-writer entry: {key.decode()} (node_id: {node_id})")

print(f"Total memory-writer entries: {memory_writer_entries}")
