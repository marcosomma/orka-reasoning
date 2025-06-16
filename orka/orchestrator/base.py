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
Base Orchestrator
================

Core orchestrator class with initialization and configuration management.
"""

import os
from uuid import uuid4

from ..fork_group_manager import ForkGroupManager, SimpleForkGroupManager
from ..loader import YAMLLoader
from ..memory_logger import create_memory_logger


class OrchestratorBase:
    """
    Base orchestrator class that handles initialization and configuration.
    """

    def __init__(self, config_path):
        """
        Initialize the Orchestrator with a YAML config file.
        Loads orchestrator and agent configs, sets up memory and fork management.
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

        if memory_backend == "kafka":
            self.memory = create_memory_logger(
                backend="kafka",
                bootstrap_servers=os.getenv(
                    "KAFKA_BOOTSTRAP_SERVERS",
                    "localhost:9092",
                ),
                topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "orka-memory"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
            )
            # For Kafka, we'll use a simple in-memory fork manager since Kafka doesn't have Redis-like operations
            self.fork_manager = SimpleForkGroupManager()
        else:
            self.memory = create_memory_logger(
                backend="redis",
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
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
