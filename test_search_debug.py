#!/usr/bin/env python3

import sys

sys.path.append(".")
import json

from redis.commands.search.query import Query

from orka.memory.redisstack_logger import RedisStackMemoryLogger


def test_search_filtering():
    """Test the memory search filtering logic."""

    # Create logger
    logger = RedisStackMemoryLogger(
        host="localhost",
        port=6380,
        session="default",
    )

    print("🔍 Testing search filtering logic...")

    # Our specific stored memory key
    target_key = "orka_memory:5018c268ea4143fcaf2e58e618dab3bf"

    # First, test raw Redis search with more results
    print("\n1. Testing raw Redis search...")
    try:
        search_query = "@content:61"
        search_results = logger.redis_client.ft(logger.index_name).search(
            Query(search_query).paging(0, 50),  # Search more results
        )
        print(
            f"   Raw search found {len(search_results.docs)} results (total: {search_results.total})",
        )

        # Look for our specific memory
        found_target = False
        stored_memories_count = 0

        for i, doc in enumerate(search_results.docs):
            memory_data = logger.redis_client.hgetall(doc.id)
            if memory_data:
                # Parse metadata
                try:
                    metadata_value = memory_data.get("metadata", "{}")
                    if isinstance(metadata_value, bytes):
                        metadata_value = metadata_value.decode()
                    metadata = json.loads(metadata_value)

                    log_type = metadata.get("log_type", "N/A")
                    category = metadata.get("category", "N/A")

                    # Check if this is our target memory
                    if doc.id == target_key:
                        found_target = True
                        content = memory_data.get("content", b"").decode("utf-8", errors="ignore")
                        print(f"   ✅ FOUND TARGET MEMORY at position {i + 1}:")
                        print(f"     Key: {doc.id}")
                        print(f"     Content: {content[:80]}...")
                        print(f"     log_type: {log_type}, category: {category}")

                        # Test filtering logic for our memory
                        memory_log_type = metadata.get("log_type", "log")
                        memory_category = metadata.get("category", "log")
                        requested_log_type = "memory"

                        should_skip = (
                            requested_log_type == "memory"
                            and memory_log_type != "memory"
                            and memory_category != "stored"
                        )

                        print(f"     Should skip: {should_skip}")

                        if not should_skip:
                            print("     ✅ This memory SHOULD be included!")
                        else:
                            print("     ❌ This memory WILL be filtered out")

                    # Count stored memories
                    if log_type == "memory" and category == "stored":
                        stored_memories_count += 1
                        if stored_memories_count <= 3:  # Show first few stored memories
                            content = memory_data.get("content", b"").decode(
                                "utf-8",
                                errors="ignore",
                            )
                            print(f"   📝 Stored memory {stored_memories_count}: {doc.id}")
                            print(f"     Content: {content[:60]}...")

                except Exception:
                    pass  # Skip errors for brevity

        print(f"   📊 Found {stored_memories_count} stored memories total")

        if not found_target:
            print(f"   ❌ Target memory {target_key} NOT found in search results")

    except Exception as e:
        print(f"   ❌ Raw search failed: {e}")
        return False

    # Now test the search_memories method
    print("\n2. Testing search_memories method...")
    try:
        memories = logger.search_memories(
            query="61",
            num_results=50,  # Search more results
            log_type="memory",
        )

        print(f"   Search returned {len(memories)} memories")

        for i, memory in enumerate(memories[:5]):  # Show first 5
            content = memory.get("content", "N/A")
            metadata = memory.get("metadata", {})
            log_type = metadata.get("log_type", "N/A")
            category = metadata.get("category", "N/A")

            print(f"   Memory {i + 1}:")
            print(f"     Content: {content[:60]}...")
            print(f"     Log Type: {log_type}")
            print(f"     Category: {category}")
            print(f"     Key: {memory.get('key', 'N/A')}")

        return len(memories) > 0

    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_search_filtering()
    print(f"\n🎯 Test result: {'SUCCESS' if success else 'FAILED'}")
