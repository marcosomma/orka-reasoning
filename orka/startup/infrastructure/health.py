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
Health Checking
===============

This module provides health checking functionality for infrastructure services.
"""

import asyncio
import logging
import subprocess
from typing import Dict

from .kafka import initialize_schema_registry, wait_for_kafka_services

logger = logging.getLogger(__name__)


def wait_for_services(backend: str) -> None:
    """
    Wait for infrastructure services to be ready.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')
    """
    # Redis is already checked during native startup in start_native_redis()
    # No additional waiting needed for Redis

    if backend in ["kafka", "dual"]:
        wait_for_kafka_services()

        # Initialize Schema Registry schemas at startup
        if backend in ["kafka", "dual"]:
            initialize_schema_registry()


async def monitor_backend_process(backend_proc: subprocess.Popen) -> None:
    """
    Monitor the backend process and detect if it stops unexpectedly.

    Args:
        backend_proc: The backend process to monitor

    Raises:
        RuntimeError: If the backend process stops unexpectedly
    """
    while True:
        try:
            await asyncio.sleep(1)
            # Check if backend process is still running
            if backend_proc.poll() is not None:
                logger.error("Orka backend stopped unexpectedly!")
                raise RuntimeError("Backend process terminated")
        except asyncio.CancelledError:
            # This happens when Ctrl+C is pressed, break out of the loop
            break


def display_service_endpoints(backend: str) -> None:
    """
    Display service endpoints for the configured backend.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')
    """
    print(f"🚀 Starting OrKa with {backend.upper()} backend...")
    print("=" * 80)

    if backend in ["redis", "redisstack"]:
        print("📍 Service Endpoints:")
        print("   • Orka API: http://localhost:8000")
        print("   • Redis:    localhost:6380 (native)")
    elif backend == "kafka":
        print("📍 Service Endpoints (Hybrid Kafka + Redis):")
        print("   • Orka API:         http://localhost:8001")
        print("   • Kafka (Events):   localhost:9092")
        print("   • Redis (Memory):   localhost:6380 (native)")
        print("   • Zookeeper:        localhost:2181")
        print("   • Schema Registry:  http://localhost:8081")
        print("   • Schema UI:        http://localhost:8082")
    elif backend == "dual":
        print("📍 Service Endpoints:")
        print("   • Orka API (Dual):  http://localhost:8002")
        print("   • Redis:            localhost:6380 (native)")
        print("   • Kafka:            localhost:9092")
        print("   • Zookeeper:        localhost:2181")
        print("   • Schema Registry:  http://localhost:8081")
        print("   • Schema UI:        http://localhost:8082")

    print("=" * 80)


def display_startup_success() -> None:
    """Display successful startup message."""
    print("")
    print("✅ All services started successfully!")
    print("📝 Press Ctrl+C to stop all services")
    print("")


def display_shutdown_message() -> None:
    """Display graceful shutdown message."""
    print("\n🛑 Shutting down services...")


def display_shutdown_complete() -> None:
    """Display shutdown complete message."""
    print("✅ All services stopped.")


def display_error(error: Exception) -> None:
    """
    Display error message during startup.

    Args:
        error: The exception that occurred
    """
    logger.error(f"Error during startup: {error}")
    print(f"\n❌ Startup failed: {error}")


def check_process_health(processes: Dict[str, subprocess.Popen]) -> bool:
    """
    Check the health of all managed processes.

    Args:
        processes: Dictionary of process name to process object

    Returns:
        bool: True if all processes are healthy, False otherwise
    """
    for name, proc in processes.items():
        if proc and proc.poll() is not None:
            logger.warning(f"Process {name} has terminated unexpectedly")
            return False
    return True
