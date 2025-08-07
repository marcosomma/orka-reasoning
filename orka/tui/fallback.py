"""
Fallback interface implementations for when Rich is not available.
"""

import json
import logging
import os
import sys
import time
from typing import Any, TypeVar, cast

logger = logging.getLogger(__name__)

from ..memory_logger import BaseMemoryLogger, create_memory_logger

# Type variable for memory logger
MemoryLogger = TypeVar("MemoryLogger", bound=BaseMemoryLogger)


class FallbackInterface:
    """Basic fallback interface when Rich is not available."""

    def run_basic_fallback(self, args: Any) -> int:
        """Basic fallback interface when Rich is not available."""
        try:
            backend = cast(
                str,
                getattr(args, "backend", None)
                or os.getenv(
                    "ORKA_MEMORY_BACKEND",
                    "redisstack",
                ),
            )

            # Provide proper Redis URL based on backend
            if backend == "redisstack":
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
            else:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

            memory = create_memory_logger(backend=backend, redis_url=redis_url)

            if getattr(args, "json", False):
                return self.basic_json_watch(memory, backend, args)
            else:
                return self.basic_display_watch(memory, backend, args)

        except Exception as e:
            logger.error(f"Error in basic fallback: {e}")
            return 1

    def basic_json_watch(self, memory: MemoryLogger, backend: str, args: Any) -> int:
        """Basic JSON mode memory watch."""
        try:
            while True:
                try:
                    stats = memory.get_memory_stats()

                    output = {
                        "timestamp": stats.get("timestamp"),
                        "backend": backend,
                        "stats": stats,
                    }

                    logger.info(json.dumps(output, indent=2, default=str))
                    time.sleep(getattr(args, "interval", 5))

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(json.dumps({"error": str(e), "backend": backend}))
                    time.sleep(getattr(args, "interval", 5))

        except KeyboardInterrupt:
            pass

        return 0

    def basic_display_watch(self, memory: MemoryLogger, backend: str, args: Any) -> int:
        """Basic display mode memory watch."""
        try:
            while True:
                try:
                    # Clear screen unless disabled
                    if not getattr(args, "no_clear", False):
                        os.system("cls" if os.name == "nt" else "clear")

                    logger.info("=== OrKa Memory Watch ===")
                    logger.info(f"Backend: {backend} | Interval: {getattr(args, 'interval', 5)}s")
                    logger.info("-" * 60)

                    # Get comprehensive stats
                    stats = memory.get_memory_stats()

                    # Display basic metrics
                    logger.info("📊 Memory Statistics:")
                    logger.info(f"   Total Entries: {stats.get('total_entries', 0)}")
                    logger.info(f"   Stored Memories: {stats.get('stored_memories', 0)}")
                    logger.info(f"   Orchestration Logs: {stats.get('orchestration_logs', 0)}")

                    time.sleep(getattr(args, "interval", 5))

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in memory watch: {e}")
                    time.sleep(getattr(args, "interval", 5))

        except KeyboardInterrupt:
            pass

        return 0
