# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
OrKa CLI Package
===============

Modular CLI architecture with backward compatibility.

This package provides a clean modular structure for the OrKa CLI while maintaining
100% backward compatibility with existing code. All functions that were previously
available in `orka.orka_cli` are now properly organized into focused modules but
remain accessible through the same import patterns.

Architecture Overview
--------------------

**Core Modules:**
- `types` - Type definitions for events and payloads
- `core` - Core functionality including run_cli_entrypoint
- `utils` - Shared utilities like setup_logging
- `parser` - Command-line argument parsing logic

**Command Modules:**
- `memory/` - Memory management commands (stats, cleanup, configure, watch)
- `orchestrator/` - Orchestrator operations (run commands)

**Backward Compatibility:**
All existing imports continue to work:

```python
# These imports still work exactly as before
from orka.orka_cli import run_cli_entrypoint, memory_stats, setup_logging

# Module usage also works
import orka.orka_cli
result = orka.orka_cli.run_cli_entrypoint(config, input_text)
```

**Benefits of Modular Structure:**
- Easier maintenance and testing
- Clear separation of concerns
- Improved code organization
- Extensible architecture for new features
"""

# Import all public functions for backward compatibility
from .core import run_cli_entrypoint
from .memory import (
    _memory_watch_display,
    _memory_watch_fallback,
    _memory_watch_json,
    memory_cleanup,
    memory_configure,
    memory_stats,
    memory_watch,
)
from .orchestrator import run_orchestrator
from .parser import create_parser, setup_subcommands
from .types import Event, EventPayload
from .utils import setup_logging

# Re-export everything for backward compatibility
__all__ = [
    # Core functionality
    "run_cli_entrypoint",
    "setup_logging",
    # Memory management
    "memory_cleanup",
    "memory_configure",
    "memory_stats",
    "memory_watch",
    "_memory_watch_display",
    "_memory_watch_fallback",
    "_memory_watch_json",
    # Orchestrator operations
    "run_orchestrator",
    # Parser functionality
    "create_parser",
    "setup_subcommands",
    # Types
    "Event",
    "EventPayload",
]
