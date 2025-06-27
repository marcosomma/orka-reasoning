#!/usr/bin/env python3
"""
Parallel Memory Test - Verify thread safety and embedding fixes
"""

import concurrent.futures
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "orka"))

from orka.memory_logger import create_memory_logger


def worker_thread(thread_id, memory_logger, num_operations=5):
    """Worker function to test parallel memory operations."""
    results = []

    try:
        for i in range(num_operations):
            # Store a memory
            content = f"Thread {thread_id} - Operation {i} - Testing parallel memory access"
            key = memory_logger.log_memory(
                content=content,
                node_id=f"thread_{thread_id}",
                trace_id=f"parallel_test_{thread_id}",
                metadata={
                    "log_type": "memory",
                    "category": "stored",
                    "thread_id": thread_id,
                    "operation": i,
                },
                importance_score=0.8,
                memory_type="short_term",
                expiry_hours=0.5,  # 30 minutes
            )

            # Try to retrieve memories
            memories = memory_logger.get_recent_stored_memories(3)

            # Try vector search
            search_results = memory_logger.search_memories(
                query=f"testing parallel thread {thread_id}",
                num_results=3,
                log_type="memory",
            )

            results.append(
                {
                    "thread_id": thread_id,
                    "operation": i,
                    "key": key,
                    "memories_found": len(memories),
                    "search_results": len(search_results),
                    "success": True,
                },
            )

            # Small delay to increase chance of race conditions
            time.sleep(0.1)

    except Exception as e:
        results.append(
            {
                "thread_id": thread_id,
                "error": str(e),
                "success": False,
            },
        )

    return results


def test_parallel_memory_operations():
    """Test parallel memory operations with multiple threads."""
    print("🔄 Testing Parallel Memory Operations")
    print("=" * 50)

    # Create RedisStack memory logger
    try:
        memory = create_memory_logger(
            backend="redisstack",
            redis_url="redis://localhost:6380/0",
        )
        print("✅ Memory logger created successfully")

        # Check vector search capability
        embedder_available = hasattr(memory, "embedder") and memory.embedder is not None
        print(f"🤖 Embedder available: {'✅ Yes' if embedder_available else '❌ No'}")

    except Exception as e:
        print(f"❌ Failed to create memory logger: {e}")
        return

    # Test single-threaded first
    print("\n📝 Testing single-threaded operations...")
    try:
        single_results = worker_thread(0, memory, 2)
        success_count = sum(1 for r in single_results if r.get("success", False))
        print(
            f"✅ Single-threaded test: {success_count}/{len(single_results)} operations successful",
        )
    except Exception as e:
        print(f"❌ Single-threaded test failed: {e}")
        return

    # Test multi-threaded
    print("\n🚀 Testing multi-threaded operations...")
    num_threads = 4
    operations_per_thread = 3

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit tasks
        futures = [
            executor.submit(worker_thread, thread_id, memory, operations_per_thread)
            for thread_id in range(1, num_threads + 1)
        ]

        # Collect results
        all_results = []
        successful_threads = 0

        for future in concurrent.futures.as_completed(futures):
            try:
                thread_results = future.result()
                all_results.extend(thread_results)

                # Check if thread completed successfully
                if all(r.get("success", False) for r in thread_results):
                    successful_threads += 1

            except Exception as e:
                print(f"❌ Thread failed with exception: {e}")
                all_results.append({"error": str(e), "success": False})

    end_time = time.time()

    # Analyze results
    total_operations = len(all_results)
    successful_operations = sum(1 for r in all_results if r.get("success", False))

    print("\n📊 Parallel Test Results:")
    print(f"   Threads: {num_threads}")
    print(f"   Operations per thread: {operations_per_thread}")
    print(f"   Total operations: {total_operations}")
    print(f"   Successful operations: {successful_operations}/{total_operations}")
    print(f"   Successful threads: {successful_threads}/{num_threads}")
    print(f"   Duration: {end_time - start_time:.2f} seconds")

    # Show any errors
    errors = [r for r in all_results if not r.get("success", False)]
    if errors:
        print("\n❌ Errors encountered:")
        for error in errors:
            print(f"   {error}")
    else:
        print("✅ No errors encountered!")

    # Test memory stats in parallel context
    print("\n📈 Memory Stats After Parallel Operations:")
    try:
        stats = memory.get_memory_stats()
        print(f"   Total entries: {stats.get('total_entries', 0)}")
        print(f"   Stored memories: {stats.get('stored_memories', 0)}")
        print(f"   Active entries: {stats.get('active_entries', 0)}")

        if hasattr(memory, "get_performance_metrics"):
            metrics = memory.get_performance_metrics()
            print(f"   Vector search enabled: {metrics.get('vector_search_enabled', False)}")

    except Exception as e:
        print(f"❌ Failed to get stats: {e}")

    # Final recommendation
    if successful_operations == total_operations and successful_threads == num_threads:
        print("\n🎉 All tests passed! RedisStack now supports parallel operations.")
        print("💡 Your fork/join workflows should work correctly now.")
    else:
        print("\n⚠️ Some operations failed. Check the errors above.")


if __name__ == "__main__":
    test_parallel_memory_operations()
