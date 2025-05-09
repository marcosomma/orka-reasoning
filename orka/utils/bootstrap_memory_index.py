import redis.asyncio as redis
import asyncio

async def ensure_memory_index(client: redis.Redis):
    """Ensure the memory index exists in Redis Search."""
    try:
        await client.ft("memory_idx").info()
    except redis.ResponseError:
        await client.ft("memory_idx").create_index(
            (
                redis.commands.search.field.TextField("content"),
                redis.commands.search.field.TagField("session"),
                redis.commands.search.field.TagField("agent"),
                redis.commands.search.field.NumericField("ts"),
                redis.commands.search.field.VectorField(
                    "vector", "FLAT", {
                        "TYPE": "FLOAT32",
                        "DIM": 384,
                        "DISTANCE_METRIC": "COSINE"
                    }
                )
            ),
            definition=redis.commands.search.IndexDefinition(
                prefix=["mem:"],
                index_type="HASH"
            )
        )

async def retry(coro, attempts=3, backoff=0.2):
    """Retry a coroutine with exponential backoff."""
    for i in range(attempts):
        try:
            return await coro
        except redis.ConnectionError:
            if i == attempts - 1:
                raise
            await asyncio.sleep(backoff * (2 ** i)) 