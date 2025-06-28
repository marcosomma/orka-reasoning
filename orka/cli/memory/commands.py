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

"""
Memory CLI Commands
==================

This module contains CLI commands for memory management operations including
statistics, cleanup, and configuration.
"""

import json
import os
import sys

from orka.memory_logger import create_memory_logger


def memory_stats(args):
    """Display memory usage statistics."""
    try:
        # Get backend from args or environment, default to redisstack for best performance
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")

        # Provide proper Redis URL based on backend
        if backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Try RedisStack first for enhanced performance, fallback to Redis if needed
        try:
            memory = create_memory_logger(backend=backend, redis_url=redis_url)
        except ImportError as e:
            if backend == "redisstack":
                print(f"⚠️ RedisStack not available ({e}), falling back to Redis", file=sys.stderr)
                backend = "redis"
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                memory = create_memory_logger(backend=backend, redis_url=redis_url)
            else:
                raise

        # Get statistics
        stats = memory.get_memory_stats()

        # Display results
        if args.json:
            output = {"stats": stats}
            print(json.dumps(output, indent=2))
        else:
            print("=== OrKa Memory Statistics ===")
            print(f"Backend: {stats.get('backend', backend)}")
            print(f"Decay Enabled: {stats.get('decay_enabled', False)}")
            print(f"Total Streams: {stats.get('total_streams', 0)}")
            print(f"Total Entries: {stats.get('total_entries', 0)}")
            print(f"Expired Entries: {stats.get('expired_entries', 0)}")

            if stats.get("entries_by_type"):
                print("\nEntries by Type:")
                for event_type, count in stats["entries_by_type"].items():
                    print(f"  {event_type}: {count}")

            if stats.get("entries_by_memory_type"):
                print("\nEntries by Memory Type:")
                for memory_type, count in stats["entries_by_memory_type"].items():
                    print(f"  {memory_type}: {count}")

            if stats.get("entries_by_category"):
                print("\nEntries by Category:")
                for category, count in stats["entries_by_category"].items():
                    if count > 0:  # Only show categories with entries
                        print(f"  {category}: {count}")

            if stats.get("decay_config"):
                print("\nDecay Configuration:")
                config = stats["decay_config"]
                print(f"  Short-term retention: {config.get('short_term_hours')}h")
                print(f"  Long-term retention: {config.get('long_term_hours')}h")
                print(f"  Check interval: {config.get('check_interval_minutes')}min")
                if config.get("last_decay_check"):
                    print(f"  Last cleanup: {config['last_decay_check']}")

    except Exception as e:
        print(f"Error getting memory statistics: {e}", file=sys.stderr)
        return 1

    return 0


def memory_cleanup(args):
    """Clean up expired memory entries."""
    try:
        # Get backend from args or environment, default to redisstack for best performance
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")

        # Provide proper Redis URL based on backend
        if backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Try RedisStack first for enhanced performance, fallback to Redis if needed
        try:
            memory = create_memory_logger(backend=backend, redis_url=redis_url)
        except ImportError as e:
            if backend == "redisstack":
                print(f"⚠️ RedisStack not available ({e}), falling back to Redis", file=sys.stderr)
                backend = "redis"
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                memory = create_memory_logger(backend=backend, redis_url=redis_url)
            else:
                raise

        # Perform cleanup
        if args.dry_run:
            print("=== Dry Run: Memory Cleanup Preview ===")
        else:
            print("=== Memory Cleanup ===")

        result = memory.cleanup_expired_memories(dry_run=args.dry_run)

        # Display results
        if args.json:
            output = {"cleanup_result": result}
            print(json.dumps(output, indent=2))
        else:
            print(f"Backend: {backend}")
            print(f"Status: {result.get('status', 'completed')}")
            print(f"Deleted Entries: {result.get('deleted_count', 0)}")
            print(f"Streams Processed: {result.get('streams_processed', 0)}")
            print(f"Total Entries Checked: {result.get('total_entries_checked', 0)}")

            if result.get("error_count", 0) > 0:
                print(f"Errors: {result['error_count']}")

            if result.get("duration_seconds"):
                print(f"Duration: {result['duration_seconds']:.2f}s")

            if args.verbose and result.get("deleted_entries"):
                print("\nDeleted Entries:")
                for entry in result["deleted_entries"][:10]:  # Show first 10
                    entry_desc = (
                        f"{entry.get('agent_id', 'unknown')} - {entry.get('event_type', 'unknown')}"
                    )
                    if "stream" in entry:
                        print(f"  {entry['stream']}: {entry_desc}")
                    else:
                        print(f"  {entry_desc}")
                if len(result["deleted_entries"]) > 10:
                    print(f"  ... and {len(result['deleted_entries']) - 10} more")

    except Exception as e:
        print(f"Error during memory cleanup: {e}", file=sys.stderr)
        return 1

    return 0


