import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..contracts import Context, MemoryEntry, Registry
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryWriter(BaseNode):
    """Node for writing to memory."""

    def __init__(
        self,
        node_id: str,
        registry: Registry,
        timeout: Optional[float] = 30.0,
        max_concurrency: int = 10,
    ):
        super().__init__(node_id, registry, timeout, max_concurrency)
        self._memory = None
        self._embedder = None

    async def initialize(self) -> None:
        """Initialize the node and its resources."""
        await super().initialize()
        self._memory = self.registry.get("memory")
        self._embedder = self.registry.get("embedder")

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """Implementation of memory writing."""
        content = ctx.get("content")
        if not content:
            raise ValueError("Content is required for memory writing")

        # Create memory entry
        entry = MemoryEntry(
            content=content,
            importance=ctx.get("importance", 0.5),
            timestamp=datetime.now(),
            metadata=ctx.get("metadata", {}),
            is_summary=False,
        )

        # Get embedding for the content
        embedding = await self._embedder.encode(content)

        # Write to memory
        await self._memory.write(entry, embedding)

        return {"status": "success", "entry": entry}
