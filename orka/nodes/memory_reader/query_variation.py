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
Query Variation Mixin
=====================

Methods for generating query variations for improved search recall.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class QueryVariationMixin:
    """Mixin providing query variation generation methods."""

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
                        "this", "that", "with", "from", "they",
                        "were", "been", "have", "their", "said",
                        "each", "which", "what", "where",
                    }
                ]
                context_terms.update(words[:3])  # Top 3 terms per context item

            # Create context-enhanced variations
            if context_terms:
                for term in list(context_terms)[:2]:  # Use top 2 context terms
                    context_variations.extend([
                        f"{query} {term}",
                        f"{term} {query}",
                        f"{query} related to {term}",
                    ])

            # Add context variations (deduplicated)
            for var in context_variations:
                if var not in variations:
                    variations.append(var)

        # Limit total variations to avoid excessive processing
        return variations[:8]  # Max 8 variations

    def _generate_query_variations(self, query: str) -> list[str]:
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
            variations.extend([
                word,
                f"about {word}",
                f"{word} information",
                f"what is {word}",
                f"tell me about {word}",
            ])

        elif len(words) == 2:
            # Two word queries - create combinations
            variations.extend([
                query_lower,
                " ".join(reversed(words)),
                f"about {query_lower}",
                f"{words[0]} and {words[1]}",
                f"information about {query_lower}",
            ])

        else:
            # Multi-word queries
            variations.extend([
                query_lower,
                f"about {query_lower}",
                f"information on {query_lower}",
                # Take first and last words
                f"{words[0]} {words[-1]}",
                # Take first two words
                " ".join(words[:2]),
                # Take last two words
                " ".join(words[-2:]),
            ])

        # Remove duplicates while preserving order
        unique_variations = []
        for v in variations:
            if v and v not in unique_variations:
                unique_variations.append(v)

        return unique_variations

