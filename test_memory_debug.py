#!/usr/bin/env python3
"""
Debug script to test memory storage and retrieval in OrKa routing example.
"""

import asyncio
import json
import os

import redis.asyncio as redis

from orka.nodes.memory_reader_node import MemoryReaderNode


async def check_memory_storage():
    """Check what's actually stored in Redis memory."""

    # Connect to Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=False)

    try:
        print("🔍 Checking Redis memory storage...")
        print("=" * 50)

        # Check all keys
        all_keys = await redis_client.keys("*")
        print(f"📊 Total keys in Redis: {len(all_keys)}")

        # Check memory-related keys
        memory_keys = [k for k in all_keys if b"memory" in k or b"mem:" in k]
        print(f"🧠 Memory-related keys: {len(memory_keys)}")

        for key in memory_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            print(f"  - {key_str}")

        # Check stream keys (where memories are stored)
        stream_keys = [k for k in all_keys if b"orka:memory:" in k]
        print(f"🌊 Stream keys: {len(stream_keys)}")

        for stream_key in stream_keys:
            stream_key_str = stream_key.decode() if isinstance(stream_key, bytes) else stream_key
            print(f"\n📋 Stream: {stream_key_str}")

            # Get entries from stream
            entries = await redis_client.xrange(stream_key_str)
            print(f"   Entries: {len(entries)}")

            for entry_id, data in entries:
                entry_id_str = entry_id.decode() if isinstance(entry_id, bytes) else entry_id
                print(f"   📝 Entry ID: {entry_id_str}")

                # Decode payload
                if b"payload" in data:
                    payload_bytes = data[b"payload"]
                    payload_str = (
                        payload_bytes.decode()
                        if isinstance(payload_bytes, bytes)
                        else payload_bytes
                    )
                    try:
                        payload = json.loads(payload_str)
                        print(f"      Content: {payload.get('content', 'N/A')[:100]}...")
                        print(f"      Metadata: {payload.get('metadata', {})}")
                    except json.JSONDecodeError:
                        print(f"      Raw payload: {payload_str[:100]}...")

        # Check vector memory keys
        vector_keys = [k for k in all_keys if k.startswith(b"mem:")]
        print(f"\n🔢 Vector memory keys: {len(vector_keys)}")

        for vector_key in vector_keys[:5]:  # Show first 5
            vector_key_str = vector_key.decode() if isinstance(vector_key, bytes) else vector_key
            print(f"  - {vector_key_str}")

            # Get content
            content = await redis_client.hget(vector_key_str, "content")
            namespace = await redis_client.hget(vector_key_str, "namespace")

            if content:
                content_str = content.decode() if isinstance(content, bytes) else content
                namespace_str = namespace.decode() if isinstance(namespace, bytes) else namespace
                print(f"    Content: {content_str[:100]}...")
                print(f"    Namespace: {namespace_str}")

        print("\n" + "=" * 50)
        print("✅ Memory check complete!")

    except Exception as e:
        print(f"❌ Error checking memory: {e}")
    finally:
        await redis_client.close()


async def test_memory_search():
    """Test memory search functionality."""

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=False)

    try:
        print("\n🔍 Testing memory search...")
        print("=" * 50)

        # Search for number 132 analysis
        namespace = "processed_numbers"
        search_query = "132"

        print(f"🔎 Searching for: '{search_query}' in namespace: '{namespace}'")

        # Check stream search
        stream_key = f"orka:memory:{namespace}:default"
        print(f"📋 Checking stream: {stream_key}")

        try:
            entries = await redis_client.xrange(stream_key)
            print(f"   Found {len(entries)} entries in stream")

            for entry_id, data in entries:
                if b"payload" in data:
                    payload_bytes = data[b"payload"]
                    payload_str = payload_bytes.decode()
                    payload = json.loads(payload_str)
                    content = payload.get("content", "")

                    if search_query in content:
                        print(f"   ✅ MATCH found in entry {entry_id}")
                        print(f"      Content: {content}")
                        print(f"      Metadata: {payload.get('metadata', {})}")
                    else:
                        print(f"   ❌ No match in entry {entry_id}")
                        print(f"      Content: {content[:100]}...")
        except Exception as e:
            print(f"   ❌ Stream not found or error: {e}")

        # Check vector memory search
        vector_keys = await redis_client.keys("mem:*")
        print(f"\n🔢 Checking {len(vector_keys)} vector memory entries...")

        matches = 0
        for vector_key in vector_keys:
            try:
                content = await redis_client.hget(vector_key, "content")
                namespace_stored = await redis_client.hget(vector_key, "namespace")

                if content and namespace_stored:
                    content_str = content.decode()
                    namespace_str = namespace_stored.decode()

                    if namespace_str == namespace and search_query in content_str:
                        matches += 1
                        print(f"   ✅ MATCH in vector key: {vector_key.decode()}")
                        print(f"      Content: {content_str}")
            except Exception as e:
                print(f"   ❌ Error checking vector key {vector_key}: {e}")

        print(f"\n📊 Total vector matches found: {matches}")

    except Exception as e:
        print(f"❌ Error in memory search test: {e}")
    finally:
        await redis_client.close()


async def test_memory_reader():
    reader = MemoryReaderNode(
        node_id="test_memory_reader",
        namespace="processed_numbers",
        limit=5,
        enable_context_search=True,
        similarity_threshold=0.3,
    )

    context = {
        "input": "1",
        "session_id": "default",
        "namespace": "processed_numbers",
    }

    result = await reader.run(context)
    print(f"Full result: {result}")
    print()

    # Check result structure
    result_obj = result.get("result", {})
    print(f"Result object keys: {result_obj.keys()}")
    print()

    memories = result_obj.get("memories", "NONE")
    print(f"Memories: {memories}")
    print(f"Memories type: {type(memories)}")
    print()

    if memories != "NONE" and isinstance(memories, list) and len(memories) > 0:
        print(f"✅ SUCCESS! Found {len(memories)} memories!")
        for i, memory in enumerate(memories):
            content = memory.get("content", "")
            similarity = memory.get("similarity", 0)
            print(f'  Memory {i + 1}: content="{content}", similarity={similarity:.3f}')
    else:
        print("❌ No memories found or invalid format")


if __name__ == "__main__":
    print("🚀 Starting OrKa Memory Debug Script")
    print("=" * 50)

    asyncio.run(check_memory_storage())
    asyncio.run(test_memory_search())
    asyncio.run(test_memory_reader())
