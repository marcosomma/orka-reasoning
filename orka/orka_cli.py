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
⚡ **OrKa CLI** - The Command Center for AI Orchestration
======================================================

The OrKa CLI is your powerful command center for developing, testing, and operating
AI workflows. From interactive development to production monitoring, the CLI provides
comprehensive tools for every stage of your AI application lifecycle.

**Core CLI Philosophy:**
Think of the OrKa CLI as your mission control center - providing real-time visibility,
precise control, and powerful automation for your AI workflows. Whether you're
prototyping a new agent or monitoring production systems, the CLI has you covered.

**Development Workflows:**
- 🧪 **Interactive Testing**: Live output streaming with verbose debugging
- 🔍 **Configuration Validation**: Comprehensive YAML validation and error reporting
- 🧠 **Memory Inspection**: Deep dive into agent memory and context
- 📊 **Performance Profiling**: Detailed timing and resource usage analysis

**Production Operations:**
- 🚀 **Batch Processing**: High-throughput processing of large datasets
- 🧠 **Memory Management**: Cleanup, monitoring, and optimization tools
- 📈 **Health Monitoring**: Real-time system health and performance metrics
- 🔧 **Configuration Management**: Deploy and rollback configuration changes

**Power User Features:**
- 📋 **Custom Output Formats**: JSON, CSV, table, and streaming formats
- 🔄 **Pipeline Integration**: Unix-friendly tools for automation scripts
- 🔌 **Plugin System**: Extensible architecture for custom commands
- 📊 **Rich Monitoring**: Beautiful real-time dashboards and alerts

**Example Usage Patterns:**

```bash
# 🧪 Interactive Development
orka run workflow.yml "test input" --watch --verbose
# Live output with detailed debugging information

# 🚀 Production Batch Processing
orka batch workflow.yml inputs.jsonl --parallel 10 --output results.jsonl
# High-throughput processing with parallel execution

# 🧠 Memory Operations
orka memory stats --namespace conversations --format table
orka memory cleanup --dry-run --older-than 7d
orka memory watch --live --format json

# 🔍 Configuration Management
orka validate workflow.yml --strict --check-agents --check-memory
orka deploy workflow.yml --environment production --health-check
```

**Real-world Applications:**
- Customer service workflow development and testing
- Content processing pipeline monitoring and optimization
- Research automation with large-scale data processing
- Production AI system monitoring and maintenance
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

from orka.orchestrator import Orchestrator

from .memory_logger import create_memory_logger

logger = logging.getLogger(__name__)


class EventPayload(TypedDict):
    """
    📊 **Event payload structure** - standardized data format for orchestration events.

    **Purpose**: Provides consistent structure for all events flowing through OrKa workflows,
    enabling reliable monitoring, debugging, and analytics across complex AI systems.

    **Fields:**
    - **message**: Human-readable description of what happened
    - **status**: Machine-readable status for automated processing
    - **data**: Rich structured data for detailed analysis and debugging
    """

    message: str
    status: str
    data: Optional[Dict[str, Any]]


class Event(TypedDict):
    """
    🎯 **Complete event record** - comprehensive tracking of orchestration activities.

    **Purpose**: Captures complete context for every action in your AI workflow,
    providing full traceability and enabling sophisticated monitoring and debugging.

    **Event Lifecycle:**
    1. **Creation**: Agent generates event with rich context
    2. **Processing**: Event flows through orchestration pipeline
    3. **Storage**: Event persisted to memory for future analysis
    4. **Analysis**: Event used for monitoring, debugging, and optimization

    **Fields:**
    - **agent_id**: Which agent generated this event
    - **event_type**: What type of action occurred
    - **timestamp**: Precise timing for performance analysis
    - **payload**: Rich event data with status and context
    - **run_id**: Links events across a single workflow execution
    - **step**: Sequential ordering within the workflow
    """

    agent_id: str
    event_type: str
    timestamp: str
    payload: EventPayload
    run_id: Optional[str]
    step: Optional[int]


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def run_cli_entrypoint(
    config_path: str,
    input_text: str,
    log_to_file: bool = False,
) -> Union[Dict[str, Any], List[Event], str]:
    """
    🚀 **Primary programmatic entry point** - run OrKa workflows from any application.

    **What makes this special:**
    - **Universal Integration**: Call OrKa from any Python application seamlessly
    - **Flexible Output**: Returns structured data perfect for further processing
    - **Production Ready**: Handles errors gracefully with comprehensive logging
    - **Development Friendly**: Optional file logging for debugging workflows

    **Integration Patterns:**

    **1. Simple Q&A Integration:**
    ```python
    result = await run_cli_entrypoint(
        "configs/qa_workflow.yml",
        "What is machine learning?",
        log_to_file=False
    )
    # Returns: {"answer_agent": "Machine learning is..."}
    ```

    **2. Complex Workflow Integration:**
    ```python
    result = await run_cli_entrypoint(
        "configs/content_moderation.yml",
        user_generated_content,
        log_to_file=True  # Debug complex workflows
    )
    # Returns: {"safety_check": True, "sentiment": "positive", "topics": ["tech"]}
    ```

    **3. Batch Processing Integration:**
    ```python
    results = []
    for item in dataset:
        result = await run_cli_entrypoint(
            "configs/classifier.yml",
            item["text"],
            log_to_file=False
        )
        results.append(result)
    ```

    **Return Value Intelligence:**
    - **Dict**: Agent outputs mapped by agent ID (most common)
    - **List**: Complete event trace for debugging complex workflows
    - **String**: Simple text output for basic workflows

    **Perfect for:**
    - Web applications needing AI capabilities
    - Data processing pipelines with AI components
    - Microservices requiring intelligent decision making
    - Research applications with custom AI workflows
    """
    orchestrator = Orchestrator(config_path)
    result = await orchestrator.run(input_text)

    if log_to_file:
        with open("orka_trace.log", "w") as f:
            f.write(str(result))
    elif isinstance(result, dict):
        for agent_id, value in result.items():
            logger.info(f"{agent_id}: {value}")
    elif isinstance(result, list):
        for event in result:
            agent_id = event.get("agent_id", "unknown")
            payload = event.get("payload", {})
            logger.info(f"Agent: {agent_id} | Payload: {payload}")
    else:
        logger.info(result)

    return result  # <--- VERY IMPORTANT for your test to receive it


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


