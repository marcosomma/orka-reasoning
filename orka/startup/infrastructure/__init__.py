# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Infrastructure Management Package
=================================

This package provides infrastructure service management for OrKa including
Redis and health monitoring capabilities.
"""

from .health import (
    check_process_health,
    display_error,
    display_service_endpoints,
    display_shutdown_complete,
    display_shutdown_message,
    display_startup_success,
    monitor_backend_process,
    wait_for_services,
)
from .redis import (
    cleanup_redis_docker,
    start_native_redis,
    start_redis_docker,
    terminate_redis_process,
    wait_for_redis,
)

__all__ = [
    # Health monitoring
    "check_process_health",
    "display_error",
    "display_service_endpoints",
    "display_shutdown_complete",
    "display_shutdown_message",
    "display_startup_success",
    "monitor_backend_process",
    "wait_for_services",
    # Redis management
    "cleanup_redis_docker",
    "start_native_redis",
    "start_redis_docker",
    "terminate_redis_process",
    "wait_for_redis",
]
