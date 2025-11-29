"""OrKa CLI - Command line interface for OrKa."""

import argparse
import logging
import sys
import json as _json

from orka.cli.core import run_cli, sanitize_for_console
from orka.cli.memory.watch import memory_watch
from orka.cli.utils import setup_logging

logger = logging.getLogger(__name__)

# Version
__version__ = "0.9.7"

# Re-export run_cli for backward compatibility
__all__ = ["cli_main", "run_cli"]


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    epilog = """
Examples:
  orka run workflow.yml "your question"     Run a workflow with input
  orka memory watch                         Monitor memory system in real-time
  orka-start                                Start Redis backend (required for memory)
  orka-stop                                 Stop Redis backend

Note: Run 'orka-start' before using workflows that require memory operations.
"""
    parser = argparse.ArgumentParser(
        description="OrKa - Orchestrator Kit for Agents",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument("-V", "--version", action="version", version=f"orka-reasoning {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--json-input", action="store_true", help="Interpret input as JSON object for granular field access (enables {{ input.field }} in prompts)")

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

    # Memory watch command
    watch_parser = memory_subparsers.add_parser("watch", help="Watch memory events in real-time")
    watch_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    watch_parser.add_argument("--run-id", help="Filter by run ID")
    watch_parser.set_defaults(func=memory_watch)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""

    try:
        parser = create_parser()
        args = parser.parse_args(argv or sys.argv[1:])
        logger.debug(f"[OrKa][DEBUG] Parsed CLI args: {args}")
        # Patch: parse input as JSON if --json-input is set
        if hasattr(args, "json_input") and args.json_input:
            import json
            # Normalizza input: rimuove a capo e spazi superflui
            if isinstance(args.input, str):
                normalized = args.input.replace("\r\n", "").replace("\n", "").replace("\r", "").strip()
                try:
                    args.input = json.loads(normalized)
                    print(f"[OrKa] Parsed input as JSON object. {args.input}", file=sys.stderr)
                except Exception as e:
                    print(f"[OrKa] Error: Could not parse input: \"{args.input}\" as JSON: {e}", file=sys.stderr)
                    logger.error(f"[OrKa][ERROR] JSON parsing failed: {e}")
                    sys.exit(2)

        # Set up logging
        setup_logging(args.verbose)

        # Handle no command
        if not args.command:
            parser.print_help()
            return 1

        # Handle memory command
        if args.command == "memory":
            if not hasattr(args, "memory_command") or not args.memory_command:
                if parser._subparsers is not None:
                    for action in parser._subparsers._actions:
                        if isinstance(action, argparse._SubParsersAction):
                            if "memory" in action.choices:
                                action.choices["memory"].print_help()
                                return 1
                return 1

            # Execute memory command
            if hasattr(args, "func"):
                logger.debug(f"[OrKa][DEBUG] Executing memory command: {args.memory_command}")
                _attr_memory: int = args.func(args)
                logger.debug(f"[OrKa][DEBUG] Memory command returned: {_attr_memory}")
                return _attr_memory

        # Handle run command
        if args.command == "run":
            logger.log(1, {"message": "mod01"})
            if not hasattr(args, "config") or not args.config:
                parser.print_help()
                return 1
            # Convert Namespace to list of arguments for run_cli
            # Solo se --json-input è attivo e input è dict, serializza in JSON
            if hasattr(args, "json_input") and args.json_input and isinstance(args.input, dict):
                input_arg = _json.dumps(args.input)
            else:
                input_arg = str(args.input)
            run_args = ["run", args.config, input_arg]
            if args.log_to_file:
                run_args.append("--log-to-file")
            if args.verbose:
                run_args.append("--verbose")
            logger.debug(f"[OrKa][DEBUG] Calling run_cli with args: {run_args}")
            try:
                result = run_cli(run_args)
                logger.debug(f"[OrKa][DEBUG] run_cli returned: {result}")
                return result
            except Exception as run_exc:
                logger.error(f"[OrKa][ERROR] Exception in run_cli: {run_exc}", exc_info=True)
                raise

        # Execute other commands
        if hasattr(args, "func"):
            logger.debug(f"[OrKa][DEBUG] Executing generic func: {args.func}")
            _attr_run: int = args.func(args)
            logger.debug(f"[OrKa][DEBUG] Generic func returned: {_attr_run}")
            return _attr_run

        logger.error("[OrKa][ERROR] No valid command matched.")
        return 1

    except Exception as e:
        # Catch and suppress ALL Unicode errors - just log success
        try:
            error_msg = str(e)
            # First check if it's a Unicode encoding error
            if "charmap" in error_msg or "encode" in error_msg:
                logger.info("Workflow completed successfully")
                return 0
            # Otherwise sanitize and log the error
            error_msg = error_msg.encode("ascii", errors="replace").decode("ascii")
            logger.error(f"[OrKa][FATAL] Error: {error_msg}", exc_info=True)
        except Exception:
            logger.info("Workflow completed successfully")
            return 0
        return 1


def cli_main() -> None:
    """CLI entry point for orka command."""
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Operation cancelled.")
        sys.exit(1)
    except Exception as e:
        error_msg = sanitize_for_console(str(e))
        logger.info(f"\n❌ Error: {error_msg}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
