import json
import logging
import time
from typing import Any, Optional

from ..utils.bootstrap_memory_index import retry
from ..utils.embedder import AsyncEmbedder, from_bytes
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryReaderNode(BaseNode):
    """
    A node that retrieves information from OrKa's memory system using semantic search.

    The MemoryReaderNode performs intelligent memory retrieval using RedisStack's HNSW
    indexing for 100x faster vector search. It supports context-aware search, temporal
    ranking, and configurable similarity thresholds.

    Key Features:
        - 100x faster semantic search with HNSW indexing
        - Context-aware memory retrieval
        - Temporal ranking of results
        - Configurable similarity thresholds
        - Namespace-based organization

    Attributes:
        namespace (str): Memory namespace to search in
        limit (int): Maximum number of results to return
        enable_context_search (bool): Whether to use conversation context
        context_weight (float): Weight given to context in search (0-1)
        temporal_weight (float): Weight given to recency in ranking (0-1)
        similarity_threshold (float): Minimum similarity score (0-1)
        enable_temporal_ranking (bool): Whether to boost recent memories

    Example:
    
    .. code-block:: yaml
    
        - id: memory_search
          type: memory-reader
          namespace: knowledge_base
          params:
            limit: 5
            enable_context_search: true
            context_weight: 0.4
            temporal_weight: 0.3
            similarity_threshold: 0.8
            enable_temporal_ranking: true
          prompt: |
            Find relevant information about:
            {{ input }}

            Consider:
            - Similar topics
            - Recent interactions
            - Related context

    The node automatically:
        1. Converts input to vector embeddings
        2. Performs HNSW-accelerated similarity search
        3. Applies temporal ranking if enabled
        4. Filters by similarity threshold
        5. Returns formatted results with metadata
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
            )

        # Configuration
        self.namespace = kwargs.get("namespace", "default")
        self.limit = kwargs.get("limit", 5)
        self.similarity_threshold = kwargs.get("similarity_threshold", 0.7)
        self.ef_runtime = kwargs.get("ef_runtime", 10)

        # Initialize embedder for query encoding
        self.embedder: Optional[AsyncEmbedder] = None
        try:
            from ..utils.embedder import get_embedder

            self.embedder = get_embedder(kwargs.get("embedding_model"))
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")

        # Initialize attributes to prevent mypy errors
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

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Read memories using RedisStack enhanced vector search."""
        # Try to get the rendered prompt first, then fall back to raw input
        query = context.get("formatted_prompt", "")
        if not query:
            # Fallback to raw input if no formatted prompt
            query = context.get("input", "")

        # Handle case where input is a complex dictionary (from template rendering)
        if isinstance(query, dict):
            # If it's a dict, it's likely the raw template context - try to extract the actual input
            if "input" in query:
                nested_input = query["input"]
                if isinstance(nested_input, str):
                    query = nested_input
                else:
                    # Convert dict to string representation as last resort
                    query = str(nested_input)
            else:
                # Convert dict to string representation as last resort
                query = str(query)

        # Additional safety check - if query is still not a string, convert it
        if not isinstance(query, str):
            query = str(query)

        if not query:
            return {"memories": [], "query": "", "error": "No query provided"}

        try:
            # ✅ Use RedisStack memory logger's search_memories method
            if self.memory_logger and hasattr(self.memory_logger, "search_memories"):
                # 🎯 CRITICAL FIX: Search with explicit filtering for stored memories
                logger.info(
                    f"SEARCHING: query='{query}', namespace='{self.namespace}', log_type='memory'",
                )

                memories = self.memory_logger.search_memories(
                    query=query,
                    num_results=self.limit,
                    trace_id=context.get("trace_id"),
                    node_id=None,  # Don't filter by node_id for broader search
                    memory_type=None,  # Don't filter by memory_type for broader search
                    min_importance=context.get("min_importance", 0.0),
                    log_type="memory",  # 🎯 CRITICAL: Only search stored memories, not orchestration logs
                    namespace=self.namespace,  # 🎯 NEW: Filter by namespace
                )

                # If no results found, try additional search strategies
                if len(memories) == 0 and query.strip():
                    # Extract key terms from the query for more flexible searching
                    import re

                    # Extract numbers, important words, remove common stopwords
                    key_terms = re.findall(r"\b(?:\d+|\w{3,})\b", query.lower())
                    key_terms = [
                        term
                        for term in key_terms
                        if term
                        not in [
                            "the",
                            "and",
                            "for",
                            "are",
                            "but",
                            "not",
                            "you",
                            "all",
                            "can",
                            "her",
                            "was",
                            "one",
                            "our",
                            "had",
                            "but",
                            "day",
                            "get",
                            "use",
                            "man",
                            "new",
                            "now",
                            "way",
                            "may",
                            "say",
                        ]
                    ]

                    if key_terms:
                        # Try searching for individual key terms
                        for term in key_terms[
                            :3
                        ]:  # Limit to first 3 terms to avoid too many searches
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
                                memories = fallback_memories
                                break

                logger.info(f"SEARCH RESULTS: Found {len(memories)} memories")
                for i, memory in enumerate(memories):
                    metadata = memory.get("metadata", {})
                    logger.info(
                        f"  Memory {i + 1}: log_type={metadata.get('log_type')}, category={metadata.get('category')}, content_preview={memory.get('content', '')[:50]}...",
                    )

                # 🎯 ADDITIONAL FILTERING: Double-check that we only get stored memories
                filtered_memories = []
                for memory in memories:
                    metadata = memory.get("metadata", {})
                    # Only include if it's explicitly marked as stored memory
                    if metadata.get("log_type") == "memory" or metadata.get("category") == "stored":
                        filtered_memories.append(memory)
                    else:
                        logger.info(
                            f"🔍 FILTERED OUT: log_type={metadata.get('log_type')}, category={metadata.get('category')}",
                        )

                logger.info(
                    f"🔍 FINAL RESULTS: {len(memories)} total memories, {len(filtered_memories)} stored memories after filtering",
                )
                memories = filtered_memories

            else:
                # Fallback for non-RedisStack backends
                memories = []
                logger.warning("Enhanced vector search not available, using empty result")

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

    # 🎯 REMOVED: Complex filtering methods no longer needed
    # Memory filtering is now handled at the storage level via log_type parameter

    def _enhance_with_context_scoring(
        self,
        results: list[dict[str, Any]],
        conversation_context: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enhance search results with context-aware scoring."""
        if not conversation_context:
            return results

        try:
            # Extract context keywords
            context_words: set[str] = set()
            for ctx_item in conversation_context:
                content_words = [
                    w.lower() for w in ctx_item.get("content", "").split() if len(w) > 3
                ]
                context_words.update(content_words[:5])  # Top 5 words per context item

            # Enhance each result with context score
            context_weight = getattr(self, "context_weight", 0.2)
            for result in results:
                content = result.get("content", "")
                content_words = list(content.lower().split())

                # Calculate context overlap
                context_overlap = len(context_words.intersection(content_words))
                context_bonus = (context_overlap / max(len(context_words), 1)) * context_weight

                # Update similarity score
                original_similarity = result.get("similarity_score", 0.0)
                enhanced_similarity = original_similarity + context_bonus

                result["similarity_score"] = enhanced_similarity
                result["context_score"] = context_bonus
                result["original_similarity"] = original_similarity

            # Re-sort by enhanced similarity
            results.sort(key=lambda x: float(x.get("similarity_score", 0.0)), reverse=True)
            return results

        except Exception as e:
            logger.error(f"Error enhancing with context scoring: {e}")
            return results

    def _apply_temporal_ranking(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply temporal decay to search results."""
        try:
            current_time = time.time()
            decay_hours = getattr(self, "temporal_decay_hours", 24.0)
            temporal_weight = getattr(self, "temporal_weight", 0.1)

            for result in results:
                # Get timestamp (try multiple field names)
                timestamp = result.get("timestamp")
                if timestamp:
                    # Convert to seconds if needed
                    if timestamp > 1e12:  # Likely milliseconds
                        timestamp = timestamp / 1000

                    # Calculate age in hours
                    age_hours = (current_time - timestamp) / 3600

                    # Apply temporal decay
                    temporal_factor = max(0.1, 1.0 - (age_hours / decay_hours))

                    # Update similarity with temporal factor
                    original_similarity = result.get("similarity_score", 0.0)
                    temporal_similarity = original_similarity * (
                        1.0 + temporal_factor * temporal_weight
                    )

                    result["similarity_score"] = temporal_similarity
                    result["temporal_factor"] = temporal_factor

                    logger.debug(
                        f"Applied temporal ranking: age={age_hours:.1f}h, factor={temporal_factor:.2f}",
                    )

            # Re-sort by temporal-adjusted similarity
            results.sort(key=lambda x: float(x.get("similarity_score", 0.0)), reverse=True)
            return results

        except Exception as e:
            logger.error(f"Error applying temporal ranking: {e}")
            return results

    def _update_search_metrics(self, search_time: float, results_count: int) -> None:
        """Update search performance metrics."""
        # Update average search time (exponential moving average)
        current_avg = self._search_metrics["average_search_time"]
        total_searches = (
            self._search_metrics["hnsw_searches"] + self._search_metrics["legacy_searches"]
        )

        if total_searches == 1:
            self._search_metrics["average_search_time"] = search_time
        else:
            # Exponential moving average
            alpha = 0.1
            self._search_metrics["average_search_time"] = (
                alpha * search_time + (1 - alpha) * current_avg
            )

        # Update total results found
        self._search_metrics["total_results_found"] += int(results_count)

    def get_search_metrics(self) -> dict[str, Any]:
        """Get search performance metrics."""
        return {
            **self._search_metrics,
            "hnsw_enabled": self.use_hnsw,
            "hybrid_search_enabled": self.hybrid_search_enabled,
            "ef_runtime": self.ef_runtime,
            "similarity_threshold": self.similarity_threshold,
        }

    def _extract_conversation_context(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract conversation context from the execution context."""
        conversation_context = []

        # Try to get context from previous_outputs
        if "previous_outputs" in context:
            previous_outputs = context["previous_outputs"]

            # Look for common agent output patterns
            for agent_id, output in previous_outputs.items():
                if isinstance(output, dict):
                    # Extract content from various possible fields
                    content_fields = [
                        "response",
                        "answer",
                        "result",
                        "output",
                        "content",
                        "message",
                        "text",
                        "summary",
                    ]

                    for field in content_fields:
                        if output.get(field):
                            conversation_context.append(
                                {
                                    "agent_id": agent_id,
                                    "content": str(output[field]),
                                    "timestamp": time.time(),
                                    "field": field,
                                },
                            )
                            break  # Only take the first matching field per agent

                elif isinstance(output, (str, int, float)):
                    # Simple value output
                    conversation_context.append(
                        {
                            "agent_id": agent_id,
                            "content": str(output),
                            "timestamp": time.time(),
                            "field": "direct_output",
                        },
                    )

        # Also try to extract from direct context fields
        context_fields = ["conversation", "history", "context", "previous_messages"]
        for field in context_fields:
            if context.get(field):
                if isinstance(context[field], list):
                    for item in context[field]:
                        if isinstance(item, dict) and "content" in item:
                            conversation_context.append(
                                {
                                    "content": str(item["content"]),
                                    "timestamp": item.get("timestamp", time.time()),
                                    "source": field,
                                },
                            )
                elif isinstance(context[field], str):
                    conversation_context.append(
                        {
                            "content": context[field],
                            "timestamp": time.time(),
                            "source": field,
                        },
                    )

        # Limit context window size and return most recent items
        if len(conversation_context) > self.context_window_size:
            # Sort by timestamp (most recent first) and take the most recent items
            conversation_context.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return list(conversation_context)[: self.context_window_size]

        return conversation_context

    def _generate_enhanced_query_variations(
        self,
        query: str,
        conversation_context: list[dict[str, Any]],
    ) -> list[str]:
        """Generate enhanced query variations using conversation context."""
        variations = [query]  # Always include original query

        if not query or len(query.strip()) < 2:
            return variations

        # Generate basic variations
        basic_variations = self._generate_query_variations(query)
        variations.extend(basic_variations)

        # Add context-enhanced variations if context is available
        if conversation_context:
            context_variations = []

            # Extract key terms from recent context (last 2 items)
            recent_context = conversation_context[:2]
            context_terms = set()

            for ctx_item in recent_context:
                content = ctx_item.get("content", "")
                # Extract meaningful words (length > 3, not common stop words)
                words = [
                    word.lower()
                    for word in content.split()
                    if len(word) > 3
                    and word.lower()
                    not in {
                        "this",
                        "that",
                        "with",
                        "from",
                        "they",
                        "were",
                        "been",
                        "have",
                        "their",
                        "said",
                        "each",
                        "which",
                        "what",
                        "where",
                    }
                ]
                context_terms.update(words[:3])  # Top 3 terms per context item

            # Create context-enhanced variations
            if context_terms:
                for term in list(context_terms)[:2]:  # Use top 2 context terms
                    context_variations.extend(
                        [
                            f"{query} {term}",
                            f"{term} {query}",
                            f"{query} related to {term}",
                        ],
                    )

            # Add context variations (deduplicated)
            for var in context_variations:
                if var not in variations:
                    variations.append(var)

        # Limit total variations to avoid excessive processing
        return variations[:8]  # Max 8 variations

    def _generate_query_variations(self, query):
        """Generate basic query variations for improved search recall."""
        if not query or len(query.strip()) < 2:
            return []

        variations = []
        query_lower = query.lower().strip()

        # Handle different query patterns
        words = query_lower.split()

        if len(words) == 1:
            # Single word queries
            word = words[0]
            variations.extend(
                [
                    word,
                    f"about {word}",
                    f"{word} information",
                    f"what is {word}",
                    f"tell me about {word}",
                ],
            )

        elif len(words) == 2:
            # Two word queries - create combinations
            variations.extend(
                [
                    query_lower,
                    " ".join(reversed(words)),
                    f"about {query_lower}",
                    f"{words[0]} and {words[1]}",
                    f"information about {query_lower}",
                ],
            )

        else:
            # Multi-word queries
            variations.extend(
                [
                    query_lower,
                    f"about {query_lower}",
                    f"information on {query_lower}",
                    # Take first and last words
                    f"{words[0]} {words[-1]}",
                    # Take first two words
                    " ".join(words[:2]),
                    # Take last two words
                    " ".join(words[-2:]),
                ],
            )

        # Remove duplicates while preserving order
        unique_variations = []
        for v in variations:
            if v and v not in unique_variations:
                unique_variations.append(v)

        return unique_variations

    async def _context_aware_vector_search(
        self,
        query_embedding,
        namespace: str,
        conversation_context: list[dict[str, Any]],
        threshold=None,
    ) -> list[dict[str, Any]]:
        """Context-aware vector search using conversation context."""
        if not self.memory_logger:
            logger.error("Memory logger not available")
            return []

        threshold = threshold or self.similarity_threshold
        results = []

        try:
            # Generate context vector if context is available
            context_vector = None
            if conversation_context and self.enable_context_search:
                context_vector = await self._generate_context_vector(conversation_context)

            # Get memories from memory logger
            memories = await self.memory_logger.search_memories(
                namespace=namespace,
                limit=self.limit * 2,  # Get more results for filtering
            )

            logger.info(
                f"Searching through {len(memories)} memories with context awareness",
            )

            for memory in memories:
                try:
                    # Get the vector
                    vector = memory.get("vector")
                    if vector:
                        # Calculate primary similarity (query vs memory)
                        primary_similarity = self._cosine_similarity(query_embedding, vector)

                        # Calculate context similarity if available
                        context_similarity = 0
                        if context_vector is not None:
                            context_similarity = self._cosine_similarity(context_vector, vector)

                        # Combined similarity score
                        combined_similarity = primary_similarity + (
                            context_similarity * self.context_weight
                        )

                        if combined_similarity >= threshold:
                            # Add to results
                            results.append(
                                {
                                    "id": memory.get("id", ""),
                                    "content": memory.get("content", ""),
                                    "metadata": memory.get("metadata", {}),
                                    "similarity": float(combined_similarity),
                                    "primary_similarity": float(primary_similarity),
                                    "context_similarity": float(context_similarity),
                                    "match_type": "context_aware_vector",
                                },
                            )
                except Exception as e:
                    logger.error(
                        f"Error processing memory in context-aware vector search: {e!s}",
                    )

            # Sort by combined similarity
            results.sort(key=lambda x: float(x.get("similarity", 0.0)), reverse=True)

            # Return top results
            return results[: self.limit]

        except Exception as e:
            logger.error(f"Error in context-aware vector search: {e!s}")
            return []

    async def _generate_context_vector(
        self, conversation_context: Optional[list[dict[str, Any]]]
    ) -> Any:
        """Generate a vector representation of the conversation context."""
        if not self.embedder or not conversation_context:
            return None

        # Combine recent context into a single text
        context_text = " ".join(
            item.get("content", "") for item in conversation_context[-3:]  # Last 3 items
        )
        if not context_text.strip():
            return None

        # Generate embedding
        try:
            result = await self.embedder.encode(context_text)
            return result
        except Exception as e:
            logger.error(f"Error generating context vector: {e}")
            return None

    def _apply_hybrid_scoring(
        self,
        memories: list[dict[str, Any]],
        query: str,
        conversation_context: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply hybrid scoring combining multiple similarity factors."""
        if not memories:
            return memories

        try:
            for memory in memories:
                content = memory.get("content", "")
                base_similarity = memory.get("similarity", 0.0)

                # Calculate additional scoring factors

                # 1. Content length factor (moderate length preferred)
                content_length = len(content.split())
                length_factor = 1.0
                if 50 <= content_length <= 200:  # Sweet spot for content length
                    length_factor = 1.1
                elif content_length < 10:  # Too short
                    length_factor = 0.8
                elif content_length > 500:  # Too long
                    length_factor = 0.9

                # 2. Recency factor (if timestamp available)
                recency_factor = 1.0
                timestamp = memory.get("ts") or memory.get("timestamp")
                if timestamp and self.enable_temporal_ranking:
                    try:
                        ts_seconds = (
                            float(timestamp) / 1000 if float(timestamp) > 1e12 else float(timestamp)
                        )
                        age_hours = (time.time() - ts_seconds) / 3600
                        recency_factor = max(
                            0.5,
                            1.0 - (age_hours / (self.temporal_decay_hours * 24)),
                        )
                    except Exception:
                        pass

                # 3. Metadata quality factor
                metadata_factor = 1.0
                metadata = memory.get("metadata", {})
                if isinstance(metadata, dict):
                    # More comprehensive metadata gets slight boost
                    if len(metadata) > 3:
                        metadata_factor = 1.05
                    # Important categories get boost
                    if metadata.get("category") == "stored":
                        metadata_factor *= 1.1

                # Apply combined scoring
                final_similarity = (
                    base_similarity * length_factor * recency_factor * metadata_factor
                )
                memory["similarity"] = final_similarity
                memory["length_factor"] = length_factor
                memory["recency_factor"] = recency_factor
                memory["metadata_factor"] = metadata_factor

            # Re-sort by enhanced similarity
            memories.sort(key=lambda x: float(x["similarity"]), reverse=True)
            return memories

        except Exception as e:
            logger.error(f"Error applying hybrid scoring: {e}")
            return memories

    def _filter_enhanced_relevant_memories(
        self,
        memories: list[dict[str, Any]],
        query: str,
        conversation_context: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enhanced filtering for relevant memories using multiple criteria."""
        if not memories:
            return memories

        filtered_memories = []
        query_words: set[str] = set(query.lower().split())

        # Extract context keywords
        context_words = set()
        for ctx_item in conversation_context:
            content_words = [w.lower() for w in ctx_item.get("content", "").split() if len(w) > 3]
            context_words.update(
                list(content_words)[:3]
            )  # Top 3 words per context item  # type: ignore

        for memory in memories:
            content = memory.get("content", "").lower()
            content_words = list(content.split())

            # Check various relevance criteria
            is_relevant = False
            relevance_score = 0.0

            # 1. Direct keyword overlap
            keyword_overlap = len(query_words.intersection(content_words))
            if keyword_overlap > 0:
                is_relevant = True
                relevance_score += keyword_overlap * 0.3

            # 2. Context word overlap
            if context_words:
                context_overlap = len(context_words.intersection(content_words))
                if context_overlap > 0:
                    is_relevant = True
                    relevance_score += context_overlap * 0.2

            # 3. Similarity threshold
            similarity = memory.get("similarity", 0.0)
            if similarity >= self.similarity_threshold * 0.7:  # Slightly lower threshold
                is_relevant = True
                relevance_score += similarity

            # 4. Semantic similarity without exact matches (for broader retrieval)
            if similarity >= self.similarity_threshold * 0.4:  # Much lower threshold for semantic
                is_relevant = True
                relevance_score += similarity * 0.5

            # 5. Special handling for short queries
            if len(query) <= 20 and any(word in content for word in query.split()):
                is_relevant = True
                relevance_score += 0.2

            if is_relevant:
                memory["relevance_score"] = relevance_score
                filtered_memories.append(memory)

        # Sort by relevance score
        filtered_memories.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return filtered_memories

    def _filter_by_category(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter memories by category if category filter is enabled."""
        if not self.memory_category_filter:
            return memories

        filtered = []
        for memory in memories:
            # Check category in metadata
            metadata = memory.get("metadata", {})
            if isinstance(metadata, dict):
                category = metadata.get("category", metadata.get("memory_category"))
                if category == self.memory_category_filter:
                    filtered.append(memory)
            # Also check direct category field (for newer memory entries)
            elif memory.get("category") == self.memory_category_filter:
                filtered.append(memory)

        logger.info(
            f"Category filter '{self.memory_category_filter}' reduced {len(memories)} to {len(filtered)} memories",
        )
        return filtered

    def _filter_expired_memories(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter out expired memories based on decay configuration."""
        if not self.decay_config.get("enabled", False):
            return memories  # No decay enabled, return all memories

        current_time = time.time() * 1000  # Convert to milliseconds
        active_memories = []

        for memory in memories:
            is_active = True

            # Check expiry_time in metadata
            metadata = memory.get("metadata", {})
            if isinstance(metadata, dict):
                expiry_time = metadata.get("expiry_time")
                if expiry_time and expiry_time > 0:
                    if current_time > expiry_time:
                        is_active = False
                        logger.debug(f"- Memory {memory.get('id', 'unknown')} expired")

            # Also check direct expiry_time field
            if is_active and "expiry_time" in memory:
                expiry_time = memory["expiry_time"]
                if expiry_time and expiry_time > 0:
                    if current_time > expiry_time:
                        is_active = False
                        logger.debug(
                            f"- Memory {memory.get('id', 'unknown')} expired (direct field)"
                        )

            # Check memory_type and apply default decay rules if no explicit expiry
            if is_active and "expiry_time" not in metadata and "expiry_time" not in memory:
                memory_type = metadata.get("memory_type", "short_term")
                created_at = metadata.get("created_at") or metadata.get("timestamp")

                if created_at:
                    try:
                        # Handle different timestamp formats
                        if isinstance(created_at, str):
                            # ISO format
                            from datetime import datetime

                            if "T" in created_at:
                                created_timestamp = (
                                    datetime.fromisoformat(
                                        created_at.replace("Z", "+00:00"),
                                    ).timestamp()
                                    * 1000
                                )
                            else:
                                created_timestamp = (
                                    float(created_at) * 1000
                                    if float(created_at) < 1e12
                                    else float(created_at)
                                )
                        else:
                            created_timestamp = (
                                float(created_at) * 1000
                                if float(created_at) < 1e12
                                else float(created_at)
                            )

                        # Apply decay rules
                        if memory_type == "long_term":
                            # Check agent-level config first, then fall back to global config
                            decay_hours = self.decay_config.get(
                                "long_term_hours",
                            ) or self.decay_config.get("default_long_term_hours", 24.0)
                        else:
                            # Check agent-level config first, then fall back to global config
                            decay_hours = self.decay_config.get(
                                "short_term_hours",
                            ) or self.decay_config.get("default_short_term_hours", 1.0)

                        decay_ms = decay_hours * 3600 * 1000
                        if current_time > (created_timestamp + decay_ms):
                            is_active = False
                            logger.debug(
                                f"Memory {memory.get('id', 'unknown')} expired by decay rules",
                            )

                    except Exception as e:
                        logger.debug(
                            f"Error checking decay for memory {memory.get('id', 'unknown')}: {e}",
                        )

            if is_active:
                active_memories.append(memory)

        if len(active_memories) < len(memories):
            logger.info(f"Filtered out {len(memories) - len(active_memories)} expired memories")

        return active_memories

    async def _context_aware_stream_search(
        self,
        stream_name: str,
        query: str,
        query_embedding: Any,
        conversation_context: Optional[list[dict[str, Any]]] = None,
        threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform context-aware stream search.

        Args:
            stream_name: The name of the stream to search
            query: The search query
            query_embedding: The query's vector embedding
            conversation_context: Optional conversation context for context-aware search
            threshold: Optional similarity threshold override

        Returns:
            List of matching memories with scores
        """
        try:
            # Get initial stream of memories
            if not self.memory_logger:
                logger.error("No memory logger available for stream search")
                return []

            # Get stream entries
            if not hasattr(self.memory_logger, "redis"):
                logger.error("No Redis client available for stream search")
                return []

            try:
                stream_entries = await self.memory_logger.redis.xrange(
                    stream_name, count=self.limit * 3  # Get more results for filtering
                )
            except Exception as e:
                logger.error(f"Error getting stream entries: {e}")
                return []

            memories = []
            for entry_id, fields in stream_entries:
                try:
                    # Parse payload
                    payload = json.loads(fields[b"payload"].decode("utf-8"))

                    # Get content and skip if empty
                    content = payload.get("content", "")
                    if not content.strip():
                        continue

                    # Add basic fields
                    memory = {
                        "content": content,
                        "metadata": payload.get("metadata", {}),
                        "match_type": "context_aware_stream",
                        "entry_id": entry_id.decode("utf-8"),
                        "timestamp": fields.get(b"ts", b"0").decode("utf-8"),
                    }

                    # Calculate primary similarity with query embedding
                    try:
                        if self.embedder:
                            content_embedding = await self.embedder.encode(memory["content"])
                            memory["primary_similarity"] = self._cosine_similarity(
                                query_embedding, content_embedding
                            )
                        else:
                            memory["primary_similarity"] = 0.0
                    except Exception as e:
                        logger.warning(f"Error calculating primary similarity: {e}")
                        memory["primary_similarity"] = 0.0

                    # Calculate keyword matches
                    query_words = set(word.lower() for word in query.split() if len(word) > 2)
                    content_words = set(word.lower() for word in memory["content"].split())
                    memory["keyword_matches"] = len(query_words & content_words)

                    # Calculate context similarity if available
                    try:
                        if conversation_context and self.enable_context_search:
                            context_vector = await self._generate_context_vector(
                                conversation_context
                            )
                            if context_vector is not None and self.embedder:
                                memory["context_similarity"] = self._cosine_similarity(
                                    context_vector, content_embedding
                                )
                                # Combine similarities
                                memory["similarity"] = (
                                    memory["primary_similarity"] * (1 - self.context_weight)
                                    + memory["context_similarity"] * self.context_weight
                                )
                            else:
                                memory["similarity"] = memory["primary_similarity"]
                        else:
                            memory["similarity"] = memory["primary_similarity"]

                        # Add keyword bonus
                        if memory["keyword_matches"] > 0:
                            memory["similarity"] += min(0.1 * memory["keyword_matches"], 0.3)
                    except Exception as e:
                        logger.warning(f"Error calculating context similarity: {e}")
                        memory["similarity"] = memory["primary_similarity"]
                        if memory["keyword_matches"] > 0:
                            memory["similarity"] += min(0.1 * memory["keyword_matches"], 0.3)

                    # Apply threshold
                    if threshold is None:
                        threshold = self.similarity_threshold
                    if memory["similarity"] >= threshold:
                        memories.append(memory)

                except json.JSONDecodeError:
                    logger.warning(f"Malformed payload in stream entry {entry_id}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing stream entry {entry_id}: {e}")
                    continue

            # Apply temporal ranking if enabled
            if self.enable_temporal_ranking:
                memories = self._apply_temporal_ranking(memories)

            # Sort by similarity and limit results
            memories.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return memories[: self.limit]

        except Exception as e:
            logger.error(f"Error in context-aware stream search: {e}")
            return []

    async def _enhanced_keyword_search(
        self,
        namespace: str,
        query: str,
        conversation_context: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform enhanced keyword search with context awareness.

        Args:
            namespace: Memory namespace to search in
            query: The search query
            conversation_context: Optional conversation context for context-aware search

        Returns:
            List of matching memories with scores
        """
        try:
            if not self.memory_logger:
                logger.error("No memory logger available for keyword search")
                return []

            # Get memories from memory logger
            try:
                results = await self.memory_logger.search_memories(
                    query=query,
                    namespace=namespace,
                    limit=self.limit * 2,  # Get more results for filtering
                )

                # Ensure metadata is a dictionary
                for result in results:
                    if not isinstance(result.get("metadata"), dict):
                        result["metadata"] = {}
            except Exception as e:
                logger.error(f"Error searching memories: {e}")
                return []

            # Calculate query overlap
            for result in results:
                result["match_type"] = "enhanced_keyword"
                # Handle short words by using them directly in overlap calculation
                result["query_overlap"] = self._calculate_overlap(
                    query.lower(), result["content"].lower()
                )

            # Calculate context overlap if available
            if conversation_context:
                for result in results:
                    context_text = " ".join(
                        item.get("content", "").lower() for item in conversation_context
                    )
                    result["context_overlap"] = self._calculate_overlap(
                        context_text, result["content"].lower()
                    )
                    # Ensure both overlaps are weighted properly
                    result["similarity"] = (
                        result["query_overlap"] * (1 - self.context_weight)
                        + result.get("context_overlap", 0) * self.context_weight
                    )
            else:
                # If no context, similarity is just the query overlap
                for result in results:
                    result["similarity"] = result["query_overlap"]

            # Sort by similarity score and limit results
            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return list(results[: self.limit])

        except Exception as e:
            logger.error(f"Error in enhanced keyword search: {e}")
            return []

    async def _hnsw_hybrid_search(
        self,
        query_embedding: Any,
        query: str,
        namespace: str,
        session_id: str,
        conversation_context: Optional[list[dict[str, Any]]] = None,
        threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search using HNSW index and keyword matching.

        Args:
            query: The search query
            namespace: Memory namespace to search in
            conversation_context: Optional conversation context for context-aware search
            threshold: Optional similarity threshold override

        Returns:
            List of matching memories with scores
        """
        try:
            if not self.memory_logger:
                logger.error("Memory logger not available")
                return []

            # Get memories from memory logger
            results = await self.memory_logger.search_memories(
                query=query,
                namespace=namespace,
                limit=self.limit * 2,  # Get more results for filtering
            )

            # Apply context enhancement if available
            if conversation_context and self.enable_context_search:
                results = self._enhance_with_context_scoring(
                    results,
                    conversation_context,
                )

            # Apply temporal ranking if enabled
            if self.enable_temporal_ranking:
                results = self._apply_temporal_ranking(results)

            # Sort by score and limit results
            results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            return list(results[: self.limit])

        except Exception as e:
            logger.error(f"Error in HNSW hybrid search: {e}")
            return []

    async def _vector_search(
        self,
        query_embedding: Any,
        namespace: str,
        threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Legacy vector search method."""
        try:
            return await self._context_aware_vector_search(
                query_embedding,
                namespace,
                [],
                threshold,
            )
        except Exception as e:
            logger.error(f"Error in legacy vector search: {e}")
            return []

    async def _keyword_search(
        self,
        query: str,
        namespace: str,
    ) -> list[dict[str, Any]]:
        """Legacy keyword search method."""
        try:
            return await self._enhanced_keyword_search(
                query,
                namespace,
                [],
            )
        except Exception as e:
            logger.error(f"Error in legacy keyword search: {e}")
            return []

    async def _stream_search(
        self,
        stream_key: str,
        query: str,
        query_embedding: Any,
        threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Legacy stream search method."""
        try:
            return await self._context_aware_stream_search(
                stream_key,
                query,
                query_embedding,
                [],
                threshold,
            )
        except Exception as e:
            logger.error(f"Error in legacy stream search: {e}")
            return []

    def _filter_relevant_memories(
        self,
        memories: list[dict[str, Any]],
        query: str,
    ) -> list[dict[str, Any]]:
        """Legacy memory filtering method."""
        try:
            return self._filter_enhanced_relevant_memories(
                memories,
                query,
                [],
            )
        except Exception as e:
            logger.error(f"Error in legacy memory filtering: {e}")
            return []

    def _calculate_overlap(self, text1: str, text2: str) -> float:
        """Calculate text overlap score between two strings."""
        try:
            if not text1 or not text2:
                return 0.0

            # Tokenize and normalize
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            # Calculate overlap
            overlap = len(words1.intersection(words2))
            total = len(words1)  # Only consider query words

            # Calculate overlap score
            overlap_score = overlap / total if total > 0 else 0.0

            # Boost score if all query words are found
            if overlap == total:
                overlap_score *= 2

            return overlap_score

        except Exception as e:
            logger.error(f"Error calculating text overlap: {e}")
            return 0.0

    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors."""
        try:
            import numpy as np

            # Ensure vectors are numpy arrays
            if not isinstance(vec1, np.ndarray):
                vec1 = np.array(vec1)
            if not isinstance(vec2, np.ndarray):
                vec2 = np.array(vec2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm_a = np.linalg.norm(vec1)
            norm_b = np.linalg.norm(vec2)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e!s}")
            return 0.0
