# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
import asyncio
import logging
import sys

import pytest

from orka.nodes.memory_reader_node import MemoryReaderNode
from orka.nodes.memory_writer_node import MemoryWriterNode

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_memory_system():
    """Test the memory system with various query variations."""
    # Initialize nodes
    writer = MemoryWriterNode("test_writer")
    reader = MemoryReaderNode("test_reader", namespace="test_namespace")

    # Test content
    content = "Artificial Intelligence was born in 1956 at the Dartmouth Conference where the term was coined by John McCarthy."

    # Write to memory
    logger.info(f"Writing content to memory: {content[:50]}...")
    write_result = await writer.run(
        {"input": content, "session_id": "test_session", "namespace": "test_namespace"}
    )
    logger.info(f"Write result: {write_result}")

    # Verify write was successful
    assert write_result["status"] == "success"

    # Give a moment for Redis to update
    await asyncio.sleep(1)

    # Test different query variations
    test_queries = [
        "When did AI born",
        "When was AI created",
        "When was artificial intelligence invented",
        "Who created AI",
        "AI history",
        "origin of artificial intelligence",
    ]

    # Need at least one successful memory retrieval for the test to pass
    found_at_least_one = False

    for query in test_queries:
        logger.info(f"\nTesting query: '{query}'")
        read_result = await reader.run(
            {
                "input": query,
                "session_id": "test_session",
                "namespace": "test_namespace",
            }
        )

        # Ensure the read operation was successful
        assert read_result["status"] == "success"

        if read_result.get("memories") == "NONE":
            logger.warning(f"❌ No memory found for query: '{query}'")
        else:
            logger.info(f"✅ Memory found for query: '{query}'")
            found_at_least_one = True
            for i, memory in enumerate(read_result.get("memories", [])):
                logger.info(f"  Memory {i + 1}:")
                logger.info(f"    Content: {memory.get('content', '')[:50]}...")
                logger.info(f"    Similarity: {memory.get('similarity', 0):.4f}")
                logger.info(f"    Match type: {memory.get('match_type', 'unknown')}")

    # At least one query should find the memory
    assert found_at_least_one, "No memories were found for any query variations"


# This allows the test to be run directly as a script
if __name__ == "__main__":
    try:
        result = asyncio.run(test_memory_system())
        print("\nTest completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        sys.exit(1)
