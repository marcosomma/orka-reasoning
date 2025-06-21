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
    """Set up logging configuration."""
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
        # Get backend from environment or args
        backend = args.backend or os.getenv("ORKA_MEMORY_BACKEND", "redis")

        # Create memory logger
        memory = create_memory_logger(backend=backend)

        # Get statistics
        stats = memory.get_memory_stats()

        # Display results
        if args.json:
            print(json.dumps(stats, indent=2))
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
        # Get backend from environment or args
        backend = args.backend or os.getenv("ORKA_MEMORY_BACKEND", "redis")

        # Create memory logger
        memory = create_memory_logger(backend=backend)

        # Perform cleanup
        if args.dry_run:
            print("=== Dry Run: Memory Cleanup Preview ===")
        else:
            print("=== Memory Cleanup ===")

        result = memory.cleanup_expired_memories(dry_run=args.dry_run)

        # Display results
        if args.json:
            print(json.dumps(result, indent=2))
        else:
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
                    print(f"  {entry['stream']}: {entry['agent_id']} - {entry['event_type']}")
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