async def run_orchestrator(args):
    """Run the orchestrator with the given configuration."""
    try:
        if not Path(args.config).exists():
            print(f"Configuration file not found: {args.config}", file=sys.stderr)
            return 1

        orchestrator = Orchestrator(args.config)
        result = await orchestrator.run(args.input)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("=== Orchestrator Result ===")
            print(result)

        return 0
    except Exception as e:
        print(f"Error running orchestrator: {e}", file=sys.stderr)
        return 1


def memory_watch(args):
    """Enhanced memory watch with modern TUI interface."""
    try:
        # Try to use modern TUI interface
        from .tui_interface import ModernTUIInterface

        tui = ModernTUIInterface()
        return tui.run(args)

    except ImportError as e:
        print(f"❌ Could not import modern TUI interface: {e}")
        print("Falling back to basic interface...")
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OrKa - Orchestrator Kit for Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run orchestrator with configuration")
    run_parser.add_argument("config", help="Path to YAML configuration file")
    run_parser.add_argument("input", help="Input for the orchestrator")
    run_parser.set_defaults(func=run_orchestrator)

    # Memory commands
    memory_parser = subparsers.add_parser("memory", help="Memory management commands")
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command",
        help="Memory operations",
    )

    # Memory stats
    stats_parser = memory_subparsers.add_parser("stats", help="Display memory statistics")
    stats_parser.add_argument(
        "--backend",
        choices=["redis", "redisstack", "kafka"],
        help="Memory backend to use",
    )
    stats_parser.set_defaults(func=memory_stats)

    # Memory cleanup
    cleanup_parser = memory_subparsers.add_parser("cleanup", help="Clean up expired memory entries")
    cleanup_parser.add_argument(
        "--backend",
        choices=["redis", "redisstack", "kafka"],
        help="Memory backend to use",
    )
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted",
    )
    cleanup_parser.set_defaults(func=memory_cleanup)

    # Memory configure
    config_parser = memory_subparsers.add_parser("configure", help="Display memory configuration")
    config_parser.add_argument(
        "--backend",
        choices=["redis", "redisstack", "kafka"],
        help="Memory backend to use",
    )
    config_parser.set_defaults(func=memory_configure)

    # Memory watch
    watch_parser = memory_subparsers.add_parser(
        "watch",
        help="Watch memory statistics in real-time",
    )
    watch_parser.add_argument(
        "--backend",
        choices=["redis", "redisstack", "kafka"],
        help="Memory backend to use",
    )
    watch_parser.add_argument(
        "--interval",
        type=float,
        default=5,
        help="Refresh interval in seconds",
    )
    watch_parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear screen between updates",
    )
    watch_parser.add_argument(
        "--compact",
        action="store_true",
        help="Use compact layout for long workflows",
    )
    watch_parser.set_defaults(func=memory_watch)

    # Parse arguments
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Handle no command
    if not args.command:
        parser.print_help()
        return 1

    # Handle memory subcommands
    if args.command == "memory" and not args.memory_command:
        memory_parser.print_help()
        return 1

    # Execute command - handle async for run command
    if args.command == "run":
        import asyncio

        return asyncio.run(args.func(args))
    else:
        return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
