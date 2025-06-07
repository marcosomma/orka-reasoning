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
Resource Registry
===============

The Resource Registry is a central dependency injection and resource management
system for the OrKa framework. It provides a consistent interface for initializing,
accessing, and managing shared resources such as language models, embedding models,
databases, and custom tools.

Key responsibilities:
-------------------
1. Lazy initialization of resources based on configuration
2. Centralized access to shared dependencies
3. Resource lifecycle management (initialization and cleanup)
4. Consistent error handling for resource failures
5. Support for custom resource types through dynamic imports

Supported resource types:
-----------------------
- sentence_transformer: Text embedding models
- redis: Redis database client
- openai: OpenAI API client
- custom: Dynamically loaded custom resources

The registry pattern helps maintain clean separation of concerns by isolating
resource initialization logic and providing a single source of truth for shared
dependencies across the framework.
"""

import importlib
import logging
from typing import Any, Dict

import redis.asyncio as redis
from openai import AsyncOpenAI

from .contracts import ResourceConfig

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False
    logger.warning(
        "sentence_transformers not available. Install with: pip install sentence-transformers"
    )


class ResourceRegistry:
    """
    Manages resource initialization, access, and lifecycle.

    The ResourceRegistry is responsible for lazily initializing resources when needed,
    providing access to them via a simple interface, and ensuring proper cleanup
    when the application shuts down. It acts as a central dependency provider
    for all OrKa components.
    """

    def __init__(self, config: Dict[str, ResourceConfig]):
        """
        Initialize the registry with resource configurations.

        Args:
            config: Dictionary mapping resource names to their configurations
        """
        self._resources: Dict[str, Any] = {}
        self._config = config
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize all resources based on their configurations.

        This method lazily initializes all configured resources, handling any
        initialization errors and ensuring resources are only initialized once.

        Raises:
            Exception: If any resource fails to initialize
        """
        if self._initialized:
            return

        for name, resource_config in self._config.items():
            try:
                resource = await self._init_resource(resource_config)
                self._resources[name] = resource
            except Exception as e:
                logger.error(f"Failed to initialize resource {name}: {e}")
                raise

        self._initialized = True

    async def _init_resource(self, config: ResourceConfig) -> Any:
        """
        Initialize a single resource based on its type and configuration.

        Args:
            config: Resource configuration containing type and parameters

        Returns:
            Initialized resource instance

        Raises:
            ValueError: If the resource type is unknown
            Exception: If resource initialization fails
        """
        resource_type = config["type"]
        resource_config = config["config"]

        if resource_type == "sentence_transformer":
            if not HAS_SENTENCE_TRANSFORMERS:
                raise ImportError(
                    "sentence_transformers is required for sentence_transformer resource. Install with: pip install sentence-transformers"
                )
            return SentenceTransformer(resource_config["model_name"])

        elif resource_type == "redis":
            return redis.from_url(resource_config["url"])

        elif resource_type == "openai":
            return AsyncOpenAI(api_key=resource_config["api_key"])

        elif resource_type == "custom":
            module_path = resource_config["module"]
            class_name = resource_config["class"]
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls(**resource_config.get("init_args", {}))

        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

    def get(self, name: str) -> Any:
        """
        Get a resource by name.

        Args:
            name: Name of the resource to retrieve

        Returns:
            The requested resource instance

        Raises:
            RuntimeError: If the registry has not been initialized
            KeyError: If the requested resource does not exist
        """
        if not self._initialized:
            raise RuntimeError("Registry not initialized")
        if name not in self._resources:
            raise KeyError(f"Resource not found: {name}")
        return self._resources[name]

    async def close(self) -> None:
        """
        Clean up and close all resources.

        This method ensures proper cleanup of all resources when the application
        is shutting down, closing connections and releasing system resources.
        """
        for name, resource in self._resources.items():
            try:
                if hasattr(resource, "close"):
                    await resource.close()
                elif hasattr(resource, "__aexit__"):
                    await resource.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing resource {name}: {e}")


def init_registry(config: Dict[str, ResourceConfig]) -> ResourceRegistry:
    """
    Create and initialize a new resource registry.

    Args:
        config: Dictionary mapping resource names to their configurations

    Returns:
        Initialized ResourceRegistry instance
    """
    registry = ResourceRegistry(config)
    return registry
