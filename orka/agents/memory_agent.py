import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..contracts import Context, MemoryEntry, Registry
from ..memory.compressor import MemoryCompressor
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """Agent for managing memory operations."""

    def __init__(
        self,
        agent_id: str,
        registry: Registry,
        timeout: Optional[float] = 30.0,
        max_concurrency: int = 10,
        max_entries: int = 1000,
        importance_threshold: float = 0.3,
    ):
        super().__init__(agent_id, registry, timeout, max_concurrency)
        self.compressor = MemoryCompressor(
            max_entries=max_entries, importance_threshold=importance_threshold
        )
        self._memory = None
        self._embedder = None

    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        await super().initialize()
        self._memory = self.registry.get("memory")
        self._embedder = self.registry.get("embedder")

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """Implementation of memory operations."""
        operation = ctx.get("operation", "read")

        if operation == "write":
            return await self._write_memory(ctx)
        elif operation == "read":
            return await self._read_memory(ctx)
        elif operation == "compress":
            return await self._compress_memory(ctx)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _write_memory(self, ctx: Context) -> Dict[str, Any]:
        """Write to memory."""
        content = ctx.get("content")
        if not content:
            raise ValueError("Content is required for write operation")

        entry = MemoryEntry(
            content=content,
            importance=ctx.get("importance", 0.5),
            timestamp=datetime.now(),
            metadata=ctx.get("metadata", {}),
            is_summary=False,
        )

        # Get embedding for the content
        embedding = await self._get_embedding(content)

        # Write to memory
        await self._memory.write(entry, embedding)

        return {"status": "written", "entry": entry}

    async def _read_memory(self, ctx: Context) -> Dict[str, Any]:
        """Read from memory."""
        query = ctx.get("query")
        if not query:
            raise ValueError("Query is required for read operation")

        # Get embedding for the query
        query_embedding = await self._get_embedding(query)

        # Search memory
        results = await self._memory.search(query_embedding, limit=ctx.get("limit", 10))

        return {"results": results}

    async def _compress_memory(self, ctx: Context) -> Dict[str, Any]:
        """Compress memory entries."""
        entries = await self._memory.get_all()

        if self.compressor.should_compress(entries):
            compressed = await self.compressor.compress(
                entries, self.registry.get("llm")
            )
            await self._memory.replace_all(compressed)
            return {"status": "compressed", "entries": compressed}

        return {"status": "no_compression_needed", "entries": entries}

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using the embedder."""
        return await self._embedder.encode(text)
