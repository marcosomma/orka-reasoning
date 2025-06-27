#!/usr/bin/env python3
"""Test that exactly mimics CLI memory watch behavior"""

import os

from orka.memory_logger import create_memory_logger


def test_cli_memory_behavior():
    print("=== Testing CLI Memory Behavior ===")

    # Mimic CLI parameters exactly
    backend = "redisstack"
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")

    print(f"Backend: {backend}")
    print(f"Redis URL: {redis_url}")

    # Create logger exactly like CLI does
    memory = create_memory_logger(backend=backend, redis_url=redis_url)
    print(f"Logger type: {type(memory).__name__}")

    # Test get_memory_stats (like CLI does)
    print("\n📊 Testing get_memory_stats:")
    stats = memory.get_memory_stats()
    print(f"  Total entries: {stats.get('total_entries', 0)}")
    print(f"  Stored memories: {stats.get('stored_memories', 0)}")
    print(f"  Orchestration logs: {stats.get('orchestration_logs', 0)}")
    print(f"  Categories: {stats.get('entries_by_category', {})}")

    # Test get_recent_stored_memories (like CLI does)
    print("\n🧠 Testing get_recent_stored_memories:")
    try:
        if hasattr(memory, "get_recent_stored_memories"):
            recent_memories = memory.get_recent_stored_memories(5)
            print(f"  Found: {len(recent_memories)} recent stored memories")

            for i, mem in enumerate(recent_memories, 1):
                # Handle bytes content
                raw_content = mem.get("content", "")
                if isinstance(raw_content, bytes):
                    raw_content = raw_content.decode()
                content = raw_content[:50] + ("..." if len(raw_content) > 50 else "")
                log_type = mem.get("metadata", {}).get("log_type", "unknown")
                print(f"    [{i}] {log_type}: {content}")
        else:
            print("  ❌ get_recent_stored_memories method not available")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test search_memories fallback (like CLI does)
    print("\n🔍 Testing search_memories fallback:")
    try:
        if hasattr(memory, "search_memories"):
            search_results = memory.search_memories(
                query=" ",  # Simple space query
                num_results=5,
                log_type="memory",
            )
            print(f"  Found: {len(search_results)} search results")

            for i, mem in enumerate(search_results, 1):
                # Handle bytes content
                raw_content = mem.get("content", "")
                if isinstance(raw_content, bytes):
                    raw_content = raw_content.decode()
                content = raw_content[:50] + ("..." if len(raw_content) > 50 else "")
                print(f"    [{i}] {content}")
        else:
            print("  ❌ search_memories method not available")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Direct comparison with our working test
    print("\n🔧 Direct RedisStackMemoryLogger test:")
    try:
        from orka.memory.redisstack_logger import RedisStackMemoryLogger

        direct_logger = RedisStackMemoryLogger(redis_url=redis_url)
        direct_stats = direct_logger.get_memory_stats()
        direct_memories = direct_logger.get_recent_stored_memories(5)

        print(f"  Direct logger - Stored memories: {direct_stats.get('stored_memories', 0)}")
        print(f"  Direct logger - Recent memories found: {len(direct_memories)}")

        # Compare logger instances
        print("\nLogger comparison:")
        print(f"  Factory logger type: {type(memory).__name__}")
        print(f"  Direct logger type: {type(direct_logger).__name__}")
        print(f"  Same type: {type(memory) == type(direct_logger)}")

        # Compare Redis URLs
        print(f"  Factory Redis URL: {getattr(memory, 'redis_url', 'N/A')}")
        print(f"  Direct Redis URL: {getattr(direct_logger, 'redis_url', 'N/A')}")

    except Exception as e:
        print(f"  ❌ Direct logger test error: {e}")


if __name__ == "__main__":
    test_cli_memory_behavior()
