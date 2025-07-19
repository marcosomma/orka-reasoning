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

"""Base orchestrator module for OrKa."""

import logging
import os
from typing import Any, cast
from uuid import uuid4

from ..fork_group_manager import ForkGroupManager
from ..loader import ConfigLoader
from ..memory_logger import create_memory_logger, BaseMemoryLogger

logger = logging.getLogger(__name__)


class BaseOrchestrator:
    """Base class for orchestrators."""

    def __init__(self, config_path: str) -> None:
        """Set up the base orchestrator."""
        self.config_path = config_path
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load()
        self.orchestrator_config = self.config_loader.get_orchestrator()
        self.agent_cfgs = self.config_loader.get_agents()

        # Memory backend configuration with RedisStack as default
        memory_backend = os.getenv("ORKA_MEMORY_BACKEND", "redisstack").lower()

        # Get debug flag from orchestrator config or environment
        debug_keep_previous_outputs = self.orchestrator_config.get("debug", {}).get(
            "keep_previous_outputs",
            False,
        )

        # Get memory configuration from YAML
        memory_config = self.orchestrator_config.get("memory", {}).get("config", {})

        if memory_backend == "kafka":
            # Kafka configuration
            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
            schema_registry_url = os.getenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
            self.memory = cast(
                BaseMemoryLogger,
                create_memory_logger(
                    "kafka",
                    bootstrap_servers=bootstrap_servers,
                    schema_registry_url=schema_registry_url,
                    debug_keep_previous_outputs=debug_keep_previous_outputs,
                    memory_config=memory_config,
                ),
            )
        else:
            # Redis configuration
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
            self.memory = cast(
                BaseMemoryLogger,
                create_memory_logger(
                    "redisstack",
                    redis_url=redis_url,
                    debug_keep_previous_outputs=debug_keep_previous_outputs,
                    memory_config=memory_config,
                ),
            )

        # Initialize fork manager if Redis is available
        self.fork_manager = None
        try:
            redis = self.memory.redis  # type: ignore
            if redis is not None:
                self.fork_manager = ForkGroupManager(redis)
        except AttributeError:
            pass

        self.queue = self.orchestrator_config["agents"][:]  # Initial agent execution queue
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

    def _init_decay_config(self) -> dict[str, Any]:
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
        orchestrator_memory_config = self.orchestrator_config.get("memory", {})
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
