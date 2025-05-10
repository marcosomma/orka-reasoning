import logging
from typing import Any, Dict, Optional

from ..contracts import Context, Registry
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryReader(BaseNode):
    """Node for reading from memory."""

    def __init__(
        self,
        node_id: str,
        registry: Registry,
        timeout: Optional[float] = 30.0,
        max_concurrency: int = 10,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ):
        super().__init__(node_id, registry, timeout, max_concurrency)
        self.top_k = top_k
        self.score_threshold = score_threshold
        self._memory = None
        self._embedder = None

    async def initialize(self) -> None:
        """Initialize the node and its resources."""
        await super().initialize()
        self._memory = self.registry.get("memory")
        self._embedder = self.registry.get("embedder")

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """Implementation of memory reading."""
        query = ctx.get("query")
        if not query:
            raise ValueError("Query is required for memory reading")

        # Get embedding for the query
        query_embedding = await self._embedder.encode(query)

        # Search memory
        results = await self._memory.search(
            query_embedding, limit=self.top_k, score_threshold=self.score_threshold
        )

        return {"status": "success", "results": results}
