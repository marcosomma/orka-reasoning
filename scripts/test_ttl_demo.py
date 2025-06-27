#!/usr/bin/env python3
"""
TTL Demo Script - Test memory expiration and TTL display
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "orka"))

from orka.memory_logger import create_memory_logger


def test_ttl_functionality():
    """Test TTL functionality with different expiration times."""
    print("🚀 TTL Demo - Testing Memory Expiration")
    print("=" * 50)

    # Create RedisStack memory logger
    memory = create_memory_logger(
        backend="redisstack",
        redis_url="redis://localhost:6380/0",
    )

    print("📝 Storing memories with different TTL values...")

    # Store memories with different expiration times
    test_memories = [
        {
            "content": "Short-lived memory - expires in 30 seconds",
            "node_id": "test_node",
            "trace_id": "ttl_demo",
            "memory_type": "short_term",
            "expiry_hours": 30 / 3600,  # 30 seconds
            "importance_score": 0.8,
        },
        {
            "content": "Medium-lived memory - expires in 2 minutes",
            "node_id": "test_node",
            "trace_id": "ttl_demo",
            "memory_type": "short_term",
            "expiry_hours": 2 / 60,  # 2 minutes
            "importance_score": 0.9,
        },
        {
            "content": "Long-lived memory - expires in 1 hour",
            "node_id": "test_node",
            "trace_id": "ttl_demo",
            "memory_type": "long_term",
            "expiry_hours": 1,  # 1 hour
            "importance_score": 0.7,
        },
        {
            "content": "Permanent memory - never expires",
            "node_id": "test_node",
            "trace_id": "ttl_demo",
            "memory_type": "long_term",
            "expiry_hours": None,  # No expiry
            "importance_score": 1.0,
        },
    ]

    # Store all test memories
    for i, mem_data in enumerate(test_memories, 1):
        try:
            key = memory.log_memory(
                content=mem_data["content"],
                node_id=mem_data["node_id"],
                trace_id=mem_data["trace_id"],
                metadata={"log_type": "memory", "category": "stored", "test_id": i},
                importance_score=mem_data["importance_score"],
                memory_type=mem_data["memory_type"],
                expiry_hours=mem_data["expiry_hours"],
            )
            print(f"✅ Stored memory {i}: {key}")
        except Exception as e:
            print(f"❌ Failed to store memory {i}: {e}")

    print("\n📊 Retrieving stored memories with TTL info...")

    # Get recent memories with TTL info
    try:
        recent_memories = memory.get_recent_stored_memories(10)

        if recent_memories:
            print(f"\n🧠 Found {len(recent_memories)} stored memories:")
            print("-" * 80)

            for i, mem in enumerate(recent_memories, 1):
                content = mem.get("content", "")[:60] + (
                    "..." if len(mem.get("content", "")) > 60 else ""
                )
                memory_type = mem.get("memory_type", "unknown")
                importance = mem.get("importance_score", 0)

                # TTL information
                ttl_formatted = mem.get("ttl_formatted", "Unknown")
                expires_at_formatted = mem.get("expires_at_formatted", "Unknown")
                has_expiry = mem.get("has_expiry", False)

                print(f"[{i}] {memory_type} | Score: {importance:.2f}")
                print(f"    📝 {content}")

                # Display TTL information
                if has_expiry:
                    if ttl_formatted == "0s":
                        print(f"    ⏰ TTL: ⚠️ Expired (was: {expires_at_formatted})")
                    else:
                        print(f"    ⏰ TTL: {ttl_formatted} (expires: {expires_at_formatted})")
                else:
                    print(f"    ⏰ TTL: {ttl_formatted}")
                print()
        else:
            print("No stored memories found")

    except Exception as e:
        print(f"❌ Error retrieving memories: {e}")

    print("\n💡 Now run: python -m orka.orka_cli memory watch --backend redisstack")
    print("   to see live TTL updates in the memory watch interface!")


if __name__ == "__main__":
    test_ttl_functionality()
