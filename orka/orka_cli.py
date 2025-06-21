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
OrKa CLI Interface
==================

This module provides a command-line interface (CLI) for the OrKa orchestration framework,
allowing users to run OrKa workflows directly from the terminal. It handles command-line
argument parsing, workflow initialization, and result presentation.

Usage
-----
.. code-block:: bash

    python -m orka.orka_cli path/to/config.yml "Your input query"

Command-line Arguments
----------------------
* ``config`` - Path to the YAML configuration file (required)
* ``input`` - Query or input text to process (required)
* ``--log-to-file`` - Save execution trace to a JSON log file (optional)

The CLI supports both direct console usage and programmatic invocation through the
``run_cli_entrypoint`` function, which can be used by other applications to embed
OrKa functionality.

Example
-------
.. code-block:: python

    import asyncio
    from orka.orka_cli import run_cli_entrypoint

    async def run_workflow():
        result = await run_cli_entrypoint(
            "workflows/qa_pipeline.yml",
            "What is the capital of France?",
            log_to_file=True
        )
        print(result)

    asyncio.run(run_workflow())
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

from orka.orchestrator import Orchestrator

from .memory_logger import create_memory_logger

logger = logging.getLogger(__name__)


class EventPayload(TypedDict):
    """
    Type definition for event payload.

    Attributes:
        message: Human-readable message about the event
        status: Status of the event (e.g., "success", "error", "in_progress")
        data: Optional structured data associated with the event
    """

    message: str
    status: str
    data: Optional[Dict[str, Any]]


