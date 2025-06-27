#!/usr/bin/env python3
"""Test script to check memory statistics."""

import json
import os

os.environ["ORKA_MEMORY_BACKEND"] = "kafka"

from orka.memory_logger import create_memory_logger


def main():
    print("🔍 Testing Memory Statistics")
    print("=" * 40)

    memory = create_memory_logger("kafka")
    stats = memory.get_memory_stats()

    print(f"📊 Total Entries: {stats.get('total_entries', 0)}")
    print(f"🌊 Total Streams: {stats.get('total_streams', 0)}")
    print(f"⏰ Expired Entries: {stats.get('expired_entries', 0)}")

    print("\n📋 Memory Types:")
    memory_types = stats.get("entries_by_memory_type", {})
    for mem_type, count in memory_types.items():
        if count > 0:
            print(f"  {mem_type}: {count}")

    print("\n📂 Memory Categories:")
    categories = stats.get("entries_by_category", {})
    for category, count in categories.items():
        if count > 0:
            print(f"  {category}: {count}")

    print("\n🎯 Event Types:")
    event_types = stats.get("entries_by_type", {})
    for event_type, count in event_types.items():
        if count > 0:
            print(f"  {event_type}: {count}")

    if "streams_detail" in stats:
        print("\n🌊 Stream Details:")
        for stream in stats["streams_detail"]:
            print(f"  {stream['stream']}: {stream['active_entries']} active entries")

    # Check local buffer insights
    if "local_buffer_insights" in stats:
        insights = stats["local_buffer_insights"]
        print("\n💾 Local Buffer Insights:")
        print(f"  Total entries: {insights['total_entries']}")
        print(f"  With decay metadata: {insights['entries_with_decay_metadata']}")

    # Create a RedisStack memory logger
    logger = create_memory_logger(backend="redisstack")

    # Get detailed stats with debug info
    print("=== Testing get_memory_stats ===")
    try:
        # Get keys directly
        client = logger._get_thread_safe_client()
        keys = client.keys("orka_memory:*")
        print(f"Found {len(keys)} keys")

        stored_count = 0
        log_count = 0

        # Debug each key
        for i, key in enumerate(keys):
            print(f"\nKey {i + 1}: {key.decode()}")
            memory_data = client.hgetall(key)

            if memory_data:
                # Parse metadata
                metadata_value = memory_data.get("metadata", "{}")
                print(f"  Raw metadata: {metadata_value}")

                if isinstance(metadata_value, bytes):
                    metadata_value = metadata_value.decode()
                    print(f"  Decoded metadata: {metadata_value}")

                try:
                    metadata = json.loads(metadata_value)
                    log_type = metadata.get("log_type", "log")
                    category = metadata.get("category", "log")

                    print(f"  log_type: {log_type}")
                    print(f"  category: {category}")

                    if log_type == "memory" or category == "stored":
                        stored_count += 1
                        print("  → STORED MEMORY")
                    else:
                        log_count += 1
                        print("  → ORCHESTRATION LOG")
                except Exception as e:
                    print(f"  Error parsing metadata: {e}")
                    log_count += 1

        print(f"\nManual count: {stored_count} stored, {log_count} logs")

        # Now test the actual method
        stats = logger.get_memory_stats()
        print("\nMethod result:")
        print(f"  Stored memories: {stats.get('stored_memories', 'N/A')}")
        print(f"  Orchestration logs: {stats.get('orchestration_logs', 'N/A')}")
        print(f"  Categories: {stats.get('entries_by_category', {})}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
