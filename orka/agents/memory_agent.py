import json
import time
from typing import Any, Dict, List

from sentence_transformers import SentenceTransformer

from .agent_base import BaseAgent
from .utils.redis_client import get_redis_client


class MemoryAgent(BaseAgent):
    """Stateful read/write memory node that supports both stream and vector storage."""

    def __init__(self, config: Dict[str, Any]):
        agent_id = config.get("id", "memory_agent")
        prompt = config.get("prompt", "")
        queue = config.get("queue", [])
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue)
        self.mode = config.get("mode", "hybrid")
        self.memory_scope = config.get("memory_scope", "session")
        self.vector_enabled = config.get("vector", False)
        self.embedding_model = None
        if self.vector_enabled:
            model_name = config.get(
                "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
            )
            self.embedding_model = SentenceTransformer(model_name)
        self.redis = get_redis_client()

    def _get_stream_key(self, session_id: str) -> str:
        """Get the Redis stream key for the given scope and session."""
        return f"orka:memory:{self.memory_scope}:{session_id}"

    def _append_stream(self, text: str, context: Dict[str, Any]) -> str:
        """Append a memory entry to the Redis stream."""
        session_id = context.get("session_id", "default")
        stream_key = self._get_stream_key(session_id)

        entry = {
            "ts": int(time.time()),
            "agent_id": self.agent_id,
            "type": "memory.append",
            "session": session_id,
            "payload": json.dumps(
                {"content": text, "metadata": context.get("metadata", {})}
            ),
        }

        # Add to both scoped and global streams
        memory_id = self.redis.xadd("orka:memory", entry)
        self.redis.xadd(stream_key, entry)
        return memory_id

    def _upsert_vector(self, text: str, context: Dict[str, Any]) -> None:
        """Store vector embedding in Redis Search."""
        if not self.embedding_model:
            return

        # Generate embedding
        vector = self.embedding_model.encode(text)

        # Store in Redis Search
        doc_id = f"mem_{int(time.time())}"
        self.redis.ft("memory_idx").add_document(
            doc_id,
            content=text,
            vector=vector.tobytes(),
            session=context.get("session_id", "default"),
            agent=self.agent_id,
            ts=int(time.time()),
        )

    def _query_vector(
        self, text: str, k: int = 5, score_threshold: float = 0.25
    ) -> List[Dict[str, Any]]:
        """Query vector store for similar memories."""
        if not self.embedding_model:
            return []

        # Generate query embedding
        query_vector = self.embedding_model.encode(text)

        # Search in Redis
        results = self.redis.ft("memory_idx").search(
            f"*=>[KNN {k} @vector $BLOB AS score]",
            query_params={"BLOB": query_vector.tobytes()},
            sort_by="score",
            sort_asc=False,
        )

        # Filter and format results
        hits = []
        for doc in results.docs:
            if doc.score > score_threshold:
                hits.append(
                    {
                        "id": doc.id,
                        "content": doc.content,
                        "score": doc.score,
                        "metadata": {
                            "session": doc.session,
                            "agent": doc.agent,
                            "ts": doc.ts,
                        },
                    }
                )
        return hits

    def _get_episodic(self, session_id: str, k: int = 100) -> List[Dict[str, Any]]:
        """Get latest k episodic memories from stream."""
        stream_key = self._get_stream_key(session_id)
        entries = self.redis.xrange(stream_key, count=k)

        memories = []
        for entry_id, data in entries:
            try:
                payload = json.loads(data[b"payload"])
                memories.append(
                    {
                        "id": entry_id.decode(),
                        "content": payload["content"],
                        "metadata": payload.get("metadata", {}),
                        "ts": int(data[b"ts"]),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return memories

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run the memory agent in the specified mode."""
        text = context.get("input", "")
        session_id = context.get("session_id", "default")

        result = {"episodic": [], "semantic": []}

        # Write operations
        if self.mode in ("write", "hybrid"):
            self._append_stream(text, context)
            if self.vector_enabled:
                self._upsert_vector(text, context)

        # Read operations
        if self.mode in ("read", "hybrid"):
            result["episodic"] = self._get_episodic(session_id)
            if self.vector_enabled:
                result["semantic"] = self._query_vector(text)

        return result
