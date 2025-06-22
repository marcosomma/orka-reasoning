import json
import logging
import os
import time
from typing import Any, Dict

import redis.asyncio as redis

from ..utils.bootstrap_memory_index import retry
from ..utils.embedder import get_embedder, to_bytes
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryWriterNode(BaseNode):
    """Node for writing to memory stream and optionally vector store."""

    def __init__(self, node_id: str, prompt: str = None, queue: list = None, **kwargs):
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.vector_enabled = kwargs.get(
            "vector",
            True,
        )  # Enable vector storage by default
        self.namespace = kwargs.get("namespace", "default")
        self.key_template = kwargs.get("key_template", "")
        self.metadata = kwargs.get("metadata", {})

        # Store agent-level decay configuration
        self.decay_config = kwargs.get("decay_config", {})

        # Store memory logger for decay-aware logging
        self.memory_logger = kwargs.get("memory_logger")

        # Initialize embedder if vector storage is enabled
        try:
            self.embedder = (
                get_embedder(kwargs.get("embedding_model")) if self.vector_enabled else None
            )
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e!s}")
            self.embedder = None
            # Still try to initialize a fallback embedder if possible
            try:
                self.embedder = get_embedder(None)  # Try with default model
                self.vector_enabled = True
                logger.info(
                    "Initialized fallback embedder after primary embedder failed",
                )
            except Exception as e2:
                logger.error(f"Failed to initialize fallback embedder: {e2!s}")
                self.vector_enabled = False

        # Use environment variable for Redis URL
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=False)
        self.type = "memorywriternode"  # Used for agent type identification

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Write to memory stream and optionally vector store."""
        try:
            # Get required content
            text = context.get("input", "")
            if not text:
                logger.warning("Empty text provided for memory storage")
                # Try to get content from prompt if input is empty
                if self.prompt and "{{" in self.prompt and "}}" in self.prompt:
                    # Extract value from previous_outputs based on prompt template
                    from jinja2 import Template

                    try:
                        template = Template(self.prompt)
                        text = template.render(**context)
                        logger.info(
                            f"Resolved text from prompt template: {text[:100]}...",
                        )
                    except Exception as e:
                        logger.error(f"Error processing prompt template: {e!s}")

                # If still no text, try common output fields
                if not text and context.get("previous_outputs"):
                    common_output_fields = [
                        "synthesize_timeline_answer",
                        "answer",
                        "output",
                        "result",
                        "response",
                    ]
                    for field in common_output_fields:
                        if field in context["previous_outputs"]:
                            text = context["previous_outputs"][field]
                            logger.info(f"Using {field} as content: {text[:100]}...")
                            break

            if not text:
                logger.error("Unable to find content to store in memory")
                return {
                    "status": "error",
                    "error": "No content available to store in memory",
                }

            session_id = context.get("session_id", "default")
            namespace = context.get("namespace", self.namespace)

            # Prepare metadata with any template variables resolved
            metadata = self.metadata.copy() if self.metadata else {}
            if isinstance(metadata, dict):
                # Process any template variables in metadata
                for key, value in metadata.items():
                    if isinstance(value, str) and "{{" in value and "}}" in value:
                        try:
                            # Try to extract from previous_outputs using Jinja2
                            from jinja2 import Template

                            template = Template(value)
                            resolved_value = template.render(**context)
                            metadata[key] = resolved_value
                            logger.info(
                                f"Resolved metadata variable {key}={resolved_value}",
                            )
                        except Exception as e:
                            logger.error(
                                f"Error resolving metadata template {key}: {e!s}",
                            )
                            # Fallback: direct extraction from previous_outputs
                            if "previous_outputs." in value:
                                var_path = value.strip("{} ").split(".", 1)[1]
                                if (
                                    "previous_outputs" in context
                                    and var_path in context["previous_outputs"]
                                ):
                                    metadata[key] = context["previous_outputs"][var_path]
                                    logger.info(
                                        f"Fallback resolved metadata variable {key}={metadata[key]}",
                                    )

            # Add additional metadata for better retrieval
            metadata["timestamp"] = time.time()
            metadata["agent_id"] = self.node_id
            if "input" in context:
                metadata["query"] = context["input"]

            # Set memory category to "stored" for memory writer nodes
            metadata["category"] = "stored"

            # Use key_template if provided
            entry_key = None
            if self.key_template:
                try:
                    from jinja2 import Template

                    template = Template(self.key_template)
                    entry_key = template.render(**context)
                    logger.info(f"Generated key from template: {entry_key}")
                except Exception as e:
                    logger.error(f"Error processing key template: {e!s}")

            # If no key template or error, use a timestamp-based key
            if not entry_key:
                entry_key = str(time.time_ns())
                logger.info(f"Using timestamp-based key: {entry_key}")

            logger.info(f"Writing memory in namespace '{namespace}': {text[:100]}...")

            # Define stream_key for use in both paths
            stream_key = f"orka:memory:{namespace}:{session_id}"

            # Use memory logger if available (for decay-aware logging)
            if self.memory_logger:
                # Use the memory logger for decay-aware storage
                self.memory_logger.log(
                    agent_id=self.node_id,
                    event_type="write",
                    payload={
                        "content": text,
                        "metadata": metadata,
                        "query": context.get("input", ""),
                        "timestamp": time.time(),
                        "key": entry_key,
                        "namespace": namespace,
                        "session": session_id,
                    },
                    run_id=session_id,
                    agent_decay_config=self.decay_config,
                )
                entry_id = f"memory_logger_{time.time_ns()}"  # Placeholder ID for memory logger
                logger.info(f"Written to memory logger with entry: {entry_id}")
            else:
                # Fallback to direct Redis stream writing (legacy behavior)
                # Prepare stream entry with more detailed metadata
                entry = {
                    "ts": str(time.time_ns()),
                    "agent_id": self.node_id,
                    "type": "memory.append",
                    "session": session_id,
                    "payload": json.dumps(
                        {
                            "content": text,
                            "metadata": metadata,
                            "query": context.get("input", ""),
                            "timestamp": time.time(),
                            "key": entry_key,
                        },
                    ),
                }

                # Write to stream with retry
                entry_id = await retry(self.redis.xadd(stream_key, entry))
                logger.info(f"Written to stream: {stream_key} with entry ID: {entry_id}")

                # Verify the stream entry was written successfully
                try:
                    last_entry = await retry(
                        self.redis.xrevrange(stream_key, "+", "-", count=1),
                    )
                    if last_entry:
                        last_id, last_data = last_entry[0]
                        logger.info(f"Verified write: Last entry ID: {last_id}")
                        payload = (
                            last_data.get(b"payload", b"{}").decode()
                            if isinstance(last_data.get(b"payload"), bytes)
                            else last_data.get("payload", "{}")
                        )
                        logger.info(
                            f"Verified write: Last entry payload sample: {payload[:50]}...",
                        )
                    else:
                        logger.warning(
                            f"Could not verify stream write - no entries in {stream_key}",
                        )
                except Exception as e:
                    logger.error(f"Error verifying stream write: {e!s}")

            # Optionally write to vector store
            doc_id = None
            if self.vector_enabled and self.embedder:
                try:
                    # Try to generate an embedding for the text
                    try:
                        vector = await self.embedder.encode(text)
                    except Exception as e:
                        logger.error(
                            f"Failed to encode text for vector storage: {e!s}",
                        )
                        # Use fallback method
                        try:
                            from ..utils.embedder import AsyncEmbedder

                            fallback_embedder = AsyncEmbedder(None)
                            vector = await fallback_embedder.encode(text)
                            logger.info("Successfully generated fallback embedding")
                        except Exception as e2:
                            logger.error(f"Fallback embedding also failed: {e2!s}")
                            raise e2

                    doc_id = f"mem:{namespace}:{int(time.time() * 1e6)}"

                    # Store vector data in Redis
                    await retry(self.redis.hset(doc_id, "content", text))
                    await retry(self.redis.hset(doc_id, "vector", to_bytes(vector)))
                    await retry(self.redis.hset(doc_id, "session", session_id))
                    await retry(self.redis.hset(doc_id, "namespace", namespace))
                    await retry(self.redis.hset(doc_id, "agent", self.node_id))
                    await retry(self.redis.hset(doc_id, "key", entry_key))
                    await retry(
                        self.redis.hset(doc_id, "ts", str(int(time.time() * 1e3))),
                    )

                    # Store enhanced metadata
                    enhanced_metadata = metadata.copy()
                    enhanced_metadata.update(
                        {
                            "query": context.get("input", ""),
                            "timestamp": time.time(),
                            "stream_entry_id": entry_id.decode()
                            if isinstance(entry_id, bytes)
                            else entry_id,
                        },
                    )

                    await retry(
                        self.redis.hset(
                            doc_id,
                            "metadata",
                            json.dumps(enhanced_metadata),
                        ),
                    )
                    logger.info(f"Written to vector store with ID: {doc_id}")

                    # Verify the vector was stored correctly
                    stored_vector = await retry(self.redis.hget(doc_id, "vector"))
                    if stored_vector:
                        logger.info(
                            f"Vector successfully stored with length {len(stored_vector)} bytes",
                        )
                    else:
                        logger.warning("Vector was not stored correctly")

                    # Verify content was stored correctly
                    stored_content = await retry(self.redis.hget(doc_id, "content"))
                    if stored_content:
                        content_str = (
                            stored_content.decode()
                            if isinstance(stored_content, bytes)
                            else stored_content
                        )
                        logger.info(
                            f"Content successfully stored: {content_str[:50]}...",
                        )
                    else:
                        logger.warning("Content was not stored correctly")

                except Exception as e:
                    logger.error(f"Failed to store vector embedding: {e!s}")

            # Store result in context
            result = {
                "status": "success",
                "session": session_id,
                "namespace": namespace,
                "stream_key": stream_key,
                "entry_id": entry_id,
            }

            if doc_id:
                result["vector_id"] = doc_id

            context.setdefault("outputs", {})[self.node_id] = result
            return result

        except Exception as e:
            logger.error(f"Error writing to memory: {e!s}")
            error_result = {
                "status": "error",
                "error": str(e),
            }
            context.setdefault("outputs", {})[self.node_id] = error_result
            return error_result
