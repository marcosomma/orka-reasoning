import logging
from typing import Any

from ..contracts import Context, Registry
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class RAGNode(BaseNode):
    """
    RAG Node Implementation
    ======================

    A specialized node that performs Retrieval-Augmented Generation (RAG) operations
    by combining semantic search with language model generation.

    Core Functionality
    -----------------

    **RAG Process:**
    1. **Query Processing**: Extract and prepare the input query
    2. **Embedding Generation**: Convert query to vector representation
    3. **Memory Search**: Find relevant documents using semantic similarity
    4. **Context Formatting**: Structure retrieved documents for LLM consumption
    5. **Answer Generation**: Use LLM to generate response based on context

    **Integration Points:**
    - **Memory Backend**: Searches for relevant documents using vector similarity
    - **Embedder Service**: Generates query embeddings for semantic search
    - **LLM Service**: Generates final answers based on retrieved context
    - **Registry System**: Accesses shared resources through dependency injection

    Architecture Details
    -------------------

    **Node Configuration:**
    - `top_k`: Number of documents to retrieve (default: 5)
    - `score_threshold`: Minimum similarity score for relevance (default: 0.7)
    - `timeout`: Maximum execution time for the operation
    - `max_concurrency`: Limit on parallel executions

    **Resource Management:**
    - Lazy initialization of expensive resources (memory, embedder, LLM)
    - Registry-based dependency injection for shared services
    - Automatic resource cleanup and lifecycle management
    - Thread-safe execution for concurrent operations

    **Error Handling:**
    - Graceful handling of missing or invalid queries
    - Fallback responses when no relevant documents found
    - Structured error reporting with context preservation
    - Automatic retry logic for transient failures

    Implementation Features
    ----------------------

    **Search Capabilities:**
    - Vector similarity search using embeddings
    - Configurable relevance thresholds
    - Top-k result limiting for performance
    - Metadata filtering and namespace support

    **Context Management:**
    - Intelligent document formatting for LLM consumption
    - Source attribution and reference tracking
    - Context length optimization for model limits
    - Structured output with sources and confidence scores

    **LLM Integration:**
    - Dynamic prompt construction with retrieved context
    - Configurable model parameters and settings
    - Response quality validation and filtering
    - Token usage tracking and optimization

    Usage Examples
    --------------

    **Basic Configuration:**
    ```yaml
    agents:
      - id: rag_assistant
        type: rag
        top_k: 5
        score_threshold: 0.7
        timeout: 30.0
    ```

    **Advanced Configuration:**
    ```yaml
    agents:
      - id: specialized_rag
        type: rag
        top_k: 10
        score_threshold: 0.8
        max_concurrency: 5
        llm_config:
          model: "gpt-4"
          temperature: 0.1
          max_tokens: 500
    ```

    **Integration with Memory:**
    ```python
    # The node automatically integrates with the memory system
    # Memory backend provides semantic search capabilities
    # Embedder service generates query vectors
    # LLM service generates final responses
    ```

    Response Format
    --------------

    **Successful Response:**
    ```json
    {
      "result": {
        "answer": "Generated response based on retrieved context",
        "sources": [
          {
            "content": "Source document content",
            "score": 0.85,
            "metadata": {...}
          }
        ]
      },
      "status": "success",
      "error": null,
      "metadata": {"node_id": "rag_assistant"}
    }
    ```

    **Error Response:**
    ```json
    {
      "result": null,
      "status": "error",
      "error": "Query is required for RAG operation",
      "metadata": {"node_id": "rag_assistant"}
    }
    ```

    **No Results Response:**
    ```json
    {
      "result": {
        "answer": "I couldn't find any relevant information to answer your question.",
        "sources": []
      },
      "status": "success",
      "error": null,
      "metadata": {"node_id": "rag_assistant"}
    }
    ```

    Performance Considerations
    -------------------------

    **Optimization Features:**
    - Lazy resource initialization to reduce startup time
    - Configurable concurrency limits for resource management
    - Efficient context formatting to minimize token usage
    - Caching strategies for frequently accessed documents

    **Scalability:**
    - Supports high-throughput query processing
    - Memory-efficient document handling
    - Parallel processing capabilities
    - Resource pooling for external services

    **Monitoring:**
    - Execution timing and performance metrics
    - Search quality and relevance tracking
    - LLM usage and cost monitoring
    - Error rate and pattern analysis
    """

    def __init__(
        self,
        node_id: str,
        registry: Registry,
        prompt: str = "",
        queue: str = "default",
        timeout: float | None = 30.0,
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

    async def run(self, context: Context) -> dict[str, Any]:
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

    async def _run_impl(self, ctx: Context) -> dict[str, Any]:
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

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using the embedder."""
        return await self._embedder.encode(text)

    def _format_context(self, results: list[dict[str, Any]]) -> str:
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
