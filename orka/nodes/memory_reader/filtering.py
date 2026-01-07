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
Filtering Mixin
===============

Methods for filtering memory search results.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FilteringMixin:
    """Mixin providing memory filtering methods."""

    # Attributes expected from host class
    similarity_threshold: float
    memory_category_filter: str | None
    decay_config: dict
    enable_temporal_ranking: bool
    temporal_decay_hours: float

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

                # 1. Content length factor (moderate length preferred)
                content_length = len(content.split())
                length_factor = 1.0
                if 50 <= content_length <= 200:
                    length_factor = 1.1
                elif content_length < 10:
                    length_factor = 0.8
                elif content_length > 500:
                    length_factor = 0.9

                # 2. Recency factor (if timestamp available)
                recency_factor = 1.0
                timestamp = memory.get("ts") or memory.get("timestamp")
                if timestamp and getattr(self, "enable_temporal_ranking", True):
                    try:
                        ts_seconds = (
                            float(timestamp) / 1000 if float(timestamp) > 1e12 else float(timestamp)
                        )
                        age_hours = (time.time() - ts_seconds) / 3600
                        decay_hours = getattr(self, "temporal_decay_hours", 24.0)
                        recency_factor = max(0.5, 1.0 - (age_hours / (decay_hours * 24)))
                    except Exception as e:
                        logger.debug(f"Recency factor calculation failed for timestamp {timestamp}: {e}")

                # 3. Metadata quality factor
                metadata_factor = 1.0
                metadata = memory.get("metadata", {})
                if isinstance(metadata, dict):
                    if len(metadata) > 3:
                        metadata_factor = 1.05
                    if metadata.get("category") == "stored":
                        metadata_factor *= 1.1

                # Apply combined scoring
                final_similarity = base_similarity * length_factor * recency_factor * metadata_factor
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
        context_words: set[str] = set()
        for ctx_item in conversation_context:
            content_words = [w.lower() for w in ctx_item.get("content", "").split() if len(w) > 3]
            context_words.update(list(content_words)[:3])

        threshold = getattr(self, "similarity_threshold", 0.7)

        for memory in memories:
            content = memory.get("content", "").lower()
            content_words_set = set(content.split())

            # Check various relevance criteria
            is_relevant = False
            relevance_score = 0.0

            # 1. Direct keyword overlap
            keyword_overlap = len(query_words.intersection(content_words_set))
            if keyword_overlap > 0:
                is_relevant = True
                relevance_score += keyword_overlap * 0.3

            # 2. Context word overlap
            if context_words:
                context_overlap = len(context_words.intersection(content_words_set))
                if context_overlap > 0:
                    is_relevant = True
                    relevance_score += context_overlap * 0.2

            # 3. Similarity threshold
            similarity = memory.get("similarity", 0.0)
            if similarity >= threshold * 0.7:
                is_relevant = True
                relevance_score += similarity

            # 4. Semantic similarity without exact matches
            if similarity >= threshold * 0.4:
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
        category_filter = getattr(self, "memory_category_filter", None)
        if not category_filter:
            return memories

        filtered = []
        for memory in memories:
            metadata = memory.get("metadata", {})
            if isinstance(metadata, dict):
                category = metadata.get("category", metadata.get("memory_category"))
                if category == category_filter:
                    filtered.append(memory)
            elif memory.get("category") == category_filter:
                filtered.append(memory)

        logger.info(
            f"Category filter '{category_filter}' reduced {len(memories)} to {len(filtered)} memories"
        )
        return filtered

    def _filter_expired_memories(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter out expired memories based on decay configuration."""
        decay_config = getattr(self, "decay_config", {})
        if not decay_config.get("enabled", False):
            return memories

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

            # Check memory_type and apply default decay rules
            if is_active and "expiry_time" not in metadata and "expiry_time" not in memory:
                memory_type = metadata.get("memory_type", "short_term")
                created_at = metadata.get("created_at") or metadata.get("timestamp")

                if created_at:
                    try:
                        # Handle different timestamp formats
                        if isinstance(created_at, str):
                            from datetime import datetime
                            if "T" in created_at:
                                created_timestamp = (
                                    datetime.fromisoformat(
                                        created_at.replace("Z", "+00:00")
                                    ).timestamp() * 1000
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
                            decay_hours = decay_config.get(
                                "long_term_hours"
                            ) or decay_config.get("default_long_term_hours", 24.0)
                        else:
                            decay_hours = decay_config.get(
                                "short_term_hours"
                            ) or decay_config.get("default_short_term_hours", 1.0)

                        decay_ms = decay_hours * 3600 * 1000
                        if current_time > (created_timestamp + decay_ms):
                            is_active = False

                    except Exception as e:
                        logger.debug(f"Error checking decay: {e}")

            if is_active:
                active_memories.append(memory)

        if len(active_memories) < len(memories):
            logger.info(f"Filtered out {len(memories) - len(active_memories)} expired memories")

        return active_memories

    def _filter_relevant_memories(
        self,
        memories: list[dict[str, Any]],
        query: str,
    ) -> list[dict[str, Any]]:
        """Legacy memory filtering method."""
        try:
            return self._filter_enhanced_relevant_memories(memories, query, [])
        except Exception as e:
            logger.error(f"Error in legacy memory filtering: {e}")
            return []

