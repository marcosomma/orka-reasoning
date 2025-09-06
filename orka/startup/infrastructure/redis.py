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
Redis Infrastructure Management
==============================

This module handles Redis Stack management including native startup and Docker fallback.
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from ..config import get_docker_dir

logger = logging.getLogger(__name__)


def start_native_redis(port: int = 6380) -> Optional[subprocess.Popen]:
    """
    Start Redis Stack natively on the specified port, with Docker fallback.

    Args:
        port: Port to start Redis on (default: 6380)

    Returns:
        subprocess.Popen: The Redis process, or None if using Docker

    Raises:
        RuntimeError: If both native and Docker Redis fail to start
    """
    try:
        # Check if Redis Stack is available natively
        logger.info("🔍 Checking Redis Stack availability...")
        result = subprocess.run(
            ["redis-stack-server", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info(f"🔧 Starting Redis Stack natively on port {port}...")

            # Create data directory if it doesn't exist
            data_dir = Path("./redis-data")
            data_dir.mkdir(exist_ok=True)

            # Start Redis Stack with vector capabilities and persistence
            redis_proc = subprocess.Popen(
                [
                    "redis-stack-server",
                    "--port",
                    str(port),
                    "--appendonly",
                    "yes",
                    "--dir",
                    str(data_dir),
                    "--save",
                    "900 1",  # Save if at least 1 key changed in 900 seconds
                    "--save",
                    "300 10",  # Save if at least 10 keys changed in 300 seconds
                    "--save",
                    "60 10000",  # Save if at least 10000 keys changed in 60 seconds
                    "--maxmemory-policy",
                    "allkeys-lru",  # LRU eviction policy
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for Redis to be ready
            wait_for_redis(port)

            logger.info(f"✅ Redis Stack running natively on port {port}")
            return redis_proc
        else:
            raise FileNotFoundError("Redis Stack not found in PATH")

    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("❌ Redis Stack not found natively.")
        logger.info("🐳 Falling back to Docker Redis Stack...")

        try:
            # Use Docker fallback
            return start_redis_docker(port)

        except Exception as docker_error:
            logger.error(f"❌ Docker fallback also failed: {docker_error}")
            logger.info("📦 To fix this, install Redis Stack:")
            logger.info("   • Windows: Download from https://redis.io/download")
            logger.info("   • macOS: brew install redis-stack")
            logger.info("   • Ubuntu: sudo apt install redis-stack-server")
            logger.info("   • Or ensure Docker is available for fallback")
            raise RuntimeError("Both native and Docker Redis Stack unavailable")

    except Exception as e:
        logger.error(f"❌ Failed to start native Redis: {e}")
        raise RuntimeError(f"Redis startup failed: {e}")


def start_redis_docker(port: int = 6380) -> Optional[subprocess.Popen]:
    """
    Start Redis Stack using Docker as a fallback.

    Args:
        port: Port to start Redis on

    Returns:
        Optional[subprocess.Popen]: None since Docker process is managed by Docker daemon

    Raises:
        RuntimeError: If Docker Redis fails to start
    """
    try:
        docker_dir: str = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        logger.info(f"🔧 Starting Redis Stack via Docker on port {port}...")

        # Stop any existing Redis containers
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "down",
                "redis",
            ],
            check=False,
            capture_output=True,
        )

        # Start Redis Stack via Docker
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "redis",
            ],
            check=True,
        )

        # Wait for Redis to be ready
        wait_for_redis(port)

        logger.info(f"✅ Redis Stack running via Docker on port {port}")
        return None

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to start Redis via Docker: {e}")
    except Exception as e:
        raise RuntimeError(f"Docker Redis startup error: {e}")


def wait_for_redis(port: int, max_attempts: int = 30) -> None:
    """
    Wait for Redis to be ready and responsive (works for both native and Docker).

    Args:
        port: Redis port to check
        max_attempts: Maximum number of connection attempts

    Raises:
        RuntimeError: If Redis doesn't become ready within the timeout
    """
    logger.info(f"⏳ Waiting for Redis to be ready on port {port}...")

    # First, check if we're using Docker and use Docker health check
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=docker-redis-1", "--format", "{{.Status}}"],
            capture_output=True, text=True, check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"📦 Redis container status: {result.stdout.strip()}")
            
            # Use Docker health check for more reliable detection
            for attempt in range(max_attempts):
                try:
                    health_result = subprocess.run(
                        ["docker", "exec", "docker-redis-1", "redis-cli", "ping"],
                        capture_output=True, text=True, check=False, timeout=5
                    )
                    
                    if health_result.returncode == 0 and "PONG" in health_result.stdout:
                        logger.info(f"✅ Redis is ready on port {port}! (verified via Docker)")
                        return
                        
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
                
                if attempt < max_attempts - 1:
                    logger.info(f"Redis not ready yet, waiting... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(2)
                else:
                    # Fall back to host connection test
                    logger.warning("Docker health check failed, trying host connection...")
                    break
    except Exception:
        pass  # Fall back to host connection test

    # Fallback to host connection test (for native Redis or if Docker check fails)
    for attempt in range(max_attempts):
        try:
            # Try to connect using redis-cli first (if available)
            try:
                result = subprocess.run(
                    ["redis-cli", "-p", str(port), "ping"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                if result.returncode == 0 and "PONG" in result.stdout:
                    logger.info(f"✅ Redis is ready on port {port}!")
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass  # redis-cli not available, try alternative

            # Fallback to socket + Redis library check with longer timeout
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # Increased timeout for Windows Docker
            socket_result = sock.connect_ex(("localhost", port))
            sock.close()

            if socket_result == 0:
                # Additional check with Redis ping (with retries for Windows Docker)
                try:
                    import redis

                    client = redis.Redis(
                        host="localhost", 
                        port=port, 
                        decode_responses=True,
                        socket_connect_timeout=10,
                        socket_timeout=10,
                        retry_on_timeout=True,
                        retry_on_error=[redis.ConnectionError, redis.TimeoutError]
                    )
                    if client.ping():
                        logger.info(f"✅ Redis is ready on port {port}!")
                        return
                except Exception as e:
                    logger.debug(f"Redis ping failed: {e}")
                    pass  # Continue trying

        except Exception as e:
            logger.debug(f"Connection attempt failed: {e}")
            pass

        if attempt < max_attempts - 1:
            logger.info(f"Redis not ready yet, waiting... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(3)  # Slightly longer wait for Windows Docker
        else:
            raise RuntimeError(
                f"Redis failed to start on port {port} after {max_attempts} attempts",
            )


def cleanup_redis_docker() -> None:
    """Clean up Redis Docker services."""
    try:
        docker_dir: str = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        logger.info("🛑 Stopping Redis Docker services...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "down",
                "redis",
            ],
            check=False,
            capture_output=True,
        )
        logger.info("✅ Redis Docker services stopped")
    except Exception as e:
        logger.warning(f"⚠️ Error stopping Redis Docker services: {e}")


def terminate_redis_process(redis_proc: subprocess.Popen) -> None:
    """
    Gracefully terminate a Redis process.

    Args:
        redis_proc: The Redis process to terminate
    """
    if redis_proc and redis_proc.poll() is None:  # Process is still running
        logger.info("🛑 Stopping Redis process...")
        redis_proc.terminate()
        try:
            redis_proc.wait(timeout=5)
            logger.info("✅ Redis stopped gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Force killing Redis process...")
            redis_proc.kill()
            redis_proc.wait()
