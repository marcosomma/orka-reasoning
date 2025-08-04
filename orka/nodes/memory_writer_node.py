import logging
from typing import Any

from jinja2 import Template

from ..memory_logger import create_memory_logger
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryWriterNode(BaseNode):
    """Enhanced memory writer using RedisStack through memory logger."""

    def __init__(self, node_id: str, **kwargs: Any) -> None:
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

        # Store key_template for rendering
        self.key_template = kwargs.get("key_template")

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write to memory using RedisStack memory logger."""
        try:
            # Extract structured memory object from validation guardian
            memory_content = self._extract_memory_content(context)
            if not memory_content:
                return {"status": "error", "error": "No memory content to store"}
            logger.info(
                f"[DEBUG] - MemoryWriterNode: Extracted memory content: {memory_content[:200]}..."
            )  # Log first 200 chars

            # Extract configuration from context
            namespace = context.get("namespace", self.namespace)
            session_id = context.get("session_id", self.session_id)

            # Merge metadata from YAML config and context
            merged_metadata = self._merge_metadata(context)

            # Process key_template if present
            if self.key_template:
                try:
                    # Create template context for key rendering (optimized - exclude previous_outputs)
                    template_context = {
                        "input": context.get("input", ""),
                        "timestamp": context.get("timestamp", ""),
                        # ✅ FIX: Exclude previous_outputs to reduce memory bloat
                        # Include only essential context keys
                        "run_id": context.get("run_id", ""),
                        "session_id": context.get("session_id", ""),
                        "namespace": context.get("namespace", ""),
                    }

                    # Apply same enhancement as in template rendering
                    if "input" in context and isinstance(context["input"], dict):
                        input_data = context["input"]
                        if "loop_number" in input_data:
                            template_context["loop_number"] = input_data["loop_number"]
                        if "input" in input_data:
                            template_context["original_input"] = input_data["input"]

                    # Render the key template
                    from jinja2 import Template

                    template = Template(self.key_template)
                    rendered_key = template.render(**template_context)

                    # Store rendered key in metadata for identification
                    merged_metadata["memory_key_template"] = str(rendered_key)

                except Exception as e:
                    logger.warning(f"Failed to render key template: {e}")
                    merged_metadata["memory_key_template"] = self.key_template

            # Use memory logger for direct memory storage
            # ✅ FIX: Filter out previous_outputs from merged metadata
            filtered_merged_metadata = {
                k: v for k, v in merged_metadata.items() if k != "previous_outputs"
            }

            final_metadata = {
                "namespace": namespace,
                "session": session_id,
                "content_type": "user_input",
                **filtered_merged_metadata,  # Include filtered metadata only
                # Set these AFTER merged_metadata to prevent overwriting
                "category": str(merged_metadata.get("category", "stored")),
                "log_type": "memory",  # Mark as stored memory, not orchestration log
                "tags": ", ".join(merged_metadata.get("tags", [])),
            }

            assert self.memory_logger is not None, "Memory logger not initialized"
            memory_key = self.memory_logger.log_memory(
                content=memory_content,
                node_id=self.node_id,
                trace_id=session_id,
                metadata=final_metadata,
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
                "stored_metadata": final_metadata,
            }

        except Exception as e:
            logger.error(f"Error writing to memory: {e}")
            return {"status": "error", "error": str(e)}

    def _merge_metadata(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge metadata from YAML config, context, and guardian outputs."""
        try:
            # Start with YAML metadata structure (always preserve this)
            merged_metadata = self.yaml_metadata.copy()

            # Render YAML metadata templates first
            rendered_yaml_metadata = self._render_metadata_templates(merged_metadata, context)

            # Add context metadata (overrides YAML where keys conflict)
            # ✅ FIX: Filter out previous_outputs to reduce memory bloat
            context_metadata = context.get("metadata", {})
            # Remove previous_outputs if present in context metadata
            filtered_context_metadata = {
                k: v for k, v in context_metadata.items() if k != "previous_outputs"
            }
            rendered_yaml_metadata.update(filtered_context_metadata)

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
            # Ensure we return a dict[str, Any] by copying and casting
            metadata_copy = dict(self.yaml_metadata)
            return {str(k): v for k, v in metadata_copy.items()}

    def _render_metadata_templates(
        self,
        metadata: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Render Jinja2 templates in metadata using context data."""
        try:
            rendered_metadata = {}

            # Create optimized template context (exclude previous_outputs to reduce memory bloat)
            template_context = {
                "input": context.get("input", ""),
                "timestamp": context.get("timestamp", ""),
                "now": lambda: context.get("timestamp", ""),  # now() function for templates
                # ✅ FIX: Include only essential context keys, exclude previous_outputs
                "run_id": context.get("run_id", ""),
                "session_id": context.get("session_id", ""),
                "namespace": context.get("namespace", ""),
                "agent_id": context.get("agent_id", ""),
            }

            # Expose key properties from input object at root level for template access
            if "input" in context and isinstance(context["input"], dict):
                input_data = context["input"]

                # Expose loop_number at root level (templates expect {{ loop_number }})
                if "loop_number" in input_data:
                    template_context["loop_number"] = input_data["loop_number"]

                # Expose past_loops_metadata at root level
                if "past_loops_metadata" in input_data:
                    template_context["past_loops_metadata"] = input_data["past_loops_metadata"]

                # Expose the original input content at root level
                if "input" in input_data:
                    template_context["original_input"] = input_data["input"]

            # Add helper functions for template use (same as prompt rendering)
            template_context.update(self._get_template_helper_functions(template_context))

            # Ensure timestamp is always available
            if not template_context.get("timestamp"):
                import datetime

                template_context["timestamp"] = datetime.datetime.now().isoformat()

            # Process metadata templates
            for key, value in metadata.items():
                try:
                    if isinstance(value, str) and ("{{" in value or "{%" in value):
                        # Render string templates
                        try:
                            template = Template(value)
                            rendered_value = template.render(**template_context)

                            # Handle special cases where rendered value might be None or empty
                            if rendered_value is None or rendered_value == "":
                                # Try to extract default value from template if present
                                if "default(" in value:
                                    # Use original template string as fallback
                                    rendered_metadata[key] = value
                                    logger.warning(
                                        f"Template rendered empty, using default for '{key}'",
                                    )
                                else:
                                    rendered_metadata[key] = ""
                                    logger.warning(f"Template rendered empty for '{key}'")
                            else:
                                rendered_metadata[key] = rendered_value

                        except Exception as template_error:
                            logger.error(
                                f"Template render error for key '{key}': {template_error}",
                            )
                            # Use original value if template fails
                            rendered_metadata[key] = str(value)

                    elif isinstance(value, dict):
                        # Recursively render nested dictionaries
                        rendered_metadata[key] = str(
                            self._render_metadata_templates(value, context)
                        )
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
                                    logger.warning(f"Error rendering list item template: {e}")
                                    rendered_list.append(str(item))
                            else:
                                rendered_list.append(item)
                        rendered_metadata[key] = str(rendered_list)
                    else:
                        # Keep non-template values as-is
                        rendered_metadata[key] = value

                except Exception as e:
                    logger.error(f"Error processing metadata key '{key}': {e}")
                    # Keep original value if rendering fails, but ensure it's not a slice
                    if hasattr(value, "__getitem__") and not isinstance(value, (str, list, dict)):
                        rendered_metadata[key] = str(value)
                    else:
                        rendered_metadata[key] = value

            return rendered_metadata

        except Exception as e:
            logger.error(f"Error rendering metadata templates: {e}")
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
                            return str(
                                self._memory_object_to_text(memory_obj, context.get("input", ""))
                            )

            # Try to get the rendered prompt first, then fall back to raw input
            content = context.get("formatted_prompt", "")
            if not content:
                # Extract clean string content from nested input structure
                input_value = context.get("input", "")

                # If input is a complex nested structure, extract the actual string content
                if isinstance(input_value, dict):
                    # Look for the actual input string in the nested structure
                    if "input" in input_value:
                        actual_input = input_value["input"]
                        if isinstance(actual_input, str):
                            return actual_input
                        else:
                            return str(actual_input)
                    else:
                        # Try to create a meaningful string representation
                        return f"Complex input structure with keys: {list(input_value.keys())}"
                elif isinstance(input_value, str):
                    return input_value
                else:
                    return str(input_value)
            else:
                return str(content)

        except Exception as e:
            logger.error(f"❌ Error extracting memory content: {e}")
            import traceback

            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            # Safe fallback - return a simple string
            return "Memory content extraction failed"

    def _memory_object_to_text(self, memory_obj: dict[str, Any], original_input: str) -> str:
        """Convert structured memory object to searchable text format."""
        try:
            # Create a natural language representation that's searchable
            number = str(memory_obj.get("number", original_input))
            result = str(memory_obj.get("result", "unknown"))
            condition = str(memory_obj.get("condition", ""))
            analysis_type = str(memory_obj.get("analysis_type", ""))
            confidence = str(memory_obj.get("confidence", 1.0))

            # Format as searchable text
            text_parts = [
                f"Number: {number}",
                f"Greater than 5: {result}",
                f"Condition: {condition}",
                f"Analysis: {analysis_type}",
                f"Confidence: {confidence}",
                f"Validated: {str(memory_obj.get('validation_status', 'unknown'))}",
            ]

            # Add the structured data as JSON for exact matching
            structured_text = " | ".join(text_parts)
            structured_text += f" | JSON: {str(memory_obj)}"

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
            base_hours = float(
                self.decay_config.get("long_term_hours")
                or self.decay_config.get(
                    "default_long_term_hours",
                    24.0,
                )
            )
        else:
            # Check agent-level config first, then fall back to global config
            base_hours = float(
                self.decay_config.get("short_term_hours")
                or self.decay_config.get(
                    "default_short_term_hours",
                    1.0,
                )
            )

        # Adjust based on importance (higher importance = longer retention)
        importance_multiplier = 1.0 + importance_score
        return float(base_hours * importance_multiplier)

    def _get_template_helper_functions(self, payload):
        """
        Create helper functions available in Jinja2 templates for easier variable access.

        These functions provide a cleaner, more maintainable way to access complex
        nested data structures in YAML workflow templates.

        Returns:
            dict: Dictionary of helper functions for template context
        """

        def get_input():
            """Get the main input string, handling nested input structures."""
            if "input" in payload:
                input_data = payload["input"]
                if isinstance(input_data, dict):
                    return input_data.get("input", str(input_data))
                return str(input_data)
            return ""

        def get_loop_number():
            """Get the current loop number."""
            if "loop_number" in payload:
                return payload["loop_number"]
            if "input" in payload and isinstance(payload["input"], dict):
                return payload["input"].get("loop_number", 1)
            return 1

        def has_past_loops():
            """Check if there are past loops available."""
            past_loops = get_past_loops()
            return len(past_loops) > 0

        def get_past_loops():
            """Get the past loops list."""
            if "input" in payload and isinstance(payload["input"], dict):
                prev_outputs = payload["input"].get("previous_outputs", {})
                return prev_outputs.get("past_loops", [])
            return []

        def get_past_insights():
            """Get insights from the last past loop."""
            past_loops = get_past_loops()
            if past_loops:
                last_loop = past_loops[-1]
                return last_loop.get("synthesis_insights", "No synthesis insights found")
            return "No synthesis insights found"

        def get_past_loop_data(key):
            """Get specific data from the last past loop."""
            past_loops = get_past_loops()
            if past_loops:
                last_loop = past_loops[-1]
                return last_loop.get(key, f"No {key} found")
            return f"No {key} found"

        def get_agent_response(agent_name):
            """Get an agent's response from previous_outputs."""
            previous_outputs = payload.get("previous_outputs", {})
            agent_result = previous_outputs.get(agent_name, {})

            if isinstance(agent_result, dict):
                return agent_result.get("response", f"No response from {agent_name}")
            return str(agent_result)

        def format_memory_query(perspective, topic=None):
            """Format a memory query for a specific perspective."""
            if topic is None:
                topic = get_input()
            return f"{perspective.title()} perspective on: {topic}"

        def get_current_topic():
            """Get the current topic being discussed."""
            return get_input()

        def get_round_info():
            """Get formatted round information for display."""
            loop_num = get_loop_number()
            if has_past_loops():
                last_loop = get_past_loops()[-1]
                return last_loop.get("round", str(loop_num))
            return str(loop_num)

        def safe_get(obj, key, default=""):
            """Safely get a value from an object with a default."""
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        def joined_results():
            """Get joined results from fork operations if available."""
            previous_outputs = payload.get("previous_outputs", {})
            for agent_name, agent_result in previous_outputs.items():
                if isinstance(agent_result, dict) and "joined_results" in agent_result:
                    return agent_result["joined_results"]
            return []

        return {
            # Input helpers
            "get_input": get_input,
            "get_current_topic": get_current_topic,
            # Loop helpers
            "get_loop_number": get_loop_number,
            "has_past_loops": has_past_loops,
            "get_past_loops": get_past_loops,
            "get_past_insights": get_past_insights,
            "get_past_loop_data": get_past_loop_data,
            "get_round_info": get_round_info,
            # Agent helpers
            "get_agent_response": get_agent_response,
            "joined_results": joined_results,
            # Memory helpers
            "format_memory_query": format_memory_query,
            # Utility helpers
            "safe_get": safe_get,
        }
