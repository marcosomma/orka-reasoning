#!/usr/bin/env python3
"""
Vector Search Test - Verify embedder and vector search functionality
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "orka"))

from orka.memory_logger import create_memory_logger


def test_vector_search():
    """Test vector search functionality."""
    print("🔍 Testing Vector Search Functionality")
    print("=" * 50)

    # Create RedisStack memory logger with embedder
    try:
        memory = create_memory_logger(
            backend="redisstack",
            redis_url="redis://localhost:6380/0",
        )
        print("✅ Memory logger created successfully")
    except Exception as e:
        print(f"❌ Failed to create memory logger: {e}")
        return

    # Check if embedder is available
    embedder_available = hasattr(memory, "embedder") and memory.embedder is not None
    print(f"🤖 Embedder available: {'✅ Yes' if embedder_available else '❌ No'}")

    if embedder_available:
        embedder = memory.embedder
        print(f"   Model: {getattr(embedder, 'model_name', 'Unknown')}")
        print(f"   Dimension: {getattr(embedder, 'embedding_dim', 'Unknown')}")
        print(f"   Model loaded: {getattr(embedder, 'model_loaded', 'Unknown')}")

        # Test embedder directly
        try:
            import asyncio

            test_text = "This is a test sentence for embedding"
            embedding = asyncio.run(embedder.encode(test_text))
            print(f"✅ Embedding test successful: shape={embedding.shape}, type={type(embedding)}")
            print(f"   Sample values: {embedding[:5]}")
        except Exception as e:
            print(f"❌ Embedding test failed: {e}")

    # Test vector search through memory logger
    print("\n📝 Testing memory storage with embeddings...")
    try:
        # Store a test memory
        key = memory.log_memory(
            content="Python is a high-level programming language known for its simplicity",
            node_id="test_vector_node",
            trace_id="vector_test",
            metadata={"log_type": "memory", "category": "stored", "test": True},
            importance_score=0.9,
            memory_type="short_term",
            expiry_hours=1,
        )
        print(f"✅ Stored test memory: {key}")

        # Test vector search
        results = memory.search_memories(
            query="programming language Python",
            num_results=5,
            log_type="memory",
        )

        if results:
            print(f"✅ Vector search successful: found {len(results)} results")
            for i, result in enumerate(results, 1):
                content = result.get("content", "")[:60] + (
                    "..." if len(result.get("content", "")) > 60 else ""
                )
                score = result.get("similarity_score", 0)
                print(f"   [{i}] Score: {score:.3f} | {content}")
        else:
            print("⚠️ Vector search returned no results")

    except Exception as e:
        print(f"❌ Vector search test failed: {e}")

    # Test performance metrics
    print("\n📊 Performance Metrics:")
    try:
        if hasattr(memory, "get_performance_metrics"):
            metrics = memory.get_performance_metrics()
            print(f"   Vector search enabled: {metrics.get('vector_search_enabled', False)}")
            print(f"   Embedder model: {metrics.get('embedder_model', 'None')}")
            print(f"   Embedding dimension: {metrics.get('embedding_dimension', 0)}")

            index_status = metrics.get("index_status", {})
            print(f"   Index status: {index_status.get('status', 'unknown')}")
            if index_status.get("status") == "available":
                print(f"   Index documents: {index_status.get('num_docs', 0)}")
        else:
            print("   Performance metrics not available")
    except Exception as e:
        print(f"❌ Failed to get performance metrics: {e}")

    print("\n💡 Now run: python -m orka.orka_cli memory watch --backend redisstack")
    print("   to see the enhanced memory watch with vector search enabled!")


if __name__ == "__main__":
    test_vector_search()
