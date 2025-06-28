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

**Modular Architecture:**
This CLI has been refactored into a modular architecture for improved maintainability
while preserving 100% backward compatibility. All existing imports and usage patterns
continue to work unchanged.
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
