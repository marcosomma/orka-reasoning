from orka.memory.redisstack_logger import RedisStackMemoryLogger

print("=== Creating Test Stored Memory ===")
logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")

# Create a proper stored memory using log_memory method
memory_key = logger.log_memory(
    content="Test stored memory: The number 42 is the answer to everything",
    node_id="test_memory_writer",
    trace_id="test_session_123",
    metadata={
        "namespace": "test_memories",
        "category": "stored",
        "log_type": "memory",
        "content_type": "user_input",
        "test": True,
    },
    importance_score=0.9,
    memory_type="long_term",
    expiry_hours=24,
)

print(f"✅ Created stored memory: {memory_key}")

# Test if it's detected
memories = logger.get_recent_stored_memories(5)
print(f"🧠 Found {len(memories)} stored memories")

if memories:
    memory = memories[0]
    content = memory["content"][:80] + "..." if len(memory["content"]) > 80 else memory["content"]
    print(f"  Content: {content}")
    print(f"  Node: {memory['node_id']}")
    print(f"  TTL: {memory['ttl_formatted']}")
    print(f"  Metadata log_type: {memory['metadata'].get('log_type')}")

# Test stats
stats = logger.get_memory_stats()
print("\n📊 Updated Statistics:")
print(f"  • Stored memories: {stats['stored_memories']}")
print(f"  • Orchestration logs: {stats['orchestration_logs']}")
print(f"  • Total entries: {stats['total_entries']}")
print(f"  • Categories: {stats['entries_by_category']}")
