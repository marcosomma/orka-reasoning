# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Search Methods Mixin
====================

Methods for various search strategies (vector, keyword, hybrid, stream).
"""

import json
import logging
from typing import Any, Optional

from .utils import calculate_overlap, cosine_similarity

logger = logging.getLogger(__name__)


class SearchMethodsMixin:
    """Mixin providing search methods for memory retrieval."""

    # Attributes expected from host class
    memory_logger: Any
    embedder: Any
    limit: int
    similarity_threshold: float
    context_weight: float
    enable_context_search: bool
    enable_temporal_ranking: bool

    async def _context_aware_vector_search(
        self,
        query_embedding,
        namespace: str,
        conversation_context: list[dict[str, Any]],
        threshold: float | None = None,
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
                limit=self.limit * 2,
            )

            logger.info(f"Searching through {len(memories)} memories with context awareness")

            for memory in memories:
                try:
                    vector = memory.get("vector")
                    if vector:
                        # Calculate primary similarity
                        primary_similarity = cosine_similarity(query_embedding, vector)

                        # Calculate context similarity if available
                        context_similarity = 0
                        if context_vector is not None:
                            context_similarity = cosine_similarity(context_vector, vector)

                        # Combined similarity score
                        combined_similarity = primary_similarity + (
                            context_similarity * self.context_weight
                        )

                        if combined_similarity >= threshold:
                            results.append({
                                "id": memory.get("id", ""),
                                "content": memory.get("content", ""),
                                "metadata": memory.get("metadata", {}),
                                "similarity": float(combined_similarity),
                                "primary_similarity": float(primary_similarity),
                                "context_similarity": float(context_similarity),
                                "match_type": "context_aware_vector",
                            })
                except Exception as e:
                    logger.error(f"Error processing memory: {e!s}")

            # Sort by combined similarity
            results.sort(key=lambda x: float(x.get("similarity", 0.0)), reverse=True)
            return results[:self.limit]

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
            item.get("content", "") for item in conversation_context[-3:]
        )
        if not context_text.strip():
            return None

        try:
            result = await self.embedder.encode(context_text)
            return result
        except Exception as e:
            logger.error(f"Error generating context vector: {e}")
            return None

    async def _enhanced_keyword_search(
        self,
        namespace: str,
        query: str,
        conversation_context: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """Perform enhanced keyword search with context awareness."""
        try:
            if not self.memory_logger:
                logger.error("No memory logger available for keyword search")
                return []

            try:
                results = await self.memory_logger.search_memories(
                    query=query,
                    namespace=namespace,
                    limit=self.limit * 2,
                )

                for result in results:
                    if not isinstance(result.get("metadata"), dict):
                        result["metadata"] = {}
            except Exception as e:
                logger.error(f"Error searching memories: {e}")
                return []

            # Calculate query overlap
            for result in results:
                result["match_type"] = "enhanced_keyword"
                result["query_overlap"] = calculate_overlap(
                    query.lower(), result["content"].lower()
                )

            # Calculate context overlap if available
            if conversation_context:
                for result in results:
                    context_text = " ".join(
                        item.get("content", "").lower() for item in conversation_context
                    )
                    result["context_overlap"] = calculate_overlap(
                        context_text, result["content"].lower()
                    )
                    result["similarity"] = (
                        result["query_overlap"] * (1 - self.context_weight)
                        + result.get("context_overlap", 0) * self.context_weight
                    )
            else:
                for result in results:
                    result["similarity"] = result["query_overlap"]

            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return list(results[:self.limit])

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
        """Perform hybrid search using HNSW index and keyword matching."""
        try:
            if not self.memory_logger:
                logger.error("Memory logger not available")
                return []

            results = await self.memory_logger.search_memories(
                query=query,
                namespace=namespace,
                limit=self.limit * 2,
            )

            # Apply context enhancement if available
            if conversation_context and self.enable_context_search:
                results = self._enhance_with_context_scoring(results, conversation_context)

            # Apply temporal ranking if enabled
            if self.enable_temporal_ranking:
                results = self._apply_temporal_ranking(results)

            results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            return list(results[:self.limit])

        except Exception as e:
            logger.error(f"Error in HNSW hybrid search: {e}")
            return []

    async def _context_aware_stream_search(
        self,
        stream_name: str,
        query: str,
        query_embedding: Any,
        conversation_context: Optional[list[dict[str, Any]]] = None,
        threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Perform context-aware stream search."""
        try:
            if not self.memory_logger:
                logger.error("No memory logger available for stream search")
                return []

            if not hasattr(self.memory_logger, "redis"):
                logger.error("No Redis client available for stream search")
                return []

            try:
                stream_entries = await self.memory_logger.redis.xrange(
                    stream_name, count=self.limit * 3
                )
            except Exception as e:
                logger.error(f"Error getting stream entries: {e}")
                return []

            memories = []
            threshold = threshold or self.similarity_threshold

            for entry_id, fields in stream_entries:
                try:
                    payload = json.loads(fields[b"payload"].decode("utf-8"))
                    content = payload.get("content", "")
                    if not content.strip():
                        continue

                    memory = {
                        "content": content,
                        "metadata": payload.get("metadata", {}),
                        "match_type": "context_aware_stream",
                        "entry_id": entry_id.decode("utf-8"),
                        "timestamp": fields.get(b"ts", b"0").decode("utf-8"),
                    }

                    # Calculate primary similarity
                    try:
                        if self.embedder:
                            content_embedding = await self.embedder.encode(memory["content"])
                            memory["primary_similarity"] = cosine_similarity(
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

                    # Calculate combined similarity
                    memory["similarity"] = memory["primary_similarity"]
                    if memory["keyword_matches"] > 0:
                        memory["similarity"] += min(0.1 * memory["keyword_matches"], 0.3)

                    if memory["similarity"] >= threshold:
                        memories.append(memory)

                except json.JSONDecodeError:
                    logger.warning(f"Malformed payload in stream entry {entry_id}")
                except Exception as e:
                    logger.error(f"Error processing stream entry {entry_id}: {e}")

            # Apply temporal ranking if enabled
            if self.enable_temporal_ranking:
                memories = self._apply_temporal_ranking(memories)

            memories.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return memories[:self.limit]

        except Exception as e:
            logger.error(f"Error in context-aware stream search: {e}")
            return []

    # Legacy methods for backward compatibility
    async def _vector_search(
        self,
        query_embedding: Any,
        namespace: str,
        threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Legacy vector search method."""
        try:
            return await self._context_aware_vector_search(
                query_embedding, namespace, [], threshold
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
            return await self._enhanced_keyword_search(query, namespace, [])
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
                stream_key, query, query_embedding, [], threshold
            )
        except Exception as e:
            logger.error(f"Error in legacy stream search: {e}")
            return []

    # These will be provided by ContextScoringMixin
    def _enhance_with_context_scoring(self, results, context):
        """Stub - provided by ContextScoringMixin."""
        return results

    def _apply_temporal_ranking(self, results):
        """Stub - provided by ContextScoringMixin."""
        return results

