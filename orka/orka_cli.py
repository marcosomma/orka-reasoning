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
OrKa CLI - Command Line Interface
=================================

The OrKa CLI provides a comprehensive command-line interface for managing and operating
OrKa AI workflows. From development and testing to production monitoring, the CLI offers
tools for every stage of the AI application lifecycle.

Core Features
------------

**Workflow Operations:**
- Execute orchestrated workflows with real-time output
- Validate YAML configurations before deployment
- Debug workflows with verbose logging and tracing
- Batch processing for high-throughput scenarios

**Memory Management:**
- View memory statistics and usage patterns
- Clean up expired memories with configurable policies
- Monitor memory operations in real-time
- Configure memory backends and settings

**Development Tools:**
- Interactive workflow testing and debugging
- Configuration validation with detailed error reporting
- Live output streaming for development workflows
- Performance profiling and optimization insights

Architecture
-----------

**Modular Design:**
The CLI is built with a modular architecture that separates concerns:

- `core.py` - Core functionality including run_cli_entrypoint
- `parser.py` - Command-line argument parsing and subcommand setup
- `utils.py` - Shared utilities like logging configuration
- `memory/` - Memory management commands (stats, cleanup, watch, configure)
- `orchestrator/` - Orchestrator operations (run commands)

**Backward Compatibility:**
All existing imports and usage patterns continue to work unchanged:

```python
# These imports still work exactly as before
from orka.orka_cli import run_cli_entrypoint, memory_stats, setup_logging

# Module usage also works
import orka.orka_cli
result = orka.orka_cli.run_cli_entrypoint(config, input_text)
```

Command Structure
----------------

**Main Commands:**
- `orka run` - Execute workflows with configuration files
- `orka memory` - Memory management operations
- `orka validate` - Configuration validation (future)

**Memory Subcommands:**
- `orka memory stats` - Display memory usage statistics
- `orka memory cleanup` - Clean expired memories with dry-run support
- `orka memory watch` - Real-time memory monitoring
- `orka memory configure` - Memory backend configuration

**Global Options:**
- `--verbose` - Enable detailed logging output
- `--json` - Format output as JSON for automation
- `--help` - Display help information for any command

Usage Examples
--------------

**Basic Workflow Execution:**
```bash
# Execute a workflow with input
orka run workflow.yml "process this text"

# With verbose logging
orka run workflow.yml "input" --verbose

# JSON output for automation
orka run workflow.yml "input" --json
```

**Memory Operations:**
```bash
# View memory statistics
orka memory stats

# Clean expired memories (dry run)
orka memory cleanup --dry-run

# Real-time memory monitoring
orka memory watch --live

# Configure memory backend
orka memory configure --backend redis --url redis://localhost:6379
```

**Configuration Validation:**
```bash
# Validate workflow configuration
orka validate workflow.yml

# Strict validation with agent checking
orka validate workflow.yml --strict --check-agents
```

Implementation Details
---------------------

**Error Handling:**
- Comprehensive error messages with context
- Graceful handling of configuration errors
- Detailed validation feedback for YAML files
- Recovery suggestions for common issues

**Output Formatting:**
- Human-readable tables for interactive use
- JSON output for automation and scripting
- Streaming output for long-running operations
- Colored output for improved readability

**Integration Features:**
- Unix-friendly design for shell scripting
- Exit codes for automation workflows
- Environment variable support
- Configuration file discovery

**Performance:**
- Efficient processing for large datasets
- Parallel execution support where applicable
- Memory-efficient streaming for large outputs
- Optimized startup time for quick operations

Development Integration
----------------------

**IDE Support:**
- Rich help text for all commands and options
- Autocomplete support for common shells
- Detailed error messages with line numbers
- Configuration validation with syntax highlighting

**Automation:**
- JSON output for programmatic consumption
- Reliable exit codes for CI/CD integration
- Batch processing capabilities
- Silent mode for automated scripts

**Debugging:**
- Verbose logging with multiple levels
- Trace ID propagation for request tracking
- Performance timing information
- Memory usage monitoring
"""

import argparse
import sys

# Import everything from the new modular CLI structure
# This preserves 100% backward compatibility
from orka.cli import *

# Import additional functions that might be accessed directly
from orka.cli.parser import create_parser, setup_subcommands


def main():
    """Main CLI entry point - now uses modular components."""
    parser = create_parser()
    setup_subcommands(parser)

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
        # Find and show memory parser help
        subparsers_actions = [
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ]
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                if choice == "memory":
                    subparser.print_help()
                    return 1

    # Execute command - handle async for run command
    if args.command == "run":
        import asyncio

        return asyncio.run(args.func(args))
    else:
        return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
