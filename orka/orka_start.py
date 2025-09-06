#!/usr/bin/env python3
"""
OrKa Service Runner
====================

Main entry point for starting the OrKa service stack.
By default, uses RedisStack backend for high-performance memory operations with HNSW vector indexing.

This provides optimal performance with simplified infrastructure:
- RedisStack for ultra-fast memory operations and vector search
- HNSW indexing for 100x faster semantic search
- Simplified architecture with single backend

Environment Variables:
--------------------
ORKA_MEMORY_BACKEND: Backend type ('redisstack' or 'redis')
REDIS_URL: Redis connection URL (default: redis://localhost:6380/0)
"""
import os
import sys

# Initialize logging first
from orka.utils.logging_utils import setup_logging

setup_logging()

# Set default backend to RedisStack for optimal performance
if "ORKA_MEMORY_BACKEND" not in os.environ:
    os.environ["ORKA_MEMORY_BACKEND"] = "redisstack"

# Ensure Redis is configured for memory operations
if "REDIS_URL" not in os.environ:
    os.environ["REDIS_URL"] = "redis://localhost:6380/0"

# Import all functions from the modular startup package to maintain backward compatibility
from orka.startup import (  # Main orchestration functions
    main,
    run_startup,
    wait_for_redis,
)

# The _wait_for_redis function is now wait_for_redis (removed underscore)
# Provide backward compatibility alias
_wait_for_redis = wait_for_redis


# Public API for backward compatibility
__all__ = [
    "_wait_for_redis",
    "main",
    "run_startup",
    "wait_for_redis",
]

backend = os.environ["ORKA_MEMORY_BACKEND"]
print(f"🚀 Starting OrKa with {backend.upper()} Backend...")
print("📋 Configuration:")
print(f"   • Memory Backend: {backend}")
print(f"   • Redis URL: {os.environ['REDIS_URL']}")
print(f"   • LOG_LEVEL: {os.getenv('ORKA_LOG_LEVEL', 'INFO')}")


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
