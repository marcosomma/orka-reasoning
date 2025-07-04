import logging
from typing import Any

from jinja2 import Template

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

        # ✅ CRITICAL: Always store metadata structure defined in YAML
        self.yaml_metadata = kwargs.get("metadata", {})

        # Remove direct Redis client - use memory logger instead
        # self.redis = redis.from_url(...)  # ← REMOVE

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write to memory using RedisStack memory logger."""
        try:
            # 🔍 DEBUG: Log the complete context structure
            logger.info(f"MemoryWriterNode received context keys: {list(context.keys())}")
            if "previous_outputs" in context:
                logger.info(f"Previous outputs keys: {list(context['previous_outputs'].keys())}")
                # Log structure of a few key outputs
                for key in ["logic_reasoning", "empathy_reasoning", "moderator_synthesis"]:
                    if key in context["previous_outputs"]:
                        output = context["previous_outputs"][key]
                        logger.info(
                            f"Structure of {key}: {type(output)} with keys: {list(output.keys()) if isinstance(output, dict) else 'not a dict'}",
                        )
                        if isinstance(output, dict) and "result" in output:
                            result = output["result"]
                            logger.info(
                                f"  Result structure: {type(result)} with keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}",
                            )

            # Log the YAML metadata we're trying to render
            logger.info(f"YAML metadata to render: {self.yaml_metadata}")

            # 🎯 CRITICAL FIX: Extract structured memory object from validation guardian
            memory_content = self._extract_memory_content(context)
            if not memory_content:
                return {"status": "error", "error": "No memory content to store"}

            # Extract configuration from context
            namespace = context.get("namespace", self.namespace)
            session_id = context.get("session_id", self.session_id)

            # ✅ CRITICAL: Always merge metadata from YAML config and context
            merged_metadata = self._merge_metadata(context)

            # 🔍 DEBUG: Log the final merged metadata
            logger.info(f"Final merged metadata: {merged_metadata}")

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
                    **merged_metadata,  # Include all metadata from YAML and context
                },
                importance_score=self._calculate_importance_score(memory_content, merged_metadata),
                memory_type=self._classify_memory_type(
                    merged_metadata,
                    self._calculate_importance_score(memory_content, merged_metadata),
                ),
                expiry_hours=self._get_expiry_hours(
                    self._classify_memory_type(
                        merged_metadata,
                        self._calculate_importance_score(memory_content, merged_metadata),
                    ),
                    self._calculate_importance_score(memory_content, merged_metadata),
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
                "stored_metadata": merged_metadata,  # Include metadata in response
            }

        except Exception as e:
            logger.error(f"Error writing to memory: {e}")
            return {"status": "error", "error": str(e)}

    def _merge_metadata(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge metadata from YAML config, context, and guardian outputs."""
        try:
            # Start with YAML metadata structure (always preserve this)
            merged_metadata = self.yaml_metadata.copy()

            # ✅ CRITICAL: Render YAML metadata templates first
            rendered_yaml_metadata = self._render_metadata_templates(merged_metadata, context)

            # Add context metadata (overrides YAML where keys conflict)
            context_metadata = context.get("metadata", {})
            rendered_yaml_metadata.update(context_metadata)

            # Extract metadata from guardian outputs if present
            guardian_metadata = self._extract_guardian_metadata(context)
            if guardian_metadata:
                rendered_yaml_metadata.update(guardian_metadata)

            # Extract structured memory object metadata if present
            memory_object_metadata = self._extract_memory_object_metadata(context)
            if memory_object_metadata:
                rendered_yaml_metadata.update(memory_object_metadata)

            return rendered_yaml_metadata

        except Exception as e:
            logger.warning(f"Error merging metadata: {e}")
            return self.yaml_metadata.copy()

    def _render_metadata_templates(
        self,
        metadata: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Render Jinja2 templates in metadata using context data."""
        try:
            rendered_metadata = {}

            # Create comprehensive template context
            template_context = {
                "input": context.get("input", ""),
                "previous_outputs": context.get("previous_outputs", {}),
                "timestamp": context.get("timestamp", ""),
                "now": lambda: context.get("timestamp", ""),  # now() function for templates
                **context,  # Include all context keys
            }

            # Debug: Log template context structure
            logger.info(f"Template context keys: {list(template_context.keys())}")
            logger.info(
                f"Previous outputs keys: {list(template_context.get('previous_outputs', {}).keys())}",
            )

            # 🔍 DEBUG: Log specific structure that templates are trying to access
            prev_outputs = template_context.get("previous_outputs", {})
            for agent_key in ["logic_reasoning", "empathy_reasoning", "moderator_synthesis"]:
                if agent_key in prev_outputs:
                    agent_data = prev_outputs[agent_key]
                    logger.info(f"Agent {agent_key} structure: {type(agent_data)}")
                    if isinstance(agent_data, dict):
                        logger.info(f"  Keys: {list(agent_data.keys())}")
                        if "result" in agent_data:
                            result = agent_data["result"]
                            logger.info(f"  Result type: {type(result)}")
                            if isinstance(result, dict):
                                logger.info(f"  Result keys: {list(result.keys())}")

            for key, value in metadata.items():
                try:
                    if isinstance(value, str) and ("{{" in value or "{%" in value):
                        # Debug: Log what we're trying to render
                        logger.info(f"🎯 Rendering template for key '{key}': {value}")

                        # Render string templates with enhanced error handling
                        template = Template(value)
                        rendered_value = template.render(**template_context)

                        # Debug: Log the rendered result
                        logger.info(
                            f"✅ Rendered value for key '{key}': {rendered_value[:200]}{'...' if len(str(rendered_value)) > 200 else ''}",
                        )

                        # Handle special cases where rendered value might be None or empty
                        if rendered_value is None or rendered_value == "":
                            # Try to extract default value from template if present
                            if "default(" in value:
                                # Use original template string as fallback
                                rendered_metadata[key] = value
                                logger.warning(
                                    f"⚠️ Template rendered empty, using default for '{key}'",
                                )
                            else:
                                rendered_metadata[key] = ""
                                logger.warning(f"⚠️ Template rendered empty for '{key}'")
                        else:
                            rendered_metadata[key] = rendered_value

                    elif isinstance(value, dict):
                        # Recursively render nested dictionaries
                        rendered_metadata[key] = self._render_metadata_templates(value, context)
                    elif isinstance(value, list):
                        # Render templates in lists
                        rendered_list = []
                        for item in value:
                            if isinstance(item, str) and ("{{" in item or "{%" in item):
                                try:
                                    template = Template(item)
                                    rendered_item = template.render(**template_context)
                                    rendered_list.append(rendered_item)
                                except Exception as e:
                                    logger.warning(f"❌ Error rendering list item template: {e}")
                                    rendered_list.append(item)
                            else:
                                rendered_list.append(item)
                        rendered_metadata[key] = rendered_list
                    else:
                        # Keep non-template values as-is
                        rendered_metadata[key] = value

                except Exception as e:
                    logger.error(f"❌ Error rendering template for metadata key '{key}': {e}")
                    logger.error(f"Template value: {value}")
                    logger.error(f"Template context keys: {list(template_context.keys())}")
                    import traceback

                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    # Keep original value if rendering fails
                    rendered_metadata[key] = value

            return rendered_metadata

        except Exception as e:
            logger.error(f"❌ Error rendering metadata templates: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return metadata.copy()

    def _extract_guardian_metadata(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from validation guardian outputs."""
        try:
            guardian_metadata = {}
            previous_outputs = context.get("previous_outputs", {})

            # Check both validation guardians for metadata
            for guardian_name in ["false_validation_guardian", "true_validation_guardian"]:
                if guardian_name in previous_outputs:
                    guardian_output = previous_outputs[guardian_name]
                    if isinstance(guardian_output, dict):
                        # Extract metadata from guardian result
                        if "metadata" in guardian_output:
                            guardian_metadata.update(guardian_output["metadata"])

                        # Extract validation status
                        if "result" in guardian_output:
                            result = guardian_output["result"]
                            if isinstance(result, dict):
                                guardian_metadata["validation_guardian"] = guardian_name
                                guardian_metadata["validation_result"] = result.get(
                                    "validation_status",
                                    "unknown",
                                )

            return guardian_metadata

        except Exception as e:
            logger.warning(f"Error extracting guardian metadata: {e}")
            return {}

    def _extract_memory_object_metadata(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from structured memory objects."""
        try:
            memory_object_metadata = {}
            previous_outputs = context.get("previous_outputs", {})

            # Look for structured memory objects from guardians
            for guardian_name in ["false_validation_guardian", "true_validation_guardian"]:
                if guardian_name in previous_outputs:
                    guardian_output = previous_outputs[guardian_name]
                    if isinstance(guardian_output, dict) and "result" in guardian_output:
                        result = guardian_output["result"]
                        if isinstance(result, dict) and "memory_object" in result:
                            memory_obj = result["memory_object"]
                            if isinstance(memory_obj, dict):
                                # Extract structured fields as metadata
                                memory_object_metadata["structured_data"] = memory_obj
                                memory_object_metadata["analysis_type"] = memory_obj.get(
                                    "analysis_type",
                                    "unknown",
                                )
                                memory_object_metadata["confidence"] = memory_obj.get(
                                    "confidence",
                                    1.0,
                                )
                                memory_object_metadata["validation_status"] = memory_obj.get(
                                    "validation_status",
                                    "unknown",
                                )

            return memory_object_metadata

        except Exception as e:
            logger.warning(f"Error extracting memory object metadata: {e}")
            return {}

    def _extract_memory_content(self, context: dict[str, Any]) -> str:
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

    def _memory_object_to_text(self, memory_obj: dict[str, Any], original_input: str) -> str:
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

    def _calculate_importance_score(self, content: str, metadata: dict[str, Any]) -> float:
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

    def _classify_memory_type(self, metadata: dict[str, Any], importance_score: float) -> str:
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
