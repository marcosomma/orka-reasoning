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
Infrastructure Management Package
=================================

This package provides infrastructure service management for OrKa including
Redis, Kafka, and health monitoring capabilities.
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
from .kafka import (
    cleanup_kafka_docker,
    get_kafka_services,
    initialize_schema_registry,
    start_kafka_docker,
    wait_for_kafka_services,
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
    # Kafka management
    "cleanup_kafka_docker",
    "get_kafka_services",
    "initialize_schema_registry",
    "start_kafka_docker",
    "wait_for_kafka_services",
    # Redis management
    "cleanup_redis_docker",
    "start_native_redis",
    "start_redis_docker",
    "terminate_redis_process",
    "wait_for_redis",
]
