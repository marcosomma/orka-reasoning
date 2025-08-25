# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Memory CLI Commands
==================

This module contains CLI commands for memory management operations including
statistics, cleanup, and configuration.
"""

import json
import logging
import os
import sys
from typing import Any

from orka.memory_logger import create_memory_logger

logger = logging.getLogger(__name__)


def memory_stats(args: Any) -> int:
    """Display memory usage statistics."""
    try:
        # Get backend from args or environment, default to redisstack for best performance
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")

        # Provide proper Redis URL based on backend
        if backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")

        # Try RedisStack first for enhanced performance, fallback to Redis if needed
        try:
            memory = create_memory_logger(backend=str(backend), redis_url=redis_url)
        except ImportError as e:
            if backend == "redisstack":
                logger.info(f"RedisStack not available ({e}), falling back to Redis")
                backend = "redis"
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
                memory = create_memory_logger(backend=backend, redis_url=redis_url)
            else:
                raise

        # Get statistics
        stats = memory.get_memory_stats()

        # Display results
        if args.json:
            output = {"stats": stats}
            logger.info(json.dumps(output, indent=2))
        else:
            logger.info("=== OrKa Memory Statistics ===")
            logger.info(f"Backend: {stats.get('backend', backend)}")
            logger.info(f"Decay Enabled: {stats.get('decay_enabled', False)}")
            logger.info(f"Total Streams: {stats.get('total_streams', 0)}")
            logger.info(f"Total Entries: {stats.get('total_entries', 0)}")
            logger.info(f"Expired Entries: {stats.get('expired_entries', 0)}")

            if stats.get("entries_by_type"):
                logger.info("\nEntries by Type:")
                for event_type, count in stats["entries_by_type"].items():
                    logger.info(f"  {event_type}: {count}")

            if stats.get("entries_by_memory_type"):
                logger.info("\nEntries by Memory Type:")
                for memory_type, count in stats["entries_by_memory_type"].items():
                    logger.info(f"  {memory_type}: {count}")

            if stats.get("entries_by_category"):
                logger.info("\nEntries by Category:")
                for category, count in stats["entries_by_category"].items():
                    if count > 0:  # Only show categories with entries
                        logger.info(f"  {category}: {count}")

            if stats.get("decay_config"):
                logger.info("\nDecay Configuration:")
                config = stats["decay_config"]
                logger.info(f"  > Short-term retention: {config.get('short_term_hours')}h")
                logger.info(f"  > Long-term retention: {config.get('long_term_hours')}h")
                logger.info(f"  > Check interval: {config.get('check_interval_minutes')}min")
                if config.get("last_decay_check"):
                    logger.info(f"  > Last cleanup: {config['last_decay_check']}")

    except Exception as e:
        logger.error(f"Error getting memory statistics: {e}")
        return 1

    return 0


def memory_cleanup(args: Any) -> int:
    """Clean up expired memory entries."""
    try:
        # Get backend from args or environment, default to redisstack for best performance
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")

        # Provide proper Redis URL based on backend
        if backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")

        # Try RedisStack first for enhanced performance, fallback to Redis if needed
        try:
            memory = create_memory_logger(backend=str(backend), redis_url=redis_url)
        except ImportError as e:
            if backend == "redisstack":
                logger.info(f"⚠️ RedisStack not available ({e}), falling back to Redis")
                backend = "redis"
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
                memory = create_memory_logger(backend=backend, redis_url=redis_url)
            else:
                raise

        # Perform cleanup
        if args.dry_run:
            logger.info("=== Dry Run: Memory Cleanup Preview ===")
        else:
            logger.info("=== Memory Cleanup ===")

        result = memory.cleanup_expired_memories(dry_run=args.dry_run)

        # Display results
        if args.json:
            output = {"cleanup_result": result}
            logger.info(json.dumps(output, indent=2))
        else:
            logger.info(f"Backend: {backend}")
            logger.info(f"Status: {result.get('status', 'completed')}")
            logger.info(f"Deleted Entries: {result.get('deleted_count', 0)}")
            logger.info(f"Streams Processed: {result.get('streams_processed', 0)}")
            logger.info(f"Total Entries Checked: {result.get('total_entries_checked', 0)}")

            if result.get("error_count", 0) > 0:
                logger.info(f"Errors: {result['error_count']}")

            if result.get("duration_seconds"):
                logger.info(f"Duration: {result['duration_seconds']:.2f}s")

            if args.verbose and result.get("deleted_entries"):
                logger.info("\nDeleted Entries:")
                for entry in result["deleted_entries"][:10]:  # Show first 10
                    entry_desc = (
                        f"{entry.get('agent_id', 'unknown')} - {entry.get('event_type', 'unknown')}"
                    )
                    if "stream" in entry:
                        logger.info(f"  {entry['stream']}: {entry_desc}")
                    else:
                        logger.info(f"  {entry_desc}")
                if len(result["deleted_entries"]) > 10:
                    logger.info(f"  ... and {len(result['deleted_entries']) - 10} more")

    except Exception as e:
        logger.error(f"Error during memory cleanup: {e}")
        return 1

    return 0


def memory_configure(args: Any) -> int:
    """Enhanced memory configuration with RedisStack testing."""
    try:
        backend = args.backend or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")

        # Provide proper Redis URL based on backend
        if backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")

        logger.info("=== OrKa Memory Configuration Test ===")
        logger.info(f"Backend: {backend}")

        # Test configuration
        logger.info("\n🧪 Testing Configuration:")
        try:
            memory = create_memory_logger(backend=backend, redis_url=redis_url)

            # Basic decay config test
            if hasattr(memory, "decay_config"):
                config = memory.decay_config
                logger.info(
                    f"✅ Decay Config: {'Enabled' if config.get('enabled', False) else 'Disabled'}",
                )
                if config.get("enabled", False):
                    logger.info(f"   Short-term: {config.get('default_short_term_hours', 1.0)}h")
                    logger.info(f"   Long-term: {config.get('default_long_term_hours', 24.0)}h")
                    logger.info(f"   Check interval: {config.get('check_interval_minutes', 30)}min")
            else:
                logger.info("⚠️  Decay Config: Not available")

            # Backend-specific tests
            if backend == "redisstack":
                logger.info("\n🔍 RedisStack-Specific Tests:")

                # Test index availability
                try:
                    if hasattr(memory, "client"):
                        memory.client.ft("enhanced_memory_idx").info()
                        logger.info("✅ HNSW Index: Available")

                        # Get index details
                        index_info = memory.client.ft("enhanced_memory_idx").info()
                        logger.info(f"   Documents: {index_info.get('num_docs', 0)}")
                        logger.info(
                            f"   Indexing: {'Yes' if index_info.get('indexing', False) else 'No'}",
                        )
                    else:
                        logger.info("⚠️  HNSW Index: Cannot test (no client access)")
                except Exception as e:
                    logger.error(f"❌ HNSW Index: Not available - {e}")

            elif backend == "redis":
                logger.info("\n🔧 Redis-Specific Tests:")

                # Test basic connectivity
                try:
                    if hasattr(memory, "client"):
                        memory.client.ping()
                        logger.info("✅ Redis Connection: Active")
                    else:
                        logger.info("⚠️  Redis Connection: Cannot test")
                except Exception as e:
                    logger.error(f"❌ Redis Connection: Error - {e}")

                # Test decay cleanup
                try:
                    cleanup_result = memory.cleanup_expired_memories(dry_run=True)
                    logger.info("✅ Decay Cleanup: Available")
                    logger.info(
                        f"   Checked: {cleanup_result.get('total_entries_checked', 0)} entries"
                    )
                except Exception as e:
                    logger.error(f"❌ Decay Cleanup: Error - {e}")

            elif backend == "kafka":
                logger.info("\n📡 Kafka-Specific Tests:")

                # Test hybrid backend
                try:
                    if hasattr(memory, "redis_url"):
                        logger.info("✅ Hybrid Backend: Kafka + Redis")
                        logger.info(f"   Kafka topic: {getattr(memory, 'main_topic', 'N/A')}")
                        logger.info(f"   Redis URL: {memory.redis_url}")
                    else:
                        logger.info("⚠️  Hybrid Backend: Configuration unclear")
                except Exception as e:
                    logger.error(f"❌ Hybrid Backend: Error - {e}")

            # Test memory stats retrieval
            try:
                stats = memory.get_memory_stats()
                logger.info("\n✅ Memory Stats: Available")
                logger.info(f"   Total entries: {stats.get('total_entries', 0)}")
                logger.info(f"   Decay enabled: {stats.get('decay_enabled', False)}")

                if stats.get("entries_by_memory_type"):
                    logger.info(
                        f"   Memory types: {len(stats['entries_by_memory_type'])} categories"
                    )

            except Exception as e:
                logger.error(f"\n❌ Memory Stats: Error - {e}")

            logger.info("\n✅ Configuration test completed")

        except Exception as e:
            logger.error(f"❌ Configuration test failed: {e}")
            return 1

    except Exception as e:
        logger.error(f"❌ Error testing configuration: {e}")
        return 1

    return 0