class Event(TypedDict):
    """
    Type definition for event structure.

    Represents a complete event record in the orchestration system.

    Attributes:
        agent_id: Identifier of the agent that generated the event
        event_type: Type of event (e.g., "start", "end", "error")
        timestamp: ISO-format timestamp for when the event occurred
        payload: Structured event payload with message, status, and data
        run_id: Optional identifier for the orchestration run
        step: Optional step number in the orchestration sequence
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
    Run the OrKa orchestrator with the given configuration and input.

    This function serves as the primary programmatic entry point for running
    OrKa workflows from other applications. It initializes the orchestrator,
    runs the workflow, and handles result formatting and logging.

    Args:
        config_path: Path to the YAML configuration file
        input_text: Input question or statement for the orchestrator
        log_to_file: If True, save the orchestration trace to a log file

    Returns:
        The result of the orchestration run, which can be:

        * A dictionary mapping agent IDs to their outputs
        * A list of event records from the execution
        * A simple string output for basic workflows

    Example:
        .. code-block:: python

            result = await run_cli_entrypoint(
                "configs/qa_workflow.yml",
                "Who was the first person on the moon?",
                log_to_file=True
            )
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
        # Get backend from args or environment
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redis")
        memory = create_memory_logger(backend=backend)

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
        # Get backend from args or environment
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redis")
        memory = create_memory_logger(backend=backend)

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
    """Display or test memory decay configuration."""
    try:
        # Get backend from environment or args
        backend = args.backend or os.getenv("ORKA_MEMORY_BACKEND", "redis")

        print("=== OrKa Memory Decay Configuration ===")
        print(f"Backend: {backend}")

        # Display environment variables
        print("\nEnvironment Variables:")
        env_vars = [
            "ORKA_MEMORY_BACKEND",
            "ORKA_MEMORY_DECAY_ENABLED",
            "ORKA_MEMORY_DECAY_SHORT_TERM_HOURS",
            "ORKA_MEMORY_DECAY_LONG_TERM_HOURS",
            "ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES",
        ]

        for var in env_vars:
            value = os.getenv(var, "not set")
            print(f"  {var}: {value}")

        # Test configuration by creating a memory logger
        print("\nTesting Configuration:")
        try:
            memory = create_memory_logger(backend=backend)
            if hasattr(memory, "decay_config"):
                config = memory.decay_config
                print(f"  Decay Enabled: {config.get('enabled', False)}")
                print(f"  Short-term Hours: {config.get('default_short_term_hours', 1.0)}")
                print(f"  Long-term Hours: {config.get('default_long_term_hours', 24.0)}")
                print(f"  Check Interval: {config.get('check_interval_minutes', 30)} minutes")
            else:
                print("  Memory logger does not support decay configuration")
        except Exception as e:
            print(f"  Error creating memory logger: {e}")

    except Exception as e:
        print(f"Error displaying configuration: {e}", file=sys.stderr)
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
    """Watch memory statistics in real-time with rich terminal UI."""
    try:
        # Get backend from args or environment
        backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redis")

        # Check for Kafka backend limitation
        if backend.lower() == "kafka":
            print("🚫 Kafka Memory Watch Limitation")
            print("=" * 50)
            print("❌ Cannot observe Kafka memory across different sessions/processes.")
            print("📋 Kafka memory logger stores data in-memory per Python process,")
            print("   so memory entries created by orchestrator runs are not visible")
            print("   to separate CLI processes.")
            print()
            print("💡 Recommended Solutions:")
            print("   1. Use Redis backend for development monitoring:")
            print('      $env:ORKA_MEMORY_BACKEND="redis"; python -m orka.orka_cli memory watch')
            print(
                "   2. Redis provides identical decay functionality with cross-session visibility",
            )
            print("   3. For production Kafka usage, implement monitoring within your orchestrator")
            print()
            print("✅ Both Redis and Kafka backends have identical TTL/decay functionality!")
            return 1

        memory = create_memory_logger(backend=backend)

        if args.json:
            # JSON mode - simple output without rich
            return _memory_watch_json(memory, backend, args)

        # Rich-based interface
        try:
            from rich import box
            from rich.columns import Columns
            from rich.console import Console
            from rich.layout import Layout
            from rich.live import Live
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            console = Console()

            def create_display():
                """Create the rich display layout."""
                # Get current statistics
                stats = memory.get_memory_stats()
                current_time = datetime.now().strftime("%H:%M:%S")

                # Create main layout
                layout = Layout()

                # Header
                header_text = Text(f"OrKa Memory Watch - {current_time}", style="bold cyan")
                header_text.append(f" | Backend: {backend}", style="dim")
                header_text.append(f" | Refresh: {args.interval}s", style="dim")

                # Main stats panel - compact layout for efficiency
                main_stats = Table.grid(padding=0)
                main_stats.add_column(style="bold", ratio=1)
                main_stats.add_column(style="green", ratio=1)
                main_stats.add_column(style="bold", ratio=1)
                main_stats.add_column(style="green", ratio=1)

                # Arrange stats in 2 columns to save vertical space
                main_stats.add_row(
                    "🔧 Backend:",
                    str(stats.get("backend", backend)),
                    "⚡ Decay:",
                    str(stats.get("decay_enabled", False)),
                )
                main_stats.add_row(
                    "📊 Streams:",
                    str(stats.get("total_streams", 0)),
                    "📝 Entries:",
                    str(stats.get("total_entries", 0)),
                )
                main_stats.add_row(
                    "🗑️ Expired:",
                    str(stats.get("expired_entries", 0)),
                    "",
                    "",  # Empty cells for alignment
                )

                # Add memory types summary in compact format
                memory_types_summary = stats.get("entries_by_memory_type", {})
                if memory_types_summary:
                    # Create compact memory type display
                    short_term = memory_types_summary.get("short_term", 0)
                    long_term = memory_types_summary.get("long_term", 0)
                    unknown = memory_types_summary.get("unknown", 0)

                    if short_term > 0 or long_term > 0:
                        main_stats.add_row(
                            "🔥 Short-term:",
                            f"{short_term}" if short_term > 0 else "[dim]0[/dim]",
                            "💾 Long-term:",
                            f"{long_term}" if long_term > 0 else "[dim]0[/dim]",
                        )

                    if unknown > 0:
                        main_stats.add_row(
                            "❓ Unknown:",
                            f"{unknown}",
                            "",
                            "",
                        )
                else:
                    main_stats.add_row("🧠 Memory:", "[dim]No entries[/dim]", "", "")

                # Create entry types table - optimized for long lists with stable sizing
                entries_table = Table(title="Entries by Type", box=box.ROUNDED, show_lines=False)
                entries_table.add_column("Type", style="cyan", no_wrap=True, ratio=2)
                entries_table.add_column("Count", justify="right", style="magenta", width=6)
                entries_table.add_column("Progress", min_width=15, ratio=1)

                if stats.get("entries_by_type"):
                    total_entries = max(stats.get("total_entries", 1), 1)
                    type_items = sorted(
                        stats["entries_by_type"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )

                    for event_type, count in type_items:
                        # Create progress bar
                        percentage = (count / total_entries) * 100
                        bar_filled = int((count / total_entries) * 15)  # Shorter bar for space
                        bar = "█" * bar_filled + "░" * (15 - bar_filled)

                        entries_table.add_row(
                            event_type,
                            str(count),
                            f"[green]{bar}[/green] {percentage:.1f}%",
                        )

                    # Add padding rows to maintain consistent height
                    current_rows = len(type_items)
                    min_rows = 3
                    for _ in range(max(0, min_rows - current_rows)):
                        entries_table.add_row("", "", "")
                else:
                    entries_table.add_row("[dim]No entries[/dim]", "[dim]0[/dim]", "[dim]N/A[/dim]")
                    # Add padding for consistent height
                    for _ in range(2):
                        entries_table.add_row("", "", "")

                # Create memory types table - optimized layout with stable sizing
                memory_table = Table(title="Memory Types", box=box.ROUNDED, show_lines=False)
                memory_table.add_column("Type", style="cyan", ratio=2)
                memory_table.add_column("Count", justify="right", style="magenta", width=6)
                memory_table.add_column("Status", style="bold", ratio=1)

                # Force populate memory types table
                memory_types_data = stats.get("entries_by_memory_type", {})
                if memory_types_data and any(count > 0 for count in memory_types_data.values()):
                    # Sort by count, then by type name for consistent display
                    sorted_memory_types = sorted(
                        memory_types_data.items(),
                        key=lambda x: (-x[1], x[0]),  # Sort by count desc, then name asc
                    )

                    rows_added = 0
                    for memory_type, count in sorted_memory_types:
                        if count > 0:  # Only show types with actual entries
                            if memory_type == "short_term":
                                status = "[yellow]Fast Decay[/yellow]"
                            elif memory_type == "long_term":
                                status = "[green]Persistent[/green]"
                            else:
                                status = "[red]Unknown[/red]"

                            memory_table.add_row(memory_type, str(count), status)
                            rows_added += 1

                    # Add padding rows to maintain consistent height
                    min_rows = 3
                    for _ in range(max(0, min_rows - rows_added)):
                        memory_table.add_row("", "", "")
                else:
                    # Only add placeholder when we truly have no data
                    memory_table.add_row(
                        "[dim]No memory entries[/dim]",
                        "[dim]0[/dim]",
                        "[dim]N/A[/dim]",
                    )
                    # Add padding for consistent height
                    for _ in range(2):
                        memory_table.add_row("", "", "")

                # Create layout structure - make it dynamic and content-aware
                # Adjust ratios based on content size
                entry_count = len(stats.get("entries_by_type", {}))
                memory_type_count = len(
                    [x for x in stats.get("entries_by_memory_type", {}).values() if x > 0],
                )

                # Use compact mode if requested or if there are many entries
                is_compact = getattr(args, "compact", False) or entry_count > 6

                # Fixed layout to prevent jumping - use absolute sizes
                layout.split_column(
                    Layout(Panel(header_text, style="bold blue"), size=3),
                    Layout(Panel(main_stats, title="Statistics", style="green"), size=6),
                    Layout(
                        Columns([entries_table, memory_table], equal=True),
                        size=15,  # Fixed size to prevent jumping
                    ),
                    Layout(
                        Panel(
                            Text("Press Ctrl+C to exit", style="dim italic", justify="center"),
                            style="dim",
                        ),
                        size=3,
                    ),
                )

                return layout

            # Alternative approach: Clear screen and redraw instead of Live
            if args.no_clear:
                # Use Live display for no-clear mode
                try:
                    with Live(
                        create_display(),
                        refresh_per_second=0.3,  # Slower refresh
                        console=console,
                        screen=True,
                        auto_refresh=True,
                    ) as live:
                        try:
                            while True:
                                time.sleep(args.interval)
                                live.update(create_display())
                        except KeyboardInterrupt:
                            pass

                    console.print("\n🛑 [bold red]OrKa Memory Watch stopped by user.[/bold red]")
                    return 0
                except Exception as e:
                    console.print(f"❌ [red]Rich display error: {e}[/red]")
                    return _memory_watch_simple(memory, backend, args)
            else:
                # Use clear screen approach to eliminate jumping
                try:
                    while True:
                        # Clear screen
                        if os.name == "nt":  # Windows
                            os.system("cls")
                        else:  # Unix/Linux/Mac
                            os.system("clear")

                        # Render the display
                        console.print(create_display())

                        # Wait for next refresh
                        time.sleep(args.interval)
                except KeyboardInterrupt:
                    pass

        except ImportError:
            console.print("❌ [yellow]Rich library not available. Using simple mode.[/yellow]")
            return _memory_watch_simple(memory, backend, args)

    except Exception as e:
        print(f"❌ Error watching memory: {e}", file=sys.stderr)
        return 1


def _memory_watch_json(memory, backend, args):
    """JSON mode for memory watch - simple output without curses."""
    prev_stats = {}
    iteration = 0

    try:
        while True:
            iteration += 1
            stats = memory.get_memory_stats()
            current_time = datetime.now().strftime("%H:%M:%S")

            output = {
                "timestamp": current_time,
                "iteration": iteration,
                "backend": backend,
                "stats": stats,
            }

            print(json.dumps(output, indent=2))
            time.sleep(args.interval)

    except KeyboardInterrupt:
        return 0


def _memory_watch_simple(memory, backend, args):
    """Simple fallback mode without curses."""
    print(f"OrKa Memory Watch (Backend: {backend}) - Press Ctrl+C to exit")
    print("Note: Using simple mode - install curses for better display")
    print("-" * 60)

    prev_stats = {}
    iteration = 0

    try:
        while True:
            iteration += 1
            stats = memory.get_memory_stats()
            current_time = datetime.now().strftime("%H:%M:%S")

            print(f"\n[{current_time}] Iteration #{iteration}")
            print(
                f"Entries: {stats.get('total_entries', 0)} | Expired: {stats.get('expired_entries', 0)} | Decay: {stats.get('decay_enabled', False)}",
            )

            if stats.get("entries_by_memory_type"):
                types_str = " | ".join(
                    [f"{k}: {v}" for k, v in stats["entries_by_memory_type"].items()],
                )
                print(f"Types: {types_str}")

            prev_stats = stats.copy()
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n🛑 Watch stopped.")
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
        choices=["redis", "kafka"],
        help="Memory backend to use",
    )
    stats_parser.set_defaults(func=memory_stats)

    # Memory cleanup
    cleanup_parser = memory_subparsers.add_parser("cleanup", help="Clean up expired memory entries")
    cleanup_parser.add_argument(
        "--backend",
        choices=["redis", "kafka"],
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
        choices=["redis", "kafka"],
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
        choices=["redis", "kafka"],
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