def memory_configure(args):
    """Enhanced memory configuration with RedisStack testing."""
    try:
        backend = args.backend or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")

        # Provide proper Redis URL based on backend
        if backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        print("=== OrKa Memory Configuration Test ===")
        print(f"Backend: {backend}")

        # Test configuration
        print("\n🧪 Testing Configuration:")
        try:
            memory = create_memory_logger(backend=backend, redis_url=redis_url)

            # Basic decay config test
            if hasattr(memory, "decay_config"):
                config = memory.decay_config
                print(
                    f"✅ Decay Config: {'Enabled' if config.get('enabled', False) else 'Disabled'}",
                )
                if config.get("enabled", False):
                    print(f"   Short-term: {config.get('default_short_term_hours', 1.0)}h")
                    print(f"   Long-term: {config.get('default_long_term_hours', 24.0)}h")
                    print(f"   Check interval: {config.get('check_interval_minutes', 30)}min")
            else:
                print("⚠️  Decay Config: Not available")

            # Backend-specific tests
            if backend == "redisstack":
                print("\n🔍 RedisStack-Specific Tests:")

                # Test index availability
                try:
                    if hasattr(memory, "client"):
                        memory.client.ft("enhanced_memory_idx").info()
                        print("✅ HNSW Index: Available")

                        # Get index details
                        index_info = memory.client.ft("enhanced_memory_idx").info()
                        print(f"   Documents: {index_info.get('num_docs', 0)}")
                        print(
                            f"   Indexing: {'Yes' if index_info.get('indexing', False) else 'No'}",
                        )
                    else:
                        print("⚠️  HNSW Index: Cannot test (no client access)")
                except Exception as e:
                    print(f"❌ HNSW Index: Not available - {e}")

            elif backend == "redis":
                print("\n🔧 Redis-Specific Tests:")

                # Test basic connectivity
                try:
                    if hasattr(memory, "client"):
                        memory.client.ping()
                        print("✅ Redis Connection: Active")
                    else:
                        print("⚠️  Redis Connection: Cannot test")
                except Exception as e:
                    print(f"❌ Redis Connection: Error - {e}")

                # Test decay cleanup
                try:
                    cleanup_result = memory.cleanup_expired_memories(dry_run=True)
                    print("✅ Decay Cleanup: Available")
                    print(f"   Checked: {cleanup_result.get('total_entries_checked', 0)} entries")
                except Exception as e:
                    print(f"❌ Decay Cleanup: Error - {e}")

            elif backend == "kafka":
                print("\n📡 Kafka-Specific Tests:")

                # Test hybrid backend
                try:
                    if hasattr(memory, "redis_url"):
                        print("✅ Hybrid Backend: Kafka + Redis")
                        print(f"   Kafka topic: {getattr(memory, 'main_topic', 'N/A')}")
                        print(f"   Redis URL: {memory.redis_url}")
                    else:
                        print("⚠️  Hybrid Backend: Configuration unclear")
                except Exception as e:
                    print(f"❌ Hybrid Backend: Error - {e}")

            # Test memory stats retrieval
            try:
                stats = memory.get_memory_stats()
                print("\n✅ Memory Stats: Available")
                print(f"   Total entries: {stats.get('total_entries', 0)}")
                print(f"   Decay enabled: {stats.get('decay_enabled', False)}")

                if stats.get("entries_by_memory_type"):
                    print(f"   Memory types: {len(stats['entries_by_memory_type'])} categories")

            except Exception as e:
                print(f"\n❌ Memory Stats: Error - {e}")

            print("\n✅ Configuration test completed")

        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            return 1

    except Exception as e:
        print(f"❌ Error testing configuration: {e}", file=sys.stderr)
        return 1

    return 0
