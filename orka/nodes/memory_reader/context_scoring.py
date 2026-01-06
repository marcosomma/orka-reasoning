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
Context Scoring Mixin
=====================

Methods for context-aware scoring and temporal ranking.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContextScoringMixin:
    """Mixin providing context scoring and temporal ranking methods."""

    # Attributes expected from host class
    context_weight: float
    temporal_decay_hours: float
    temporal_weight: float
    context_window_size: int
    _search_metrics: dict

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
            "hnsw_enabled": getattr(self, "use_hnsw", True),
            "hybrid_search_enabled": getattr(self, "hybrid_search_enabled", True),
            "ef_runtime": getattr(self, "ef_runtime", 10),
            "similarity_threshold": getattr(self, "similarity_threshold", 0.7),
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
                        "response", "answer", "result", "output",
                        "content", "message", "text", "summary",
                    ]

                    for field in content_fields:
                        if output.get(field):
                            conversation_context.append({
                                "agent_id": agent_id,
                                "content": str(output[field]),
                                "timestamp": time.time(),
                                "field": field,
                            })
                            break

                elif isinstance(output, (str, int, float)):
                    conversation_context.append({
                        "agent_id": agent_id,
                        "content": str(output),
                        "timestamp": time.time(),
                        "field": "direct_output",
                    })

        # Also try to extract from direct context fields
        context_fields = ["conversation", "history", "context", "previous_messages"]
        for field in context_fields:
            if context.get(field):
                if isinstance(context[field], list):
                    for item in context[field]:
                        if isinstance(item, dict) and "content" in item:
                            conversation_context.append({
                                "content": str(item["content"]),
                                "timestamp": item.get("timestamp", time.time()),
                                "source": field,
                            })
                elif isinstance(context[field], str):
                    conversation_context.append({
                        "content": context[field],
                        "timestamp": time.time(),
                        "source": field,
                    })

        # Limit context window size and return most recent items
        context_window_size = getattr(self, "context_window_size", 10)
        if len(conversation_context) > context_window_size:
            conversation_context.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return list(conversation_context)[:context_window_size]

        return conversation_context

