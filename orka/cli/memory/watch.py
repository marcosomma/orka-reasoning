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
Memory Watch Functionality
==========================

This module contains memory watch functionality with TUI interface support.
"""

import json
import os
import sys
import time

from orka.memory_logger import create_memory_logger


def memory_watch(args):
    """Modern TUI interface with Textual (default) or Rich fallback."""
    # Check if user explicitly wants fallback interface
    if getattr(args, "fallback", False):
        print("ℹ️  Using basic terminal interface as requested")
        return _memory_watch_fallback(args)

    try:
        # Use the modern TUI interface (defaults to Textual)
        from orka.tui_interface import ModernTUIInterface

        tui = ModernTUIInterface()
        return tui.run(args)

    except ImportError as e:
        print(f"❌ Could not import TUI interface: {e}")
        print("Falling back to basic terminal interface...")
        return _memory_watch_fallback(args)
    except Exception as e:
        print(f"❌ Error starting memory watch: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


def _memory_watch_fallback(args):
    """Fallback memory watch with basic interface."""
    try:
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")

        # Provide proper Redis URL based on backend
        if backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        memory = create_memory_logger(backend=backend, redis_url=redis_url)

        if getattr(args, "json", False):
            return _memory_watch_json(memory, backend, args)
        else:
            return _memory_watch_display(memory, backend, args)

    except Exception as e:
        print(f"❌ Error in fallback memory watch: {e}", file=sys.stderr)
        return 1


def _memory_watch_json(memory, backend: str, args):
    """JSON mode memory watch with continuous updates."""
    try:
        while True:
            try:
                stats = memory.get_memory_stats()

                output = {
                    "timestamp": stats.get("timestamp"),
                    "backend": backend,
                    "stats": stats,
                }

                # Add recent stored memories
                try:
                    if hasattr(memory, "get_recent_stored_memories"):
                        recent_memories = memory.get_recent_stored_memories(5)
                    elif hasattr(memory, "search_memories"):
                        recent_memories = memory.search_memories(
                            query=" ",
                            num_results=5,
                            log_type="memory",
                        )
                    else:
                        recent_memories = []

                    output["recent_stored_memories"] = recent_memories
                except Exception as e:
                    output["recent_memories_error"] = str(e)

                # Add performance metrics for RedisStack
                if backend == "redisstack" and hasattr(memory, "get_performance_metrics"):
                    try:
                        output["performance"] = memory.get_performance_metrics()
                    except Exception:
                        pass

                print(json.dumps(output, indent=2, default=str))

                time.sleep(args.interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(json.dumps({"error": str(e), "backend": backend}), file=sys.stderr)
                time.sleep(args.interval)

    except KeyboardInterrupt:
        pass

    return 0


def _memory_watch_display(memory, backend: str, args):
    """Interactive display mode with continuous updates."""
    try:
        while True:
            try:
                # Clear screen unless disabled
                if not getattr(args, "no_clear", False):
                    os.system("cls" if os.name == "nt" else "clear")

                print("=== OrKa Memory Watch ===")
                print(
                    f"Backend: {backend} | Interval: {getattr(args, 'interval', 5)}s | Press Ctrl+C to exit",
                )
                print("-" * 60)

                # Get comprehensive stats
                stats = memory.get_memory_stats()

                # Display basic metrics
                print("📊 Memory Statistics:")
                print(f"   Total Entries: {stats.get('total_entries', 0)}")
                print(f"   Active Entries: {stats.get('active_entries', 0)}")
                print(f"   Expired Entries: {stats.get('expired_entries', 0)}")
                print(f"   Stored Memories: {stats.get('stored_memories', 0)}")
                print(f"   Orchestration Logs: {stats.get('orchestration_logs', 0)}")

                # Show recent stored memories
                print("\n🧠 Recent Stored Memories:")
                try:
                    # Get recent memories using the dedicated method
                    if hasattr(memory, "get_recent_stored_memories"):
                        recent_memories = memory.get_recent_stored_memories(5)
                    elif hasattr(memory, "search_memories"):
                        recent_memories = memory.search_memories(
                            query=" ",
                            num_results=5,
                            log_type="memory",
                        )
                    else:
                        recent_memories = []

                    if recent_memories:
                        for i, mem in enumerate(recent_memories, 1):
                            # Handle bytes content from decode_responses=False
                            raw_content = mem.get("content", "")
                            if isinstance(raw_content, bytes):
                                raw_content = raw_content.decode()
                            content = raw_content[:100] + ("..." if len(raw_content) > 100 else "")

                            # Handle bytes for other fields
                            raw_node_id = mem.get("node_id", "unknown")
                            node_id = (
                                raw_node_id.decode()
                                if isinstance(raw_node_id, bytes)
                                else raw_node_id
                            )

                            print(f"   [{i}] {node_id}: {content}")
                    else:
                        print("   No stored memories found")

                except Exception as e:
                    print(f"   ❌ Error retrieving memories: {e}")

                time.sleep(getattr(args, "interval", 5))

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error in memory watch: {e}", file=sys.stderr)
                time.sleep(getattr(args, "interval", 5))

    except KeyboardInterrupt:
        pass

    return 0
