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
OrKa UI Container Management
============================

This module handles the Docker container lifecycle for the OrKa UI.
"""

import logging
import os
import subprocess
import time

logger = logging.getLogger(__name__)


def is_ui_container_running() -> bool:
    """
    Check if the orka-ui container is already running.

    Returns:
        bool: True if the container is running, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=orka-ui", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "orka-ui" in result.stdout
    except Exception as e:
        logger.warning(f"Could not check UI container status: {e}")
        return False


def stop_ui_container() -> None:
    """
    Stop and remove the orka-ui container if it exists.
    """
    try:
        # Stop the container
        subprocess.run(
            ["docker", "stop", "orka-ui"],
            capture_output=True,
            check=False,
        )
        # Remove the container
        subprocess.run(
            ["docker", "rm", "orka-ui"],
            capture_output=True,
            check=False,
        )
        logger.info("🗑️  Stopped and removed existing orka-ui container")
    except Exception as e:
        logger.warning(f"Could not stop UI container: {e}")


def start_ui_container(api_url: str = "http://localhost:8000") -> bool:
    """
    Start the OrKa UI Docker container.

    Args:
        api_url: The API URL for the OrKa backend (default: http://localhost:8000)

    Returns:
        bool: True if the container started successfully, False otherwise
    """
    # Check if container is already running
    if is_ui_container_running():
        logger.info("✅ OrKa UI container is already running")
        return True

    # Stop any existing container
    stop_ui_container()

    # Get the API URL from environment or use default
    api_url = os.getenv("ORKA_API_URL", api_url)

    logger.info("🚀 Starting OrKa UI container...")
    logger.info(f"   • API URL: {api_url}")
    logger.info(f"   • UI Port: 8080")

    try:
        # Pull the latest image (optional - controlled by environment variable)
        skip_pull = os.getenv("ORKA_UI_SKIP_PULL", "").lower() in ("true", "1", "yes")
        
        if not skip_pull:
            logger.info("📥 Pulling latest orka-ui image...")
            pull_result = subprocess.run(
                ["docker", "pull", "marcosomma/orka-ui:latest"],
                capture_output=True,
                text=True,
                check=False,
            )

            if pull_result.returncode != 0:
                logger.warning("⚠️  Could not pull latest image, using cached version")
        else:
            logger.info("⏭️  Skipping image pull (using cached version)")

        # Run the container
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            "orka-ui",
            "-p",
            "8080:80",
            "-e",
            f"VITE_API_URL_LOCAL={api_url}/api/run@dist",
            "marcosomma/orka-ui:latest",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        # Wait for container to be ready
        time.sleep(2)

        # Verify container is running
        if is_ui_container_running():
            logger.info("✅ OrKa UI container started successfully")
            logger.info(f"   • Access UI at: http://localhost:8080")
            return True
        else:
            logger.error("❌ UI container failed to start")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to start UI container: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(
            "❌ Docker not found. Please install Docker to use the OrKa UI.\n"
            "   Download from: https://www.docker.com/products/docker-desktop"
        )
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error starting UI container: {e}")
        return False


def cleanup_ui_container() -> None:
    """
    Clean up the OrKa UI container on shutdown.
    """
    logger.info("🧹 Cleaning up OrKa UI container...")
    try:
        stop_ui_container()
    except Exception as e:
        logger.warning(f"⚠️  Error during UI container cleanup: {e}")
