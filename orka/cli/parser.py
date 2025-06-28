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
CLI Parser
==========

This module contains the command-line argument parsing logic for the OrKa CLI.
"""

import argparse

from .memory import memory_cleanup, memory_configure, memory_stats, memory_watch
from .orchestrator import run_orchestrator


def create_parser():
    """Create and configure the main argument parser."""
    parser = argparse.ArgumentParser(
        description="OrKa - Orchestrator Kit for Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    return parser


def setup_subcommands(parser):
    """Set up all subcommands and their arguments."""
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
        help="Watch memory statistics in real-time with modern TUI",
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
    watch_parser.add_argument(
        "--use-rich",
        action="store_true",
        help="Use Rich fallback interface instead of Textual",
    )
    watch_parser.add_argument(
        "--fallback",
        action="store_true",
        help="Use basic terminal interface (no TUI)",
    )
    watch_parser.set_defaults(func=memory_watch)

    return parser
