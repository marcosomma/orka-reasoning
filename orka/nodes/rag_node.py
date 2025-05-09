from typing import Dict, Any, List
import redis.asyncio as redis
from .agent_node import BaseNode
from ..utils.embedder import get_embedder, to_bytes
from ..utils.bootstrap_memory_index import retry

class RAGNode(BaseNode):
    """Node for vector similarity search."""

    def __init__(self, node_id: str, prompt: str = None, queue: list = None, **kwargs):
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.top_k = kwargs.get("top_k", 5)
        self.score_threshold = kwargs.get("score_threshold", 0.75)
        self.embedder = get_embedder()
        self.redis = redis.from_url("redis://localhost:6379", decode_responses=False)

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform vector similarity search."""
        query = context.get("input", "")
        session_id = context.get("session_id", "default")
        
        if not query:
            context.setdefault("outputs", {})[self.node_id] = {
                "status": "success",
                "hits": []
            }
            return context["outputs"][self.node_id]
        
        # Generate query embedding
        query_vec = self.embedder.encode(query)
        q_vec = to_bytes(query_vec)
        
        # Search with retry
        res = await retry(self.redis.ft("memory_idx").search(
            f"*=>[KNN {self.top_k} @vector $V RETURN 3 content ts score]",
            query_params={"V": q_vec},
            dialect=2  # needed for KNN
        ))
        
        # Filter results by score threshold
        hits = [
            {
                "content": doc.content,
                "score": float(doc.score),
                "ts": int(doc.ts)
            }
            for doc in res.docs
            if float(doc.score) < self.score_threshold
        ]

        # Store result in context
        context.setdefault("outputs", {})[self.node_id] = {
            "status": "success",
            "hits": hits
        }
        
        return context["outputs"][self.node_id] 