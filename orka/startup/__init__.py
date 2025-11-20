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
OrKa Startup Package
===================

This package provides modular startup and service management for OrKa.
It handles infrastructure services (Redis), backend server management,
and orchestrates the complete service lifecycle.

Key Components:
===============
- Configuration management and path discovery
- Redis infrastructure (native & Docker)
- Backend server management
- Health monitoring and service readiness
- Cleanup and shutdown coordination
- Main orchestration logic

This package maintains backward compatibility with the original orka_start.py
while providing a cleaner, more modular architecture.
"""

# Main orchestration functions (primary interface)
# Backend server management
from .backend import is_backend_running, start_backend, terminate_backend_process

# Service cleanup
from .cleanup import (
    cleanup_services,
    cleanup_specific_backend,
    force_kill_processes,
    terminate_all_processes,
)

# Configuration and environment
from .config import (
    configure_backend_environment,
    get_docker_dir,
    get_memory_backend,
    get_service_endpoints,
)

# Infrastructure services (exposed for advanced usage)
from .infrastructure import (  # Redis; Health & monitoring
    check_process_health,
    cleanup_redis_docker,
    display_error,
    display_service_endpoints,
    display_shutdown_complete,
    display_shutdown_message,
    display_startup_success,
    monitor_backend_process,
    start_native_redis,
    start_redis_docker,
    terminate_redis_process,
    wait_for_redis,
    wait_for_services,
)
from .orchestrator import main, run_startup, start_infrastructure

# UI container management
from .ui import cleanup_ui_container, is_ui_container_running, start_ui_container, stop_ui_container

# Public API - these are the main functions that should be used
__all__ = [
    # Main entry points (most commonly used)
    "main",
    "run_startup",
    # Core infrastructure management
    "start_infrastructure",
    "cleanup_services",
    "get_memory_backend",
    "get_docker_dir",
    # Backend management
    "start_backend",
    "is_backend_running",
    "terminate_backend_process",
    # UI container management
    "start_ui_container",
    "stop_ui_container",
    "is_ui_container_running",
    "cleanup_ui_container",
    # Service-specific functions (for compatibility)
    "start_native_redis",
    "start_redis_docker",
    "wait_for_redis",
    "wait_for_services",
    # Configuration
    "configure_backend_environment",
    "get_service_endpoints",
    # Advanced cleanup
    "cleanup_specific_backend",
    "terminate_all_processes",
    "force_kill_processes",
    # Monitoring & health
    "monitor_backend_process",
    "check_process_health",
    # User interface helpers
    "display_service_endpoints",
    "display_startup_success",
    "display_shutdown_message",
    "display_shutdown_complete",
    "display_error",
    # Service-specific cleanup
    "terminate_redis_process",
    "cleanup_redis_docker",
]
