import logging
import re
from typing import Any, Optional

try:
    import numpy as np
except Exception:
    np = None

from ..utils.embedder import AsyncEmbedder
from .base_node import BaseNode
from .memory_reader.context_scoring import ContextScoringMixin
from .memory_reader.query_variation import QueryVariationMixin
from .memory_reader.search_methods import SearchMethodsMixin
from .memory_reader.filtering import FilteringMixin
from .memory_reader.utils import calculate_overlap, cosine_similarity

logger = logging.getLogger(__name__)


class MemoryReaderNode(
    BaseNode,
    ContextScoringMixin,
    QueryVariationMixin,
    SearchMethodsMixin,
    FilteringMixin,
):
    """
    A node that retrieves information from OrKa's memory system using semantic search.

    The MemoryReaderNode performs intelligent memory retrieval using RedisStack's HNSW
    indexing for 100x faster vector search. It supports context-aware search, temporal
    ranking, and configurable similarity thresholds.

    This class has been refactored into smaller mixins in the memory_reader/ package:
    - ContextScoringMixin: Context scoring, temporal ranking, metrics
    - QueryVariationMixin: Query variation generation
    - SearchMethodsMixin: Vector, keyword, hybrid, stream search
    - FilteringMixin: Memory filtering (category, expired, relevance)
    """

    def __init__(self, node_id: str, **kwargs):
        super().__init__(node_id=node_id, **kwargs)

        # Use memory logger instead of direct Redis
        self.memory_logger = kwargs.get("memory_logger")
        if not self.memory_logger:
            from ..memory_logger import create_memory_logger

            self.memory_logger = create_memory_logger(
                backend="redisstack",
                redis_url=kwargs.get("redis_url", "redis://localhost:6380/0"),
                embedder=kwargs.get("embedder"),
                memory_preset=kwargs.get("memory_preset"),
                operation="read",
            )

        # Apply operation-aware preset defaults
        config_with_preset_defaults = kwargs.copy()
        if kwargs.get("memory_preset"):
            from ..memory_logger import apply_memory_preset_to_config

            config_with_preset_defaults = apply_memory_preset_to_config(
                kwargs, memory_preset=kwargs.get("memory_preset"), operation="read"
            )

        # Configuration with preset-aware defaults
        self.namespace = config_with_preset_defaults.get("namespace", "default")
        self.limit = config_with_preset_defaults.get("limit", 5)
        self.similarity_threshold = config_with_preset_defaults.get("similarity_threshold", 0.7)
        self.ef_runtime = config_with_preset_defaults.get("ef_runtime", 10)

        # Initialize embedder for query encoding
        self.embedder: Optional[AsyncEmbedder] = None
        try:
            from ..utils.embedder import get_embedder

            self.embedder = get_embedder(kwargs.get("embedding_model"))
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")

        # Search configuration
        self.use_hnsw = kwargs.get("use_hnsw", True)
        self.hybrid_search_enabled = kwargs.get("hybrid_search_enabled", True)
        self.context_window_size = kwargs.get("context_window_size", 10)
        self.context_weight = kwargs.get("context_weight", 0.2)
        self.enable_context_search = kwargs.get("enable_context_search", True)
        self.enable_temporal_ranking = kwargs.get("enable_temporal_ranking", True)
        self.temporal_decay_hours = kwargs.get("temporal_decay_hours", 24.0)
        self.temporal_weight = kwargs.get("temporal_weight", 0.1)
        self.memory_category_filter = kwargs.get("memory_category_filter", None)
        self.decay_config = kwargs.get("decay_config", {})

        self._search_metrics = {
            "hnsw_searches": 0,
            "legacy_searches": 0,
            "total_results_found": 0,
            "average_search_time": 0.0,
        }

    async def _run_impl(self, context: dict[str, Any]) -> dict[str, Any]:
        """Read memories using RedisStack enhanced vector search."""
        query = self._extract_query(context)

        if not query:
            return {"memories": [], "query": "", "error": "No query provided"}

        try:
            memories = await self._search_memories(query, context)
            return {
                "memories": memories,
                "query": query,
                "backend": "redisstack",
                "search_type": "enhanced_vector",
                "num_results": len(memories),
            }

        except Exception as e:
            logger.error(f"Error reading memories: {e}")
            return {
                "memories": [],
                "query": query,
                "error": str(e),
                "backend": "redisstack",
            }

    def _extract_query(self, context: dict[str, Any]) -> str:
        """Extract query string from context."""
        query = context.get("formatted_prompt", "")
        if not query:
            query = context.get("input", "")

        # Handle case where input is a complex dictionary
        if isinstance(query, dict):
            if "input" in query:
                nested_input = query["input"]
                if isinstance(nested_input, str):
                    query = nested_input
                else:
                    query = str(nested_input)
            else:
                query = str(query)

        if not isinstance(query, str):
            query = str(query)

        return query

    async def _search_memories(
        self, query: str, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Search memories with fallback strategies."""
        if not (self.memory_logger and hasattr(self.memory_logger, "search_memories")):
            logger.warning("Enhanced vector search not available, using empty result")
            return []

        logger.info(
            f"SEARCHING: query='{query}', namespace='{self.namespace}', log_type='memory'"
        )

        # Primary search
        memories = self.memory_logger.search_memories(
            query=query,
            num_results=self.limit,
            trace_id=context.get("trace_id"),
            node_id=None,
            memory_type=None,
            min_importance=context.get("min_importance", 0.0),
            log_type="memory",
            namespace=self.namespace,
        )

        # Fallback search if no results
        if len(memories) == 0 and query.strip():
            memories = self._fallback_key_term_search(query, context)

        logger.info(f"SEARCH RESULTS: Found {len(memories)} memories")
        self._log_memory_results(memories)

        # Filter to stored memories only
        return self._filter_stored_memories(memories)

    def _fallback_key_term_search(
        self, query: str, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Fallback search using key terms from query."""
        key_terms = re.findall(r"\b(?:\d+|\w{3,})\b", query.lower())
        stopwords = {
            "the", "and", "for", "are", "but", "not", "you", "all",
            "can", "her", "was", "one", "our", "had", "day", "get",
            "use", "man", "new", "now", "way", "may", "say",
        }
        key_terms = [term for term in key_terms if term not in stopwords]

        for term in key_terms[:3]:
            logger.info(f"FALLBACK SEARCH: Trying key term '{term}'")
            fallback_memories = self.memory_logger.search_memories(
                query=term,
                num_results=self.limit,
                trace_id=context.get("trace_id"),
                node_id=None,
                memory_type=None,
                min_importance=context.get("min_importance", 0.0),
                log_type="memory",
                namespace=self.namespace,
            )
            if fallback_memories:
                logger.info(
                    f"FALLBACK SUCCESS: Found {len(fallback_memories)} memories with term '{term}'"
                )
                return fallback_memories

        return []

    def _log_memory_results(self, memories: list[dict[str, Any]]) -> None:
        """Log memory search results for debugging."""
        for i, memory in enumerate(memories):
            metadata = memory.get("metadata", {})
            logger.info(
                f"  Memory {i + 1}: log_type={metadata.get('log_type')}, "
                f"category={metadata.get('category')}, "
                f"content_preview={memory.get('content', '')[:50]}..."
            )

    def _filter_stored_memories(
        self, memories: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter to only include stored memories."""
        filtered = []
        for memory in memories:
            metadata = memory.get("metadata", {})
            if metadata.get("log_type") == "memory" or metadata.get("category") == "stored":
                filtered.append(memory)
            else:
                logger.info(
                    f"[SEARCH] FILTERED OUT: log_type={metadata.get('log_type')}, "
                    f"category={metadata.get('category')}"
                )

        logger.info(
            f"[SEARCH] FINAL RESULTS: {len(memories)} total memories, "
            f"{len(filtered)} stored memories after filtering"
        )
        return filtered

    # Utility methods using module functions
    def _calculate_overlap(self, text1: str, text2: str) -> float:
        """Calculate text overlap score."""
        return calculate_overlap(text1, text2)

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors."""
        return cosine_similarity(vec1, vec2)
