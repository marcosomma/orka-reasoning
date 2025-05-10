import json
import time
from typing import Any, Dict

import redis.asyncio as redis

from ..utils.bootstrap_memory_index import retry
from ..utils.embedder import get_embedder, to_bytes
from .base_node import BaseNode


class MemoryWriterNode(BaseNode):
    """Node for writing to memory stream and optionally vector store."""

    def __init__(self, node_id: str, prompt: str = None, queue: list = None, **kwargs):
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.vector_enabled = kwargs.get("vector", False)
        self.embedder = (
            get_embedder(kwargs.get("embedding_model")) if self.vector_enabled else None
        )
        self.redis = redis.from_url("redis://localhost:6379", decode_responses=False)

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Write to memory stream and optionally vector store."""
        text = context.get("input", "")
        session_id = context.get("session_id", "default")

        # Prepare stream entry
        entry = {
            "ts": str(time.time_ns()),
            "agent_id": self.node_id,
            "type": "memory.append",
            "session": session_id,
            "payload": json.dumps(
                {"content": text, "metadata": context.get("metadata", {})}
            ),
        }

        # Write to stream with retry
        stream_key = f"orka:memory:{session_id}"
        await retry(self.redis.xadd(stream_key, entry))

        # Optionally write to vector store
        if self.vector_enabled and self.embedder:
            vector = self.embedder.encode(text)
            doc_id = f"mem:{time.time_ns()}"
            # Use individual hset calls for compatibility with fakeredis
            await retry(self.redis.hset(doc_id, "content", text))
            await retry(self.redis.hset(doc_id, "vector", to_bytes(vector)))
            await retry(self.redis.hset(doc_id, "session", session_id))
            await retry(self.redis.hset(doc_id, "agent", self.node_id))
            await retry(self.redis.hset(doc_id, "ts", str(int(time.time() * 1e3))))

        # Store result in context
        context.setdefault("outputs", {})[self.node_id] = {
            "status": "success",
            "session": session_id,
        }

        return context["outputs"][self.node_id]
