"""
Fallback interface implementations for when Rich is not available.
"""

import json
import os
import sys
import time

from ..memory_logger import create_memory_logger


class FallbackInterface:
    """Basic fallback interface when Rich is not available."""

    def run_basic_fallback(self, args):
        """Basic fallback interface when Rich is not available."""
        try:
            backend = getattr(args, "backend", None) or os.getenv(
                "ORKA_MEMORY_BACKEND",
                "redisstack",
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
            print(f"❌ Error in basic fallback: {e}", file=sys.stderr)
            return 1

    def basic_json_watch(self, memory, backend: str, args):
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

                    print(json.dumps(output, indent=2, default=str))
                    time.sleep(getattr(args, "interval", 5))

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(json.dumps({"error": str(e), "backend": backend}), file=sys.stderr)
                    time.sleep(getattr(args, "interval", 5))

        except KeyboardInterrupt:
            pass

        return 0

    def basic_display_watch(self, memory, backend: str, args):
        """Basic display mode memory watch."""
        try:
            while True:
                try:
                    # Clear screen unless disabled
                    if not getattr(args, "no_clear", False):
                        os.system("cls" if os.name == "nt" else "clear")

                    print("=== OrKa Memory Watch ===")
                    print(f"Backend: {backend} | Interval: {getattr(args, 'interval', 5)}s")
                    print("-" * 60)

                    # Get comprehensive stats
                    stats = memory.get_memory_stats()

                    # Display basic metrics
                    print("📊 Memory Statistics:")
                    print(f"   Total Entries: {stats.get('total_entries', 0)}")
                    print(f"   Stored Memories: {stats.get('stored_memories', 0)}")
                    print(f"   Orchestration Logs: {stats.get('orchestration_logs', 0)}")

                    time.sleep(getattr(args, "interval", 5))

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error in memory watch: {e}", file=sys.stderr)
                    time.sleep(getattr(args, "interval", 5))

        except KeyboardInterrupt:
            pass

        return 0
