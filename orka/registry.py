import importlib
import logging
from typing import Any, Dict

import redis.asyncio as redis
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from .contracts import ResourceConfig

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """Manages resource initialization and access."""

    def __init__(self, config: Dict[str, ResourceConfig]):
        self._resources: Dict[str, Any] = {}
        self._config = config
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all resources based on config."""
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
        """Initialize a single resource based on its type."""
        resource_type = config["type"]
        resource_config = config["config"]

        if resource_type == "sentence_transformer":
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
        """Get a resource by name."""
        if not self._initialized:
            raise RuntimeError("Registry not initialized")
        if name not in self._resources:
            raise KeyError(f"Resource not found: {name}")
        return self._resources[name]

    async def close(self) -> None:
        """Clean up resources."""
        for name, resource in self._resources.items():
            try:
                if hasattr(resource, "close"):
                    await resource.close()
                elif hasattr(resource, "__aexit__"):
                    await resource.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing resource {name}: {e}")


def init_registry(config: Dict[str, ResourceConfig]) -> ResourceRegistry:
    """Create and initialize a new resource registry."""
    registry = ResourceRegistry(config)
    return registry
