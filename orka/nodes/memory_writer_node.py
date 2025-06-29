import logging
from typing import Any, Dict

from ..memory_logger import create_memory_logger
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryWriterNode(BaseNode):
    """Enhanced memory writer using RedisStack through memory logger."""

    def __init__(self, node_id: str, **kwargs):
        super().__init__(node_id=node_id, **kwargs)

        # ✅ CRITICAL: Use memory logger instead of direct Redis
        self.memory_logger = kwargs.get("memory_logger")
        if not self.memory_logger:
            # Create RedisStack memory logger
            self.memory_logger = create_memory_logger(
                backend="redisstack",
                enable_hnsw=kwargs.get("use_hnsw", True),
                vector_params=kwargs.get(
                    "vector_params",
                    {
                        "M": 16,
                        "ef_construction": 200,
                    },
                ),
                decay_config=kwargs.get("decay_config", {}),
            )

        # Configuration
        self.namespace = kwargs.get("namespace", "default")
        self.session_id = kwargs.get("session_id", "default")
        self.decay_config = kwargs.get("decay_config", {})

        # Remove direct Redis client - use memory logger instead
        # self.redis = redis.from_url(...)  # ← REMOVE

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Write to memory using RedisStack memory logger."""
        try:
            # 🎯 CRITICAL FIX: Extract structured memory object from validation guardian
            memory_content = self._extract_memory_content(context)
            if not memory_content:
                return {"status": "error", "error": "No memory content to store"}

            # Extract configuration from context
            namespace = context.get("namespace", self.namespace)
            session_id = context.get("session_id", self.session_id)
            metadata = context.get("metadata", {})

            # ✅ CRITICAL: Use memory logger for direct memory storage instead of orchestration logging
            memory_key = self.memory_logger.log_memory(
                content=memory_content,
                node_id=self.node_id,
                trace_id=session_id,
                metadata={
                    "namespace": namespace,
                    "session": session_id,
                    "category": "stored",  # Mark as stored memory
                    "log_type": "memory",  # 🎯 CRITICAL: Mark as stored memory, not orchestration log
                    "content_type": "user_input",
                    **metadata,  # Include any additional metadata from config
                },
                importance_score=self._calculate_importance_score(memory_content, metadata),
                memory_type=self._classify_memory_type(
                    metadata,
                    self._calculate_importance_score(memory_content, metadata),
                ),
                expiry_hours=self._get_expiry_hours(
                    self._classify_memory_type(
                        metadata,
                        self._calculate_importance_score(memory_content, metadata),
                    ),
                    self._calculate_importance_score(memory_content, metadata),
                ),
            )

            return {
                "status": "success",
                "session": session_id,
                "namespace": namespace,
                "content_length": len(str(memory_content)),
                "backend": "redisstack",
                "vector_enabled": True,
                "memory_key": memory_key,
            }

        except Exception as e:
            logger.error(f"Error writing to memory: {e}")
            return {"status": "error", "error": str(e)}

    def _extract_memory_content(self, context: Dict[str, Any]) -> str:
        """Extract structured memory content from validation guardian output."""
        try:
            # Look for structured memory object from validation guardian
            previous_outputs = context.get("previous_outputs", {})

            # Try validation guardians (both true and false)
            for guardian_name in ["false_validation_guardian", "true_validation_guardian"]:
                if guardian_name in previous_outputs:
                    guardian_output = previous_outputs[guardian_name]
                    if isinstance(guardian_output, dict) and "result" in guardian_output:
                        result = guardian_output["result"]
                        if isinstance(result, dict) and "memory_object" in result:
                            memory_obj = result["memory_object"]
                            # Convert structured object to searchable text
                            return self._memory_object_to_text(memory_obj, context.get("input", ""))

            # Fallback: use raw input if no structured memory object found
            return context.get("input", "")

        except Exception as e:
            logger.warning(f"Error extracting memory content: {e}")
            return context.get("input", "")

    def _memory_object_to_text(self, memory_obj: Dict[str, Any], original_input: str) -> str:
        """Convert structured memory object to searchable text format."""
        try:
            # Create a natural language representation that's searchable
            number = memory_obj.get("number", original_input)
            result = memory_obj.get("result", "unknown")
            condition = memory_obj.get("condition", "")
            analysis_type = memory_obj.get("analysis_type", "")
            confidence = memory_obj.get("confidence", 1.0)

            # Format as searchable text
            text_parts = [
                f"Number: {number}",
                f"Greater than 5: {result}",
                f"Condition: {condition}",
                f"Analysis: {analysis_type}",
                f"Confidence: {confidence}",
                f"Validated: {memory_obj.get('validation_status', 'unknown')}",
            ]

            # Add the structured data as JSON for exact matching
            structured_text = " | ".join(text_parts)
            structured_text += f" | JSON: {memory_obj}"

            return structured_text

        except Exception as e:
            logger.warning(f"Error converting memory object to text: {e}")
            return str(memory_obj)

    def _calculate_importance_score(self, content: str, metadata: Dict[str, Any]) -> float:
        """Calculate importance score for memory retention decisions."""
        score = 0.5  # Base score

        # Content length bonus (longer content often more important)
        if len(content) > 500:
            score += 0.2
        elif len(content) > 100:
            score += 0.1

        # Metadata indicators
        if metadata.get("category") == "stored":
            score += 0.3  # Explicitly stored memories are more important

        # Query presence (memories with queries are often more important)
        if metadata.get("query"):
            score += 0.1

        # Clamp score between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    def _classify_memory_type(self, metadata: Dict[str, Any], importance_score: float) -> str:
        """Classify memory as short-term or long-term based on metadata and importance."""
        # Stored memories with high importance are long-term
        if metadata.get("category") == "stored" and importance_score >= 0.7:
            return "long_term"

        # Agent-specific configuration
        if self.decay_config.get("default_long_term", False):
            return "long_term"

        return "short_term"

    def _get_expiry_hours(self, memory_type: str, importance_score: float) -> float:
        """Get expiry time in hours based on memory type and importance."""
        if memory_type == "long_term":
            # Check agent-level config first, then fall back to global config
            base_hours = self.decay_config.get("long_term_hours") or self.decay_config.get(
                "default_long_term_hours",
                24.0,
            )
        else:
            # Check agent-level config first, then fall back to global config
            base_hours = self.decay_config.get("short_term_hours") or self.decay_config.get(
                "default_short_term_hours",
                1.0,
            )

        # Adjust based on importance (higher importance = longer retention)
        importance_multiplier = 1.0 + importance_score
        return base_hours * importance_multiplier
