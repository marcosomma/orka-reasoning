"""OrKa CLI - Command line interface for OrKa."""

import argparse
import logging
import sys

from orka.cli.core import run_cli

logger = logging.getLogger(__name__)

# Re-export run_cli for backward compatibility
__all__ = ["main", "run_cli"]


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
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
    run_parser.add_argument("config", help="Configuration file path")
    run_parser.add_argument("input", help="Input query or file")
    run_parser.add_argument("--log-to-file", action="store_true", help="Log output to file")
    run_parser.set_defaults(func=run_cli)

    # Memory command
    memory_parser = subparsers.add_parser("memory", help="Memory management commands")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")

    # Memory stats command
    stats_parser = memory_subparsers.add_parser("stats", help="Show memory statistics")
    stats_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    stats_parser.set_defaults(func=lambda args: 0)

    # Memory cleanup command
    cleanup_parser = memory_subparsers.add_parser("cleanup", help="Clean up expired memories")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    cleanup_parser.set_defaults(func=lambda args: 0)

    return parser


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main(argv: list[str] | None = None) -> int | None:
    """Main entry point."""
    try:
        parser = create_parser()
        args = parser.parse_args(argv or sys.argv[1:])

        # Set up logging
        setup_logging(args.verbose)

        # Handle no command
        if not args.command:
            parser.print_help()
            return 1

        # Handle memory command
        if args.command == "memory":
            if not hasattr(args, "memory_command") or not args.memory_command:
                parser.print_help()
                return None

        # Handle run command
        if args.command == "run":
            if not hasattr(args, "config") or not args.config:
                parser.print_help()
                return 1
            # Convert Namespace to list of arguments for run_cli
            run_args = ["run", args.config, args.input]
            if args.log_to_file:
                run_args.append("--log-to-file")
            return run_cli(run_args)

        # Execute other commands
        if hasattr(args, "func"):
            return args.func(args)

        return 1

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    sys.exit(main())
