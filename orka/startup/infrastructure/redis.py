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
Redis Infrastructure Management
==============================

This module handles Redis Stack management including native startup and Docker fallback.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from ..config import get_docker_dir


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
        print("🔍 Checking Redis Stack availability...")
        result = subprocess.run(
            ["redis-stack-server", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print(f"🔧 Starting Redis Stack natively on port {port}...")

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

            print(f"✅ Redis Stack running natively on port {port}")
            return redis_proc
        else:
            raise FileNotFoundError("Redis Stack not found in PATH")

    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Redis Stack not found natively.")
        print("🐳 Falling back to Docker Redis Stack...")

        try:
            # Use Docker fallback
            return start_redis_docker(port)

        except Exception as docker_error:
            print(f"❌ Docker fallback also failed: {docker_error}")
            print("📦 To fix this, install Redis Stack:")
            print("   • Windows: Download from https://redis.io/download")
            print("   • macOS: brew install redis-stack")
            print("   • Ubuntu: sudo apt install redis-stack-server")
            print("   • Or ensure Docker is available for fallback")
            raise RuntimeError("Both native and Docker Redis Stack unavailable")

    except Exception as e:
        print(f"❌ Failed to start native Redis: {e}")
        raise RuntimeError(f"Redis startup failed: {e}")


def start_redis_docker(port: int = 6379) -> Optional[subprocess.Popen]:
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

        print(f"🔧 Starting Redis Stack via Docker on port {port}...")

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

        print(f"✅ Redis Stack running via Docker on port {port}")
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
    print(f"⏳ Waiting for Redis to be ready on port {port}...")

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
                    print(f"✅ Redis is ready on port {port}!")
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass  # redis-cli not available, try alternative

            # Fallback to socket + Redis library check
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            socket_result = sock.connect_ex(("localhost", port))
            sock.close()

            if socket_result == 0:  # Changed from result to socket_result
                # Additional check with Redis ping
                try:
                    import redis

                    client = redis.Redis(host="localhost", port=port, decode_responses=True)
                    if client.ping():
                        print(f"✅ Redis is ready on port {port}!")
                        return
                except Exception:
                    pass  # Continue trying

        except Exception:
            pass

        if attempt < max_attempts - 1:
            print(f"Redis not ready yet, waiting... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(2)
        else:
            raise RuntimeError(
                f"Redis failed to start on port {port} after {max_attempts} attempts",
            )


def cleanup_redis_docker() -> None:
    """Clean up Redis Docker services."""
    try:
        docker_dir: str = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        print("🛑 Stopping Redis Docker services...")
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
        print("✅ Redis Docker services stopped")
    except Exception as e:
        print(f"⚠️ Error stopping Redis Docker services: {e}")


def terminate_redis_process(redis_proc: subprocess.Popen) -> None:
    """
    Gracefully terminate a Redis process.

    Args:
        redis_proc: The Redis process to terminate
    """
    if redis_proc and redis_proc.poll() is None:  # Process is still running
        print("🛑 Stopping Redis process...")
        redis_proc.terminate()
        try:
            redis_proc.wait(timeout=5)
            print("✅ Redis stopped gracefully")
        except subprocess.TimeoutExpired:
            print("⚠️ Force killing Redis process...")
            redis_proc.kill()
            redis_proc.wait()
