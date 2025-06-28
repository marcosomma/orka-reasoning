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
OrKa Service Runner (Backward Compatibility Layer)
==================================================

This module provides backward compatibility for the original OrKa service runner.
The actual implementation has been refactored into the orka.startup package for
better modularity and maintainability.

Key Features:
-----------
1. Multi-Backend Support: Supports both Redis and Kafka memory backends
2. Infrastructure Management: Automates the startup and shutdown of required services
3. Docker Integration: Manages containers via Docker Compose with profiles
4. Process Management: Starts and monitors the OrKa backend server process
5. Graceful Shutdown: Ensures clean teardown of services on exit
6. Path Discovery: Locates configuration files in development and production environments

This module serves as the main entry point for running the complete OrKa service stack.
It can be executed directly to start all necessary services:

```bash
# Start with Redis backend (default)
python -m orka.orka_start

# Start with Kafka backend
ORKA_MEMORY_BACKEND=kafka python -m orka.orka_start

# Start with dual backend (both Redis and Kafka)
ORKA_MEMORY_BACKEND=dual python -m orka.orka_start
```

Once started, the services will run until interrupted (e.g., Ctrl+C), at which point
they will be gracefully shut down.
"""

# Import all functions from the modular startup package to maintain backward compatibility
from orka.startup import (
    initialize_schema_registry,
    # Main orchestration functions
    main,
    run_startup,
    wait_for_redis,
)

# The _wait_for_redis function is now wait_for_redis (removed underscore)
# Provide backward compatibility alias
_wait_for_redis = wait_for_redis

# The _initialize_schema_registry function is now initialize_schema_registry (removed underscore)
# Provide backward compatibility alias
_initialize_schema_registry = initialize_schema_registry

# Public API for backward compatibility
__all__ = [
    "_initialize_schema_registry",
    "_wait_for_redis",
    "initialize_schema_registry",
    "main",
    "run_startup",
    "wait_for_redis",
]

# Main execution block
if __name__ == "__main__":
    run_startup()
