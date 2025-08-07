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
Service Orchestrator
===================

This module handles the main orchestration of OrKa services including startup,
monitoring, and shutdown coordination.
"""

import asyncio
import logging
import subprocess
import sys

from .backend import start_backend
from .cleanup import cleanup_services
from .config import get_memory_backend
from .infrastructure.health import (
    display_error,
    display_service_endpoints,
    display_shutdown_complete,
    display_shutdown_message,
    display_startup_success,
    monitor_backend_process,
    wait_for_services,
)
from .infrastructure.kafka import start_kafka_docker
from .infrastructure.redis import start_native_redis

logger = logging.getLogger(__name__)


def start_infrastructure(backend: str) -> dict[str, subprocess.Popen]:
    """
    Start the infrastructure services natively.

    Redis will be started as a native process on port 6380.
    Kafka services will still use Docker when needed.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')

    Returns:
        Dict[str, subprocess.Popen]: Dictionary of started processes

    Raises:
        RuntimeError: If Redis Stack is not available or fails to start
        subprocess.CalledProcessError: If Kafka Docker services fail to start
    """
    processes = {}

    logger.info(f"Starting {backend.upper()} backend...")

    # Always start Redis natively for all backends (except when explicitly using Docker)
    if backend in ["redis", "redisstack", "kafka", "dual"]:
        redis_proc = start_native_redis(6380)
        if redis_proc is not None:
            processes["redis"] = redis_proc
        # If redis_proc is None, Redis is running via Docker and managed by Docker daemon

    # Start Kafka services via Docker only when needed
    if backend in ["kafka", "dual"]:
        start_kafka_docker()

    return processes


async def main() -> None:
    """
    Main entry point for starting and managing OrKa services.

    This asynchronous function:
    1. Determines which backend to use (Redis, Kafka, or dual)
    2. Starts the appropriate infrastructure services (Redis natively, Kafka via Docker)
    3. Waits for services to be ready
    4. Launches the OrKa backend server
    5. Monitors the backend process to ensure it's running
    6. Handles graceful shutdown on keyboard interrupt

    The function runs until interrupted (e.g., via Ctrl+C), at which point
    it cleans up all started processes and containers.
    """
    # Determine backend type
    backend = get_memory_backend()

    # Display startup information
    display_service_endpoints(backend)

    # Track all processes for cleanup
    processes = {}
    backend_proc = None

    try:
        # Start infrastructure
        processes = start_infrastructure(backend)

        # Wait for services to be ready
        wait_for_services(backend)

        # Start Orka backend
        backend_proc = start_backend(backend)
        processes["backend"] = backend_proc

        display_startup_success()

        # Monitor processes
        await monitor_backend_process(backend_proc)

    except KeyboardInterrupt:
        display_shutdown_message()
    except Exception as e:
        display_error(e)
    finally:
        # Always cleanup processes
        cleanup_services(backend, processes)
        display_shutdown_complete()


def run_startup() -> None:
    """
    Run the startup process with proper error handling.

    This function serves as the main entry point and handles
    keyboard interrupts and unexpected errors gracefully.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle any remaining KeyboardInterrupt that might bubble up
        logger.warning("🛑 Shutdown complete.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
