import json
from typing import Any, Dict

import redis.asyncio as redis

from ..utils.bootstrap_memory_index import retry
from .agent_node import BaseNode


class MemoryReaderNode(BaseNode):
    """Node for reading from memory stream."""

    def __init__(self, node_id: str, prompt: str = None, queue: list = None, **kwargs):
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.limit = kwargs.get("limit", 100)
        self.redis = redis.from_url("redis://localhost:6379", decode_responses=False)

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Read latest memories from stream."""
        session_id = context.get("session_id", "default")
        stream_key = f"orka:memory:{session_id}"

        # Get latest entries with retry
        entries = await retry(self.redis.xrange(stream_key))
        if entries:
            # Get last N entries, but in chronological order
            entries = entries[-self.limit :]

        memories = []
        for entry_id, data in entries:
            try:
                # Handle both string and bytes payload
                payload_str = (
                    data.get(b"payload", b"{}").decode()
                    if isinstance(data.get(b"payload"), bytes)
                    else data.get("payload", "{}")
                )
                payload = json.loads(payload_str)
                memories.append(
                    {
                        "id": entry_id.decode()
                        if isinstance(entry_id, bytes)
                        else entry_id,
                        "content": payload["content"],
                        "metadata": payload.get("metadata", {}),
                        "ts": int(data.get(b"ts", 0))
                        if isinstance(data.get(b"ts"), bytes)
                        else int(data.get("ts", 0)),
                    }
                )
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                print(f"Error processing memory entry: {e}")
                continue

        # Store result in context
        context.setdefault("outputs", {})[self.node_id] = {
            "status": "success",
            "memories": memories,
        }

        return context["outputs"][self.node_id]
