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
Base Orchestrator Module
========================

This module contains the core orchestrator base class that handles initialization,
configuration management, and setup of core infrastructure components including
memory backends, fork management, and error tracking.

The :class:`OrchestratorBase` class serves as the foundation for the main
:class:`~orka.orchestrator.Orchestrator` class through multiple inheritance composition.

Core Responsibilities
--------------------

**Configuration Management**
    * Loads and validates YAML configuration files
    * Extracts orchestrator and agent configurations
    * Handles environment variable overrides

**Infrastructure Setup**
    * Initializes memory backend (Redis or Kafka)
    * Configures fork group management for parallel execution
    * Sets up error tracking and telemetry systems

**Runtime State Management**
    * Maintains execution queue and step counters
    * Generates unique run identifiers for traceability
    * Tracks overall execution status and metrics
"""

import logging
import os
from typing import Any, Dict
from uuid import uuid4

from ..fork_group_manager import ForkGroupManager, SimpleForkGroupManager
from ..loader import YAMLLoader
from ..memory_logger import create_memory_logger

logger = logging.getLogger(__name__)


class OrchestratorBase:
    """
    Base orchestrator class that handles initialization and configuration.

    This class provides the foundational infrastructure for the OrKa orchestration
    framework, including configuration loading, memory backend setup, and core
    state management. It is designed to be composed with other specialized classes
    through multiple inheritance.

    The class automatically configures the appropriate backend based on environment
    variables and provides comprehensive error tracking capabilities for monitoring
    and debugging orchestration runs.

    Attributes:
        loader (:class:`~orka.loader.YAMLLoader`): Configuration file loader and validator
        orchestrator_cfg (dict): Orchestrator-specific configuration settings
        agent_cfgs (list): List of agent configuration objects
        memory: Memory backend instance (Redis or Kafka)
        fork_manager: Fork group manager for parallel execution
        queue (list): Current agent execution queue
        run_id (str): Unique identifier for this orchestration run
        step_index (int): Current step counter for traceability
        error_telemetry (dict): Comprehensive error tracking and metrics
    """

    def __init__(self, config_path):
        """
        Initialize the Orchestrator with a YAML config file.

        Sets up all core infrastructure including configuration loading,
        memory backend selection, fork management, and error tracking systems.

        Args:
            config_path (str): Path to the YAML configuration file

        Environment Variables:
            ORKA_MEMORY_BACKEND: Memory backend type ('redis' or 'kafka', default: 'redis')
            ORKA_DEBUG_KEEP_PREVIOUS_OUTPUTS: Keep previous outputs for debugging ('true'/'false')
            KAFKA_BOOTSTRAP_SERVERS: Kafka broker addresses (for Kafka backend)
            KAFKA_TOPIC_PREFIX: Topic prefix for Kafka topics (default: 'orka-memory')
            REDIS_URL: Redis connection URL (default: 'redis://localhost:6379/0')
        """
        self.loader = YAMLLoader(config_path)
        self.loader.validate()

        self.orchestrator_cfg = self.loader.get_orchestrator()
        self.agent_cfgs = self.loader.get_agents()

        # Configure memory backend
        memory_backend = os.getenv("ORKA_MEMORY_BACKEND", "redis").lower()

        # Get debug flag from orchestrator config or environment
        debug_keep_previous_outputs = self.orchestrator_cfg.get("debug", {}).get(
            "keep_previous_outputs",
            False,
        )
        debug_keep_previous_outputs = (
            debug_keep_previous_outputs
            or os.getenv("ORKA_DEBUG_KEEP_PREVIOUS_OUTPUTS", "false").lower() == "true"
        )

        # Extract decay configuration from orchestrator config and environment
        decay_config = self._init_decay_config()

        if memory_backend == "kafka":
            self.memory = create_memory_logger(
                backend="kafka",
                bootstrap_servers=os.getenv(
                    "KAFKA_BOOTSTRAP_SERVERS",
                    "localhost:9092",
                ),
                topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "orka-memory"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
            )
            # For Kafka, we'll use a simple in-memory fork manager since Kafka doesn't have Redis-like operations
            self.fork_manager = SimpleForkGroupManager()
        else:
            self.memory = create_memory_logger(
                backend="redis",
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
            )
            # For Redis, use the existing Redis-based fork manager
            self.fork_manager = ForkGroupManager(self.memory.redis)

        self.queue = self.orchestrator_cfg["agents"][:]  # Initial agent execution queue
        self.run_id = str(uuid4())  # Unique run/session ID
        self.step_index = 0  # Step counter for traceability

        # Error tracking and telemetry
        self.error_telemetry = {
            "errors": [],  # List of all errors encountered
            "retry_counters": {},  # Per-agent retry counts
            "partial_successes": [],  # Agents that succeeded after retries
            "silent_degradations": [],  # JSON parsing failures that fell back to raw text
            "status_codes": {},  # HTTP status codes for API calls
            "execution_status": "running",  # overall status: running, completed, failed, partial
            "critical_failures": [],  # Failures that stopped execution
            "recovery_actions": [],  # Actions taken to recover from errors
        }

    def enqueue_fork(self, agent_ids, fork_group_id):
        """
        Enqueue a fork group for parallel execution.
        """
        # This method will be implemented in the execution engine

    def _init_decay_config(self) -> Dict[str, Any]:
        """
        Initialize decay configuration from orchestrator config and environment variables.

        Returns:
            Processed decay configuration with defaults applied
        """
        # Start with default configuration
        decay_config = {
            "enabled": False,  # Opt-in by default for backward compatibility
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
        }

        # Extract from orchestrator YAML config
        orchestrator_memory_config = self.orchestrator_cfg.get("memory", {})
        orchestrator_decay_config = orchestrator_memory_config.get("decay", {})

        if orchestrator_decay_config:
            # Merge orchestrator-level decay config
            decay_config.update(orchestrator_decay_config)

        # Override with environment variables if present
        env_enabled = os.getenv("ORKA_MEMORY_DECAY_ENABLED")
        if env_enabled is not None:
            decay_config["enabled"] = env_enabled.lower() == "true"

        env_short_term = os.getenv("ORKA_MEMORY_DECAY_SHORT_TERM_HOURS")
        if env_short_term is not None:
            try:
                decay_config["default_short_term_hours"] = float(env_short_term)
            except ValueError:
                logger.warning(
                    f"Invalid ORKA_MEMORY_DECAY_SHORT_TERM_HOURS value: {env_short_term}",
                )

        env_long_term = os.getenv("ORKA_MEMORY_DECAY_LONG_TERM_HOURS")
        if env_long_term is not None:
            try:
                decay_config["default_long_term_hours"] = float(env_long_term)
            except ValueError:
                logger.warning(f"Invalid ORKA_MEMORY_DECAY_LONG_TERM_HOURS value: {env_long_term}")

        env_interval = os.getenv("ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES")
        if env_interval is not None:
            try:
                decay_config["check_interval_minutes"] = int(env_interval)
            except ValueError:
                logger.warning(
                    f"Invalid ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES value: {env_interval}",
                )

        # Log decay configuration if enabled
        if decay_config.get("enabled", False):
            logger.info(
                f"Memory decay enabled: short_term={decay_config['default_short_term_hours']}h, "
                f"long_term={decay_config['default_long_term_hours']}h, "
                f"check_interval={decay_config['check_interval_minutes']}min",
            )
        else:
            logger.debug("Memory decay disabled")

        return decay_config
