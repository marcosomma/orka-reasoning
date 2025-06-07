import json
import logging
import os
import re
from typing import Any, Dict

import redis.asyncio as redis

from ..utils.bootstrap_memory_index import retry
from ..utils.embedder import from_bytes, get_embedder
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryReaderNode(BaseNode):
    """Node for reading from memory stream with semantic search capabilities."""

    def __init__(self, node_id: str, prompt: str = None, queue: list = None, **kwargs):
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.limit = kwargs.get("limit", 10)
        self.namespace = kwargs.get("namespace", "default")
        self.similarity_threshold = kwargs.get("similarity_threshold", 0.6)
        self.embedding_model = kwargs.get("embedding_model", None)

        # Use environment variable for Redis URL
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=False)
        self.embedder = get_embedder(self.embedding_model)
        self.type = "memoryreadernode"  # Used for agent type identification

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Read relevant memories from storage based on semantic similarity."""
        query = context.get("input", "")
        original_query = query
        session_id = context.get("session_id", "default")
        namespace = context.get("namespace", self.namespace)

        logger.info(f"Reading memories for query: '{query}' in namespace: {namespace}")

        # Create a stream key that includes the namespace
        stream_key = f"orka:memory:{namespace}:{session_id}"

        try:
            # For debugging - List all keys in memory to see what's available
            all_keys = await retry(self.redis.keys("*"))
            logger.info(f"Available keys in Redis: {all_keys}")

            # Get recent memory streams to check for content
            stream_keys = await retry(self.redis.keys("orka:memory:*"))
            logger.info(f"Memory stream keys: {stream_keys}")

            # Get all vector memory keys
            vector_keys = await retry(self.redis.keys("mem:*"))
            logger.info(f"Vector memory keys: {vector_keys}")

            # Use a very low similarity threshold for better recall
            effective_threshold = self.similarity_threshold * 0.5
            logger.info(f"Using similarity threshold: {effective_threshold}")

            # Generate query variations to increase chances of finding matches
            query_variations = self._generate_query_variations(query)
            logger.info(f"Generated query variations: {query_variations}")

            memories = []

            # Try all query variations one by one
            for variation in query_variations:
                logger.info(f"Trying query variation: '{variation}'")

                # Get query embedding for semantic search
                try:
                    query_embedding = await self.embedder.encode(variation)
                    logger.info(f"Successfully encoded query: '{variation}'")
                except Exception as e:
                    logger.error(f"Error encoding query '{variation}': {str(e)}")
                    continue

                # Try vector search first
                variation_memories = await self._vector_search(
                    query_embedding, namespace, threshold=effective_threshold
                )
                logger.info(
                    f"Vector search returned {len(variation_memories)} results for '{variation}'"
                )
                memories.extend(variation_memories)

                # Try simple keyword search
                keyword_memories = await self._keyword_search(namespace, variation)
                logger.info(
                    f"Keyword search returned {len(keyword_memories)} results for '{variation}'"
                )
                memories.extend(keyword_memories)

                # Try stream search
                stream_memories = await self._stream_search(
                    stream_key,
                    variation,
                    query_embedding,
                    threshold=effective_threshold,
                )
                logger.info(
                    f"Stream search returned {len(stream_memories)} results for '{variation}'"
                )
                memories.extend(stream_memories)

                # If we found memories with this variation, don't keep trying others
                if memories:
                    logger.info(
                        f"Found memories with variation '{variation}', stopping search"
                    )
                    break

            # If still no memories, try a broader search across all streams
            if not memories:
                logger.info(
                    "No memories found in the specified namespace, trying all streams"
                )
                for key in stream_keys:
                    decoded_key = key.decode() if isinstance(key, bytes) else key
                    if decoded_key != stream_key:
                        logger.info(f"Searching in alternative stream: {decoded_key}")
                        try:
                            query_embedding = await self.embedder.encode(original_query)
                            stream_memories = await self._stream_search(
                                decoded_key,
                                original_query,
                                query_embedding,
                                threshold=effective_threshold
                                * 0.5,  # Even lower threshold for cross-stream search
                            )
                            if stream_memories:
                                logger.info(
                                    f"Found {len(stream_memories)} memories in alternative stream"
                                )
                                memories.extend(stream_memories)
                        except Exception as e:
                            logger.error(
                                f"Error searching alternative stream: {str(e)}"
                            )

            # Deduplicate memories based on content
            unique_memories = []
            seen_contents = set()
            for memory in memories:
                if memory["content"] not in seen_contents:
                    seen_contents.add(memory["content"])
                    unique_memories.append(memory)

            logger.info(f"After deduplication: {len(unique_memories)} unique memories")
            memories = unique_memories

            # Filter memories by content relevance to query (with relaxed matching)
            filtered_memories = self._filter_relevant_memories(memories, original_query)
            logger.info(f"After filtering: {len(filtered_memories)} relevant memories")

            if not filtered_memories and memories:
                logger.warning(
                    "No relevant memories found after filtering. Using all retrieved memories."
                )
                filtered_memories = memories

            logger.info(
                f"Found {len(filtered_memories)} relevant memories for query: '{original_query}'"
            )

        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            filtered_memories = []

        # Return NONE if no memories found
        if not filtered_memories:
            logger.warning(f"No memories found for query: '{original_query}'")
            return {"status": "success", "memories": "NONE"}

        # Store result in context
        result = {
            "status": "success",
            "memories": filtered_memories,
        }

        context.setdefault("outputs", {})[self.node_id] = result
        return result

    def _generate_query_variations(self, query):
        """Generate variations of a query to increase chances of finding matching memories."""
        variations = [query]

        # Clean up query first
        cleaned_query = re.sub(r"[^\w\s]", "", query).lower().strip()
        if cleaned_query != query.lower().strip():
            variations.append(cleaned_query)

        # Add variations with different formulations
        if "when did" in query.lower():
            # For questions about when something happened
            entity = re.sub(r"^when did ", "", query.lower())
            variations.append(f"{entity} history")
            variations.append(f"{entity} timeline")
            variations.append(f"{entity} date")
            variations.append(f"{entity} began")
            variations.append(f"{entity} start")
            variations.append(f"{entity} origin")

        # For questions about what something is
        if "what is" in query.lower():
            entity = re.sub(r"^what is ", "", query.lower())
            variations.append(entity)
            variations.append(f"{entity} definition")
            variations.append(f"{entity} classification")

        # For questions about how something works
        if "how does" in query.lower():
            entity = re.sub(r"^how does ", "", query.lower())
            variations.append(entity)
            variations.append(f"{entity} mechanism")
            variations.append(f"{entity} process")

        # Add keywords only variation
        keywords = [word for word in query.lower().split() if len(word) > 3]
        if keywords:
            variations.append(" ".join(keywords))

        # Remove duplicates while preserving order
        unique_variations = []
        for v in variations:
            if v not in unique_variations:
                unique_variations.append(v)

        return unique_variations

    async def _keyword_search(self, namespace, query):
        """Search for memories using simple keyword matching."""
        results = []
        try:
            # Get all vector memory keys
            keys = await retry(self.redis.keys("mem:*"))

            # Extract query keywords (words longer than 3 characters)
            query_words = set([w.lower() for w in query.split() if len(w) > 3])

            # If no substantial keywords, use all words
            if not query_words:
                query_words = set(query.lower().split())

            for key in keys:
                try:
                    # Check if this memory belongs to our namespace
                    ns = await retry(self.redis.hget(key, "namespace"))
                    if ns and ns.decode() == namespace:
                        # Get the content
                        content = await retry(self.redis.hget(key, "content"))
                        if content:
                            content_str = (
                                content.decode()
                                if isinstance(content, bytes)
                                else content
                            )
                            content_words = set(content_str.lower().split())

                            # Calculate simple word overlap
                            overlap = len(query_words.intersection(content_words))
                            if overlap > 0:
                                # Get metadata if available
                                metadata_raw = await retry(
                                    self.redis.hget(key, "metadata")
                                )
                                metadata = {}
                                if metadata_raw:
                                    try:
                                        metadata_str = (
                                            metadata_raw.decode()
                                            if isinstance(metadata_raw, bytes)
                                            else metadata_raw
                                        )
                                        metadata = json.loads(metadata_str)
                                    except:
                                        pass

                                # Add to results
                                results.append(
                                    {
                                        "id": key.decode()
                                        if isinstance(key, bytes)
                                        else key,
                                        "content": content_str,
                                        "metadata": metadata,
                                        "similarity": overlap / len(query_words),
                                        "match_type": "keyword",
                                    }
                                )
                except Exception as e:
                    logger.error(
                        f"Error processing key {key} in keyword search: {str(e)}"
                    )

            # Sort by similarity
            results.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top results
            return results[: self.limit]

        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return []

    async def _vector_search(self, query_embedding, namespace, threshold=None):
        """Search for memories using vector similarity."""
        threshold = threshold or self.similarity_threshold
        results = []

        try:
            # Get all vector memory keys
            keys = await retry(self.redis.keys("mem:*"))
            logger.info(f"Searching through {len(keys)} vector memory keys")

            for key in keys:
                try:
                    # Check if this memory belongs to our namespace
                    ns = await retry(self.redis.hget(key, "namespace"))
                    if ns and ns.decode() == namespace:
                        # Get the vector
                        vector_bytes = await retry(self.redis.hget(key, "vector"))
                        if vector_bytes:
                            # Convert bytes to vector
                            vector = from_bytes(vector_bytes)
                            # Calculate similarity
                            similarity = self._cosine_similarity(
                                query_embedding, vector
                            )

                            if similarity >= threshold:
                                # Get content and metadata
                                content = await retry(self.redis.hget(key, "content"))
                                content_str = (
                                    content.decode()
                                    if isinstance(content, bytes)
                                    else content
                                )

                                metadata_raw = await retry(
                                    self.redis.hget(key, "metadata")
                                )
                                metadata = {}
                                if metadata_raw:
                                    try:
                                        metadata_str = (
                                            metadata_raw.decode()
                                            if isinstance(metadata_raw, bytes)
                                            else metadata_raw
                                        )
                                        metadata = json.loads(metadata_str)
                                    except:
                                        pass

                                # Add to results
                                results.append(
                                    {
                                        "id": key.decode()
                                        if isinstance(key, bytes)
                                        else key,
                                        "content": content_str,
                                        "metadata": metadata,
                                        "similarity": float(similarity),
                                        "match_type": "vector",
                                    }
                                )
                except Exception as e:
                    logger.error(
                        f"Error processing key {key} in vector search: {str(e)}"
                    )

            # Sort by similarity
            results.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top results
            return results[: self.limit]

        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []

    async def _stream_search(self, stream_key, query, query_embedding, threshold=None):
        """Search for memories in the Redis stream."""
        threshold = threshold or self.similarity_threshold

        try:
            # Get all entries
            entries = await retry(self.redis.xrange(stream_key))
            memories = []

            for entry_id, data in entries:
                try:
                    # Parse the payload
                    payload_str = (
                        data.get(b"payload", b"{}").decode()
                        if isinstance(data.get(b"payload"), bytes)
                        else data.get("payload", "{}")
                    )
                    payload = json.loads(payload_str)
                    content = payload.get("content", "")

                    # Skip empty content
                    if not content:
                        continue

                    # Simple keyword matching for efficiency
                    query_lower = query.lower()
                    content_lower = content.lower()

                    # If we have a keyword match, skip vector similarity calculation
                    keyword_match = False
                    if query_lower in content_lower:
                        keyword_match = True
                        similarity = 1.0  # High similarity for exact matches
                    else:
                        # Extract query keywords (words longer than 3 characters)
                        query_words = set(
                            [w for w in query_lower.split() if len(w) > 3]
                        )
                        # If no substantial keywords, use all words
                        if not query_words:
                            query_words = set(query_lower.split())

                        content_words = set(content_lower.split())
                        common_words = query_words.intersection(content_words)
                        if common_words:
                            keyword_match = True
                            # Pseudo-similarity based on word overlap
                            similarity = len(common_words) / max(len(query_words), 1)
                        else:
                            # Only compute embeddings if no keyword match
                            # Get embedding for content and calculate similarity
                            try:
                                content_embedding = await self.embedder.encode(content)
                                similarity = self._cosine_similarity(
                                    query_embedding, content_embedding
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error encoding content for similarity: {str(e)}"
                                )
                                similarity = 0

                    # Only include if similarity is above threshold
                    if keyword_match or similarity >= threshold:
                        # Get metadata from payload
                        metadata = payload.get("metadata", {})

                        # Get timestamp
                        ts = (
                            int(data.get(b"ts", 0))
                            if isinstance(data.get(b"ts"), bytes)
                            else int(data.get("ts", 0))
                        )

                        # Decode entry_id if needed
                        entry_id_str = (
                            entry_id.decode()
                            if isinstance(entry_id, bytes)
                            else entry_id
                        )

                        memories.append(
                            {
                                "id": entry_id_str,
                                "content": content,
                                "metadata": metadata,
                                "similarity": float(similarity),
                                "ts": ts,
                                "match_type": "stream",
                                "stream_key": stream_key,
                            }
                        )
                except Exception as e:
                    logger.error(f"Error processing stream entry {entry_id}: {str(e)}")

            # Sort by similarity
            memories.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top results
            return memories[: self.limit]

        except Exception as e:
            logger.error(f"Error in stream search: {str(e)}")
            return []

    def _filter_relevant_memories(self, memories, query):
        """Filter memories by relevance to the query."""
        # With relaxed matching, we consider memories relevant if:
        # 1. They have high similarity scores
        # 2. Or they contain query keywords
        query_keywords = set([w.lower() for w in query.split() if len(w) > 3])
        if not query_keywords:
            query_keywords = set(query.lower().split())

        filtered = []
        for memory in memories:
            # Accept high similarity memories
            if memory.get("similarity", 0) >= 0.3:  # Very low threshold for acceptance
                filtered.append(memory)
                continue

            # Check for keyword presence
            content_lower = memory.get("content", "").lower()
            content_words = set(content_lower.split())
            if query_keywords.intersection(content_words):
                filtered.append(memory)
                continue

            # Check if direct substrings match
            for keyword in query_keywords:
                if len(keyword) > 3 and keyword in content_lower:
                    filtered.append(memory)
                    break

        # Sort by similarity
        filtered.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return filtered

    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors."""
        try:
            import numpy as np

            # Convert to numpy arrays
            if not isinstance(vec1, np.ndarray):
                vec1 = np.array(vec1)
            if not isinstance(vec2, np.ndarray):
                vec2 = np.array(vec2)

            # Ensure vectors have the same shape
            if vec1.shape != vec2.shape:
                logger.warning(
                    f"Vector shapes do not match: {vec1.shape} vs {vec2.shape}"
                )
                # If different shapes, can't compute similarity
                return 0

            # Calculate cosine similarity
            dot = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            # Check for zero division
            if norm1 == 0 or norm2 == 0:
                return 0

            return dot / (norm1 * norm2)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0
