#!/usr/bin/env python3

print("Starting minimal test...")

try:
    print("Testing basic imports...")
    print("pytest imported successfully")

    from fake_redis import FakeRedisClient

    print("FakeRedisClient imported successfully")

    from orka.memory_logger import RedisMemoryLogger

    print("RedisMemoryLogger imported successfully")

    print("RouterNode imported successfully")

    from orka.nodes.fork_node import ForkNode

    print("ForkNode imported successfully")

    print("All imports successful!")

    # Test basic functionality
    memory = RedisMemoryLogger(FakeRedisClient())
    print("Memory logger created successfully")

    fork_node = ForkNode(
        node_id="test_fork",
        targets=[["branch1", "branch2"]],
        memory_logger=memory,
    )
    print("ForkNode created successfully")

    print("All tests passed!")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
