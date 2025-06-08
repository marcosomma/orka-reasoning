import logging
from typing import Any, Dict, List, Optional

from ..contracts import Context, Registry
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class RAGNode(BaseNode):
    """
    A node that performs Retrieval-Augmented Generation (RAG) operations.
    """

    def __init__(
        self,
        node_id: str,
        registry: Registry,
        prompt: str = "",
        queue: str = "default",
        timeout: Optional[float] = 30.0,
        max_concurrency: int = 10,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ):
        super().__init__(
            node_id=node_id,
            prompt=prompt,
            queue=queue,
            timeout=timeout,
            max_concurrency=max_concurrency,
        )
        self.registry = registry
        self.top_k = top_k
        self.score_threshold = score_threshold
        self._memory = None
        self._embedder = None
        self._llm = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the node and its resources."""
        self._memory = self.registry.get("memory")
        self._embedder = self.registry.get("embedder")
        self._llm = self.registry.get("llm")
        self._initialized = True

    async def run(self, context: Context) -> Dict[str, Any]:
        """Run the RAG node with the given context."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self._run_impl(context)
            return {
                "result": result,
                "status": "success",
                "error": None,
                "metadata": {"node_id": self.node_id},
            }
        except Exception as e:
            logger.error(f"RAGNode {self.node_id} failed: {e!s}")
            return {
                "result": None,
                "status": "error",
                "error": str(e),
                "metadata": {"node_id": self.node_id},
            }

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """Implementation of RAG operations."""
        query = ctx.get("query")
        if not query:
            raise ValueError("Query is required for RAG operation")

        # Get embedding for the query
        query_embedding = await self._get_embedding(query)

        # Search memory for relevant documents
        results = await self._memory.search(
            query_embedding,
            limit=self.top_k,
            score_threshold=self.score_threshold,
        )

        if not results:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "sources": [],
            }

        # Format context from results
        context = self._format_context(results)

        # Generate answer using LLM
        answer = await self._generate_answer(query, context)

        return {"answer": answer, "sources": results}

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using the embedder."""
        return await self._embedder.encode(text)

    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into context for the LLM."""
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"Source {i}:\n{result['content']}\n")
        return "\n".join(context_parts)

    async def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using the LLM."""
        prompt = f"""Based on the following context, answer the question. If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {query}

Answer:"""

        response = await self._llm.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions based on the provided context.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content
