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
Embedding Operations Mixin
==========================

Provides embedding generation and content formatting operations.
"""

import asyncio
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingMixin:
    """Mixin providing embedding and content formatting operations."""

    def _format_content(self, content: str) -> str:
        """Format content according to format parameters."""
        if not self.format_params:
            return content

        try:
            formatted_content = content
            if self.format_params.get("format_response", True):
                if not self.format_params.get("preserve_newlines", False):
                    formatted_content = formatted_content.replace("\n", " ")

                filters = self.format_params.get("format_filters", [])
                for filter_config in filters:
                    if filter_config.get("type") == "replace":
                        pattern = filter_config.get("pattern", "")
                        replacement = filter_config.get("replacement", "")
                        if pattern and replacement is not None:
                            formatted_content = formatted_content.replace(
                                pattern, replacement
                            )

            return formatted_content
        except Exception as e:
            logger.warning(f"Error formatting content: {e}")
            return content

    def _get_embedding_sync(self, text: str) -> np.ndarray | None:
        """Get embedding in a sync context, handling async embedder properly."""
        if not self.embedder:
            return None

        try:
            # Check if we're in an async context
            try:
                asyncio.get_running_loop()
                in_async = True
            except RuntimeError:
                in_async = False

            if in_async:
                # In async context - use fallback encoding if available
                if hasattr(self.embedder, "_fallback_encode"):
                    logger.debug("In async context, using fallback encoding")
                    result = self.embedder._fallback_encode(text)
                    if result is not None:
                        return result
                    # Fallback returned None, try sync method
                    if hasattr(self.embedder, "encode_sync"):
                        return self.embedder.encode_sync(text)
                    logger.debug("No sync encoding available in async context")
                    return None
                else:
                    logger.debug("No fallback encoder available in async context")
                    return None
            else:
                # No running event loop - safe to use asyncio.run()
                return asyncio.run(self.embedder.encode(text))

        except Exception as e:
            error_msg = str(e) if str(e) else type(e).__name__
            logger.warning(f"Failed to get embedding: {error_msg}")
            embedding_dim = getattr(self.embedder, "embedding_dim", 384)
            return np.zeros(embedding_dim, dtype=np.float32)

