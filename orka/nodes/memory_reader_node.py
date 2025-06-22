import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from ..utils.bootstrap_memory_index import retry
from ..utils.embedder import from_bytes, get_embedder
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class MemoryReaderNode(BaseNode):
    """Node for reading from memory stream with context-aware semantic search capabilities."""

    def __init__(self, node_id: str, prompt: str = None, queue: list = None, **kwargs):
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.limit = kwargs.get("limit", 10)
        self.namespace = kwargs.get("namespace", "default")
        self.similarity_threshold = kwargs.get("similarity_threshold", 0.6)
        self.embedding_model = kwargs.get("embedding_model")

        # Enhanced search configuration
        self.context_weight = kwargs.get(
            "context_weight",
            0.3,
        )  # Weight for context-based similarity
        self.temporal_weight = kwargs.get("temporal_weight", 0.2)  # Weight for temporal relevance
        self.enable_context_search = kwargs.get("enable_context_search", True)
        self.enable_temporal_ranking = kwargs.get("enable_temporal_ranking", True)
        self.context_window_size = kwargs.get(
            "context_window_size",
            5,
        )  # Number of recent interactions to consider
        self.temporal_decay_hours = kwargs.get(
            "temporal_decay_hours",
            24,
        )  # Hours for temporal decay

        # Memory category filtering - disabled by default for backward compatibility
        # Set to "stored" if you want to only retrieve stored memories and filter out logs
        self.memory_category_filter = kwargs.get("memory_category_filter")

        # Store agent-level decay configuration
        self.decay_config = kwargs.get("decay_config", {})

        # Use environment variable for Redis URL
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=False)
        self.embedder = get_embedder(self.embedding_model)
        self.type = "memoryreadernode"  # Used for agent type identification

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Read relevant memories from storage based on context-aware semantic similarity."""
        query = context.get("input", "")
        original_query = query
        session_id = context.get("session_id", "default")
        namespace = context.get("namespace", self.namespace)

        # Extract conversation context for context-aware search
        conversation_context = self._extract_conversation_context(context)

        logger.info(f"Reading memories for query: '{query}' in namespace: {namespace}")
        if conversation_context:
            logger.info(f"Using conversation context: {len(conversation_context)} items")

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

            # Generate enhanced query variations with context
            query_variations = self._generate_enhanced_query_variations(query, conversation_context)
            logger.info(f"Generated enhanced query variations: {query_variations}")

            memories = []

            # Try all query variations one by one
            for variation in query_variations:
                logger.info(f"Trying query variation: '{variation}'")

                # Get query embedding for semantic search
                try:
                    query_embedding = await self.embedder.encode(variation)
                    logger.info(f"Successfully encoded query: '{variation}'")
                except Exception as e:
                    logger.error(f"Error encoding query '{variation}': {e!s}")
                    continue

                # Try context-aware vector search first
                variation_memories = await self._context_aware_vector_search(
                    query_embedding,
                    namespace,
                    conversation_context,
                    threshold=effective_threshold,
                )
                logger.info(
                    f"Context-aware vector search returned {len(variation_memories)} results for '{variation}'",
                )
                memories.extend(variation_memories)

                # Try enhanced keyword search with context
                keyword_memories = await self._enhanced_keyword_search(
                    namespace,
                    variation,
                    conversation_context,
                )
                logger.info(
                    f"Enhanced keyword search returned {len(keyword_memories)} results for '{variation}'",
                )
                memories.extend(keyword_memories)

                # Try context-aware stream search
                stream_memories = await self._context_aware_stream_search(
                    stream_key,
                    variation,
                    query_embedding,
                    conversation_context,
                    threshold=effective_threshold,
                )
                logger.info(
                    f"Context-aware stream search returned {len(stream_memories)} results for '{variation}'",
                )
                memories.extend(stream_memories)

                # If we found memories with this variation, don't keep trying others
                if memories:
                    logger.info(
                        f"Found memories with variation '{variation}', stopping search",
                    )
                    break

            # If still no memories, try a broader search across all streams
            if not memories:
                logger.info(
                    "No memories found in the specified namespace, trying all streams",
                )
                for key in stream_keys:
                    decoded_key = key.decode() if isinstance(key, bytes) else key
                    if decoded_key != stream_key:
                        logger.info(f"Searching in alternative stream: {decoded_key}")
                        try:
                            query_embedding = await self.embedder.encode(original_query)
                            stream_memories = await self._context_aware_stream_search(
                                decoded_key,
                                original_query,
                                query_embedding,
                                conversation_context,
                                threshold=effective_threshold
                                * 0.5,  # Even lower threshold for cross-stream search
                            )
                            if stream_memories:
                                logger.info(
                                    f"Found {len(stream_memories)} memories in alternative stream",
                                )
                                memories.extend(stream_memories)
                        except Exception as e:
                            logger.error(
                                f"Error searching alternative stream: {e!s}",
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

            # Apply hybrid similarity scoring
            scored_memories = self._apply_hybrid_scoring(
                memories,
                original_query,
                conversation_context,
            )
            logger.info(f"Applied hybrid scoring to {len(scored_memories)} memories")

            # Filter memories by enhanced relevance
            filtered_memories = self._filter_enhanced_relevant_memories(
                scored_memories,
                original_query,
                conversation_context,
            )
            logger.info(f"After enhanced filtering: {len(filtered_memories)} relevant memories")

            if not filtered_memories and memories:
                logger.warning(
                    "No relevant memories found after filtering. Using all retrieved memories.",
                )
                filtered_memories = memories

            logger.info(
                f"Found {len(filtered_memories)} relevant memories for query: '{original_query}'",
            )

        except Exception as e:
            logger.error(f"Error retrieving memories: {e!s}")
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

    def _extract_conversation_context(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract recent conversation context for context-aware search."""
        conversation_context = []

        # Extract from context history if available
        if "history" in context:
            history = context["history"]
            if isinstance(history, list):
                # Take recent items within context window
                recent_history = (
                    history[-self.context_window_size :]
                    if len(history) > self.context_window_size
                    else history
                )
                for item in recent_history:
                    if isinstance(item, dict) and "content" in item:
                        conversation_context.append(
                            {
                                "content": item["content"],
                                "timestamp": item.get("timestamp", time.time()),
                                "role": item.get("role", "unknown"),
                            },
                        )

        # Extract from previous outputs in context
        if "outputs" in context:
            outputs = context["outputs"]
            for node_id, output in outputs.items():
                if isinstance(output, dict) and "memories" in output:
                    memories = output["memories"]
                    if isinstance(memories, list):
                        for memory in memories[-3:]:  # Recent memories from previous nodes
                            if isinstance(memory, dict) and "content" in memory:
                                conversation_context.append(
                                    {
                                        "content": memory["content"],
                                        "timestamp": memory.get("ts", time.time()),
                                        "role": "memory",
                                    },
                                )

        return conversation_context

    def _generate_enhanced_query_variations(
        self,
        query: str,
        conversation_context: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate enhanced query variations using conversation context."""
        variations = self._generate_query_variations(query)  # Start with original variations

        if not conversation_context:
            return variations

        # Extract context keywords and entities
        context_keywords = set()
        context_entities = set()

        for ctx_item in conversation_context:
            content = ctx_item.get("content", "").lower()
            words = [w for w in content.split() if len(w) > 3]
            context_keywords.update(words[:5])  # Top 5 keywords per context item

            # Simple entity extraction (capitalized words)
            entities = re.findall(r"\b[A-Z][a-z]+\b", ctx_item.get("content", ""))
            context_entities.update(entities[:3])  # Top 3 entities per context item

        # Generate context-enhanced variations
        query_lower = query.lower()
        # Sort keywords to ensure deterministic ordering
        sorted_keywords = sorted(list(context_keywords))[:5]  # Limit to avoid too many variations
        for keyword in sorted_keywords:
            if keyword not in query_lower:
                variations.append(f"{query} {keyword}")
                variations.append(f"{keyword} {query}")

        for entity in list(context_entities)[:3]:
            if entity.lower() not in query_lower:
                variations.append(f"{query} related to {entity}")

        # Remove duplicates while preserving order
        unique_variations = []
        for v in variations:
            if v not in unique_variations:
                unique_variations.append(v)

        return unique_variations[:10]  # Limit to prevent too many API calls

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
            # Clean up punctuation from entity
            clean_entity = re.sub(r"[^\w\s]", "", entity).strip()
            if clean_entity:
                variations.append(clean_entity)
                variations.append(f"{clean_entity} definition")
                variations.append(f"{clean_entity} classification")

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

    async def _enhanced_keyword_search(
        self,
        namespace: str,
        query: str,
        conversation_context: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Enhanced keyword search that considers conversation context."""
        results = []
        try:
            # Get all vector memory keys
            keys = await retry(self.redis.keys("mem:*"))

            # Extract query keywords (words longer than 3 characters)
            query_words = set([w.lower() for w in query.split() if len(w) > 3])

            # If no substantial keywords, use all words
            if not query_words:
                query_words = set(query.lower().split())

            # Extract context keywords
            context_words = set()
            for ctx_item in conversation_context:
                content_words = [
                    w.lower() for w in ctx_item.get("content", "").split() if len(w) > 3
                ]
                context_words.update(content_words[:5])  # Top 5 words per context item

            for key in keys:
                try:
                    # Check if this memory belongs to our namespace
                    ns = await retry(self.redis.hget(key, "namespace"))
                    if ns and ns.decode() == namespace:
                        # Get the content
                        content = await retry(self.redis.hget(key, "content"))
                        if content:
                            content_str = (
                                content.decode() if isinstance(content, bytes) else content
                            )
                            content_words = set(content_str.lower().split())

                            # Calculate enhanced word overlap (query + context)
                            query_overlap = len(query_words.intersection(content_words))
                            context_overlap = (
                                len(context_words.intersection(content_words))
                                if context_words
                                else 0
                            )

                            # Combined similarity score
                            total_overlap = query_overlap + (context_overlap * self.context_weight)

                            if total_overlap > 0:
                                # Get metadata if available
                                metadata_raw = await retry(
                                    self.redis.hget(key, "metadata"),
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

                                # Calculate enhanced similarity
                                # Base similarity from query overlap
                                base_similarity = query_overlap / max(len(query_words), 1)

                                # Context bonus (scaled by context weight)
                                context_bonus = 0
                                if context_words and context_overlap > 0:
                                    context_bonus = (
                                        context_overlap / max(len(context_words), 1)
                                    ) * self.context_weight

                                # Combined similarity with context bonus
                                similarity = base_similarity + context_bonus

                                # Add to results
                                results.append(
                                    {
                                        "id": key.decode() if isinstance(key, bytes) else key,
                                        "content": content_str,
                                        "metadata": metadata,
                                        "similarity": similarity,
                                        "match_type": "enhanced_keyword",
                                        "query_overlap": query_overlap,
                                        "context_overlap": context_overlap,
                                    },
                                )
                except Exception as e:
                    logger.error(
                        f"Error processing key {key} in enhanced keyword search: {e!s}",
                    )

            # Sort by similarity
            results.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top results
            return results[: self.limit]

        except Exception as e:
            logger.error(f"Error in enhanced keyword search: {e!s}")
            return []

    async def _context_aware_vector_search(
        self,
        query_embedding,
        namespace: str,
        conversation_context: List[Dict[str, Any]],
        threshold=None,
    ) -> List[Dict[str, Any]]:
        """Context-aware vector search using conversation context."""
        threshold = threshold or self.similarity_threshold
        results = []

        try:
            # Generate context vector if context is available
            context_vector = None
            if conversation_context and self.enable_context_search:
                context_vector = await self._generate_context_vector(conversation_context)

            # Get all vector memory keys
            keys = await retry(self.redis.keys("mem:*"))
            logger.info(f"Searching through {len(keys)} vector memory keys with context awareness")

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

                            # Calculate primary similarity (query vs memory)
                            primary_similarity = self._cosine_similarity(query_embedding, vector)

                            # Calculate context similarity if available
                            context_similarity = 0
                            if context_vector is not None:
                                context_similarity = self._cosine_similarity(context_vector, vector)

                            # Combined similarity score
                            combined_similarity = primary_similarity + (
                                context_similarity * self.context_weight
                            )

                            if combined_similarity >= threshold:
                                # Get content and metadata
                                content = await retry(self.redis.hget(key, "content"))
                                content_str = (
                                    content.decode() if isinstance(content, bytes) else content
                                )

                                metadata_raw = await retry(
                                    self.redis.hget(key, "metadata"),
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
                                        "id": key.decode() if isinstance(key, bytes) else key,
                                        "content": content_str,
                                        "metadata": metadata,
                                        "similarity": float(combined_similarity),
                                        "primary_similarity": float(primary_similarity),
                                        "context_similarity": float(context_similarity),
                                        "match_type": "context_aware_vector",
                                    },
                                )
                except Exception as e:
                    logger.error(
                        f"Error processing key {key} in context-aware vector search: {e!s}",
                    )

            # Sort by combined similarity
            results.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top results
            return results[: self.limit]

        except Exception as e:
            logger.error(f"Error in context-aware vector search: {e!s}")
            return []

    async def _generate_context_vector(
        self,
        conversation_context: List[Dict[str, Any]],
    ) -> Optional[List[float]]:
        """Generate a context vector from conversation history."""
        if not conversation_context:
            return None

        try:
            # Combine recent context into a single text
            context_texts = []
            for ctx_item in conversation_context:
                content = ctx_item.get("content", "").strip()
                if content:
                    context_texts.append(content)

            if not context_texts:
                return None

            # Join and encode context
            combined_context = " ".join(context_texts[-3:])  # Use only the most recent 3 items
            context_vector = await self.embedder.encode(combined_context)
            return context_vector

        except Exception as e:
            logger.error(f"Error generating context vector: {e!s}")
            return None

    async def _context_aware_stream_search(
        self,
        stream_key: str,
        query: str,
        query_embedding,
        conversation_context: List[Dict[str, Any]],
        threshold=None,
    ) -> List[Dict[str, Any]]:
        """Context-aware search for memories in the Redis stream."""
        threshold = threshold or self.similarity_threshold

        try:
            # Generate context vector if available
            context_vector = None
            if conversation_context and self.enable_context_search:
                context_vector = await self._generate_context_vector(conversation_context)

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

                    # Check for direct keyword matches first
                    keyword_match = False
                    primary_similarity = 0

                    if query_lower in content_lower:
                        keyword_match = True
                        primary_similarity = 1.0  # High similarity for exact matches
                    else:
                        # Extract query keywords (words longer than 3 characters)
                        query_words = set([w for w in query_lower.split() if len(w) > 3])
                        if not query_words:
                            query_words = set(query_lower.split())

                        content_words = set(content_lower.split())
                        common_words = query_words.intersection(content_words)
                        if common_words:
                            keyword_match = True
                            primary_similarity = len(common_words) / max(len(query_words), 1)
                        else:
                            # Compute vector similarity
                            try:
                                content_embedding = await self.embedder.encode(content)
                                primary_similarity = self._cosine_similarity(
                                    query_embedding,
                                    content_embedding,
                                )
                            except Exception as e:
                                logger.error(f"Error encoding content for similarity: {e!s}")
                                primary_similarity = 0

                    # Calculate context similarity if available
                    context_similarity = 0
                    if context_vector is not None and not keyword_match:
                        try:
                            content_embedding = await self.embedder.encode(content)
                            context_similarity = self._cosine_similarity(
                                context_vector,
                                content_embedding,
                            )
                        except Exception as e:
                            logger.error(f"Error calculating context similarity: {e!s}")
                            context_similarity = 0

                    # Combined similarity
                    combined_similarity = primary_similarity + (
                        context_similarity * self.context_weight
                    )

                    # Only include if similarity is above threshold
                    if keyword_match or combined_similarity >= threshold:
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
                            entry_id.decode() if isinstance(entry_id, bytes) else entry_id
                        )

                        memories.append(
                            {
                                "id": entry_id_str,
                                "content": content,
                                "metadata": metadata,
                                "similarity": float(combined_similarity),
                                "primary_similarity": float(primary_similarity),
                                "context_similarity": float(context_similarity),
                                "ts": ts,
                                "match_type": "context_aware_stream",
                                "stream_key": stream_key,
                            },
                        )
                except Exception as e:
                    logger.error(f"Error processing stream entry {entry_id}: {e!s}")

            # Sort by combined similarity
            memories.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top results
            return memories[: self.limit]

        except Exception as e:
            logger.error(f"Error in context-aware stream search: {e!s}")
            return []

    def _apply_hybrid_scoring(
        self,
        memories: List[Dict[str, Any]],
        query: str,
        conversation_context: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Apply hybrid scoring combining semantic, keyword, context, and temporal factors."""
        current_time = time.time()

        for memory in memories:
            # Base similarity score
            base_similarity = memory.get("similarity", 0)

            # Temporal score (if enabled and timestamp available)
            temporal_score = 0
            if self.enable_temporal_ranking:
                memory_ts = memory.get("ts", 0)
                if memory_ts > 0:
                    # Convert to seconds if it's in milliseconds/nanoseconds
                    if memory_ts > 1e15:  # Likely nanoseconds (much higher threshold)
                        memory_ts = memory_ts / 1e9
                    elif memory_ts > 1e9:  # Likely milliseconds (current time ~1.75e12)
                        memory_ts = memory_ts / 1e3

                    # Calculate time difference in hours
                    time_diff_hours = (current_time - memory_ts) / 3600

                    # Ensure non-negative time difference
                    time_diff_hours = max(0, time_diff_hours)

                    # Apply exponential decay
                    if time_diff_hours < self.temporal_decay_hours:
                        temporal_score = max(0, 1 - (time_diff_hours / self.temporal_decay_hours))
                    else:
                        # Give very small score to older memories
                        temporal_score = 0.01

            # Context relevance score (already computed in context-aware searches)
            context_score = memory.get("context_similarity", 0)

            # Keyword match bonus
            keyword_bonus = 0
            query_lower = query.lower()
            content_lower = memory.get("content", "").lower()
            if query_lower in content_lower:
                keyword_bonus = 0.2  # Bonus for exact substring match

            # Calculate final hybrid score
            hybrid_score = (
                base_similarity * 0.5  # 50% base similarity
                + context_score * self.context_weight  # Context weight (default 30%)
                + temporal_score * self.temporal_weight  # Temporal weight (default 20%)
                + keyword_bonus  # Keyword bonus
            )

            memory["hybrid_score"] = hybrid_score
            memory["temporal_score"] = temporal_score
            memory["keyword_bonus"] = keyword_bonus

        # Sort by hybrid score
        memories.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
        return memories

    def _filter_enhanced_relevant_memories(
        self,
        memories: List[Dict[str, Any]],
        query: str,
        conversation_context: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Filter memories by enhanced relevance criteria including category filtering.

        Args:
            memories: List of memory objects
            query: Original query
            conversation_context: Conversation context for relevance scoring

        Returns:
            List of filtered memory objects
        """
        if not memories:
            return []

        filtered_memories = []

        for memory in memories:
            try:
                # Category-based filtering - only include stored memories for retrieval
                if self.memory_category_filter:
                    memory_category = memory.get("metadata", {}).get("category", "unknown")

                    # For backward compatibility, if category is unknown/unset, treat as "stored"
                    # This ensures existing memories without category field can still be retrieved
                    if memory_category == "unknown":
                        memory_category = "stored"

                    if memory_category != self.memory_category_filter:
                        logger.debug(
                            f"Filtered out {memory_category} memory, keeping only {self.memory_category_filter}",
                        )
                        continue

                # Enhanced relevance scoring
                content = memory.get("content", "")
                similarity = memory.get("similarity", 0.0)

                # Basic relevance check
                if similarity < self.similarity_threshold * 0.3:  # Very low threshold for recall
                    continue

                # Content relevance check
                query_words = set(query.lower().split())
                content_words = set(content.lower().split())
                word_overlap = len(query_words.intersection(content_words))

                # Context relevance check
                context_relevance = 0.0
                if conversation_context:
                    for ctx_item in conversation_context:
                        ctx_content = ctx_item.get("content", "")
                        if ctx_content:
                            ctx_words = set(ctx_content.lower().split())
                            ctx_overlap = len(content_words.intersection(ctx_words))
                            context_relevance += ctx_overlap / max(len(ctx_words), 1)

                # Combined relevance score
                combined_relevance = (
                    similarity * 0.5  # Semantic similarity
                    + (word_overlap / max(len(query_words), 1)) * 0.3  # Query overlap
                    + context_relevance * 0.2  # Context relevance
                )

                # Apply enhanced filtering
                if combined_relevance >= 0.1:  # Low threshold for high recall
                    memory["combined_relevance"] = combined_relevance
                    filtered_memories.append(memory)

            except Exception as e:
                logger.error(f"Error filtering memory: {e!s}")
                # Include memory on error to be safe
                filtered_memories.append(memory)

        # Sort by combined relevance if available, otherwise by similarity
        filtered_memories.sort(
            key=lambda x: x.get("combined_relevance", x.get("similarity", 0.0)),
            reverse=True,
        )

        return filtered_memories[: self.limit]

    def _filter_by_category(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter memories by category to separate stored memories from orchestration logs.

        Args:
            memories: List of memory objects

        Returns:
            List of filtered memory objects matching the category filter
        """
        if not self.memory_category_filter or not memories:
            return memories

        filtered_memories = []

        for memory in memories:
            try:
                # Check memory category in metadata or direct field
                memory_category = memory.get("metadata", {}).get("category", "unknown")

                # Also check direct category field for backward compatibility
                if memory_category == "unknown":
                    memory_category = memory.get("category", "unknown")

                # For backward compatibility, if category is still unknown/unset, treat as "stored"
                # This ensures existing memories without category field can still be retrieved
                if memory_category == "unknown":
                    memory_category = "stored"

                # Apply category filter
                if memory_category == self.memory_category_filter:
                    filtered_memories.append(memory)
                    logger.debug(
                        f"Included {memory_category} memory matching filter {self.memory_category_filter}",
                    )
                else:
                    logger.debug(
                        f"Filtered out {memory_category} memory, keeping only {self.memory_category_filter}",
                    )

            except Exception as e:
                logger.error(f"Error checking memory category: {e!s}")
                # Include memory on error to be safe
                filtered_memories.append(memory)

        return filtered_memories

    async def _keyword_search(self, namespace, query):
        """Search for memories using simple keyword matching."""
        # This method is kept for backward compatibility
        # Enhanced version is _enhanced_keyword_search
        return await self._enhanced_keyword_search(namespace, query, [])

    async def _vector_search(self, query_embedding, namespace, threshold=None):
        """Search for memories using vector similarity."""
        # This method is kept for backward compatibility
        # Enhanced version is _context_aware_vector_search
        return await self._context_aware_vector_search(query_embedding, namespace, [], threshold)

    async def _stream_search(self, stream_key, query, query_embedding, threshold=None):
        """Search for memories in the Redis stream."""
        # This method is kept for backward compatibility
        # Enhanced version is _context_aware_stream_search
        return await self._context_aware_stream_search(
            stream_key,
            query,
            query_embedding,
            [],
            threshold,
        )

    def _filter_relevant_memories(self, memories, query):
        """Filter memories by relevance to the query."""
        # This method is kept for backward compatibility
        # Enhanced version is _filter_enhanced_relevant_memories
        return self._filter_enhanced_relevant_memories(memories, query, [])

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
                    f"Vector shapes do not match: {vec1.shape} vs {vec2.shape}",
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
            logger.error(f"Error calculating cosine similarity: {e!s}")
            return 0
