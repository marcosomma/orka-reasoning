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
Service Cleanup
===============

This module handles cleanup and shutdown of OrKa services.
"""

import logging
import subprocess
from typing import Dict

from .infrastructure.kafka import cleanup_kafka_docker
from .infrastructure.redis import terminate_redis_process

logger = logging.getLogger(__name__)


def cleanup_services(backend: str, processes: Dict[str, subprocess.Popen] = {}) -> None:
    """
    Clean up and stop services for the specified backend.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')
        processes: Dictionary of running processes to terminate
    """
    try:
        # Terminate native processes
        if processes:
            for name, proc in processes.items():
                if name == "redis":
                    terminate_redis_process(proc)
                # Generic process termination
                elif proc and proc.poll() is None:  # Process is still running
                    print(f"🛑 Stopping {name} process...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                        print(f"✅ {name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"⚠️ Force killing {name} process...")
                        proc.kill()
                        proc.wait()

        # Stop Docker services for Kafka if needed
        if backend in ["kafka", "dual"]:
            cleanup_kafka_docker()

        logger.info("All services stopped.")
    except Exception as e:
        logger.error(f"Error stopping services: {e}")


def terminate_all_processes(processes: Dict[str, subprocess.Popen]) -> None:
    """
    Terminate all managed processes gracefully.

    Args:
        processes: Dictionary of process names to process objects
    """
    for name, proc in processes.items():
        if proc and proc.poll() is None:  # Process is still running
            try:
                print(f"🛑 Stopping {name} process...")
                proc.terminate()
                proc.wait(timeout=5)
                print(f"✅ {name} stopped gracefully")
            except subprocess.TimeoutExpired:
                print(f"⚠️ Force killing {name} process...")
                proc.kill()
                proc.wait()
            except Exception as e:
                print(f"⚠️ Error stopping {name}: {e}")


def force_kill_processes(processes: Dict[str, subprocess.Popen]) -> None:
    """
    Force kill all managed processes.

    Args:
        processes: Dictionary of process names to process objects
    """
    for name, proc in processes.items():
        if proc and proc.poll() is None:  # Process is still running
            try:
                print(f"⚠️ Force killing {name} process...")
                proc.kill()
                proc.wait()
            except Exception as e:
                print(f"⚠️ Error force killing {name}: {e}")


def cleanup_specific_backend(backend: str) -> None:
    """
    Clean up services specific to a backend type.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')
    """
    if backend in ["kafka", "dual"]:
        cleanup_kafka_docker()

    # Redis cleanup is handled by process termination
    # since it's managed as a native process
