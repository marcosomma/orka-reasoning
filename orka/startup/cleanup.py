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
Service Cleanup
===============

This module handles cleanup and shutdown of OrKa services.
"""

import logging
import subprocess
from typing import Dict

from .config import get_docker_dir
from .infrastructure.kafka import cleanup_kafka_docker
from .infrastructure.redis import cleanup_redis_docker, terminate_redis_process

logger = logging.getLogger(__name__)


def cleanup_services(backend: str, processes: Dict[str, subprocess.Popen] = {}) -> None:
    """
    Clean up and stop services for the specified backend.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')
        processes: Dictionary of running processes to terminate
    """
    try:
        logger.info("🧹 Starting comprehensive service cleanup...")

        # Terminate native processes
        if processes:
            for name, proc in processes.items():
                if name == "redis":
                    terminate_redis_process(proc)
                # Generic process termination
                elif proc and proc.poll() is None:  # Process is still running
                    logger.info(f"🛑 Stopping {name} process...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                        logger.info(f"✅ {name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"⚠️ Force killing {name} process...")
                        proc.kill()
                        proc.wait()

        # Enhanced Docker cleanup for better reliability
        if backend in ["kafka", "dual"]:
            cleanup_kafka_docker()

        # Always try to cleanup Redis Docker containers (in case they're running)
        if backend in ["redis", "redisstack", "kafka", "dual"]:
            cleanup_redis_docker_enhanced()

        logger.info("✅ All services stopped.")
    except Exception as e:
        logger.error(f"❌ Error stopping services: {e}")
        # Try emergency cleanup
        try:
            emergency_cleanup()
        except Exception as emergency_error:
            logger.error(f"❌ Emergency cleanup also failed: {emergency_error}")


def terminate_all_processes(processes: Dict[str, subprocess.Popen]) -> None:
    """
    Terminate all managed processes gracefully.

    Args:
        processes: Dictionary of process names to process objects
    """
    for name, proc in processes.items():
        if proc and proc.poll() is None:  # Process is still running
            try:
                logger.info(f"🛑 Stopping {name} process...")
                proc.terminate()
                proc.wait(timeout=5)
                logger.info(f"✅ {name} stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ Force killing {name} process...")
                proc.kill()
                proc.wait()
            except Exception as e:
                logger.warning(f"⚠️ Error stopping {name}: {e}")


def force_kill_processes(processes: Dict[str, subprocess.Popen]) -> None:
    """
    Force kill all managed processes.

    Args:
        processes: Dictionary of process names to process objects
    """
    for name, proc in processes.items():
        if proc and proc.poll() is None:  # Process is still running
            try:
                logger.warning(f"⚠️ Force killing {name} process...")
                proc.kill()
                proc.wait()
            except Exception as e:
                logger.warning(f"⚠️ Error force killing {name}: {e}")


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


def cleanup_redis_docker_enhanced() -> None:
    """Enhanced Redis Docker cleanup that handles stuck containers."""
    try:
        import os

        docker_dir = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        logger.info("🛑 Enhanced Redis Docker cleanup...")

        # Force stop and remove Redis containers
        subprocess.run(
            ["docker-compose", "-f", compose_file, "kill", "redis"],
            check=False,
            capture_output=True,
        )

        subprocess.run(
            ["docker-compose", "-f", compose_file, "rm", "-f", "redis"],
            check=False,
            capture_output=True,
        )

        # Also try direct Docker commands in case compose fails
        subprocess.run(["docker", "stop", "docker-redis-1"], check=False, capture_output=True)

        subprocess.run(["docker", "rm", "-f", "docker-redis-1"], check=False, capture_output=True)

        logger.info("✅ Enhanced Redis cleanup completed")

    except Exception as e:
        logger.warning(f"⚠️ Enhanced Redis cleanup failed: {e}")


def emergency_cleanup() -> None:
    """Emergency cleanup when normal cleanup fails."""
    logger.warning("🚨 Performing emergency cleanup...")

    try:
        # Kill all OrKa-related containers
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", "name=docker-"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            container_ids = result.stdout.strip().split("\n")
            for container_id in container_ids:
                if container_id:
                    logger.warning(f"🛑 Force stopping container: {container_id}")
                    subprocess.run(
                        ["docker", "kill", container_id], check=False, capture_output=True
                    )

                    subprocess.run(
                        ["docker", "rm", "-f", container_id], check=False, capture_output=True
                    )

        # Remove OrKa networks
        networks = ["docker_orka-redis-network", "docker_orka-kafka-network"]
        for network in networks:
            subprocess.run(["docker", "network", "rm", network], check=False, capture_output=True)

        logger.info("✅ Emergency cleanup completed")

    except Exception as e:
        logger.error(f"❌ Emergency cleanup failed: {e}")
