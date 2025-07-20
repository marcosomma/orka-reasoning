#!/usr/bin/env python3
"""
OrKa Service Runner
====================

Main entry point for starting the OrKa service stack.
By default, uses Kafka backend for event streaming and Redis for memory operations.

This provides the best of both worlds:
- Kafka for persistent event streaming and audit trails
- Redis for fast memory operations and fork/join coordination

Environment Variables:
--------------------
ORKA_MEMORY_BACKEND: Backend type ('kafka', 'redis', 'redisstack', or 'dual')
REDIS_URL: Redis connection URL (default: redis://localhost:6380/0)
KAFKA_BOOTSTRAP_SERVERS: Kafka broker list (default: localhost:9092)
KAFKA_TOPIC_PREFIX: Prefix for Kafka topics (default: orka-memory)
"""
import os
import sys

# Set default backend to Kafka (hybrid with Redis for memory)
if "ORKA_MEMORY_BACKEND" not in os.environ:
    os.environ["ORKA_MEMORY_BACKEND"] = "kafka"

# Ensure Redis is configured for memory operations
if "REDIS_URL" not in os.environ:
    os.environ["REDIS_URL"] = "redis://localhost:6380/0"

# Set default Kafka configuration if not already set
if "KAFKA_BOOTSTRAP_SERVERS" not in os.environ:
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

if "KAFKA_TOPIC_PREFIX" not in os.environ:
    os.environ["KAFKA_TOPIC_PREFIX"] = "orka-memory"

# Import all functions from the modular startup package to maintain backward compatibility
from orka.startup import (  # Main orchestration functions
    initialize_schema_registry,
    main,
    run_startup,
    wait_for_redis,
)

# The _wait_for_redis function is now wait_for_redis (removed underscore)
# Provide backward compatibility alias
_wait_for_redis = wait_for_redis

# The _initialize_schema_registry function is now initialize_schema_registry (removed underscore)
# Provide backward compatibility alias
_initialize_schema_registry = initialize_schema_registry

# Public API for backward compatibility
__all__ = [
    "_initialize_schema_registry",
    "_wait_for_redis",
    "initialize_schema_registry",
    "main",
    "run_startup",
    "wait_for_redis",
]

print("🚀 Starting OrKa with Kafka + Redis Hybrid Backend...")
print("📋 Configuration:")
print(f"   • Memory Backend: {os.environ['ORKA_MEMORY_BACKEND']}")
print(f"   • Kafka Servers: {os.environ['KAFKA_BOOTSTRAP_SERVERS']}")
print(f"   • Kafka Topic Prefix: {os.environ['KAFKA_TOPIC_PREFIX']}")
print(f"   • Redis URL: {os.environ['REDIS_URL']}")


def cli_main():
    """
    CLI entry point for orka-start command.
    This function is referenced in pyproject.toml's console_scripts.
    """
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutdown complete.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


# Main execution block
if __name__ == "__main__":
    cli_main()
