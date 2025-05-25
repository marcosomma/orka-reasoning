import asyncio

import redis.asyncio as redis


async def delete_memories():
    # Connect to Redis
    r = redis.from_url("redis://localhost:6379", decode_responses=False)

    try:
        # Get all memory keys
        memory_keys = await r.keys("orka:memory:*")
        vector_keys = await r.keys("mem:*")

        print(
            f"Found {len(memory_keys)} memory streams and {len(vector_keys)} vector memories"
        )

        # Delete memory streams
        for key in memory_keys:
            await r.delete(key)
            print(
                f"Deleted memory stream: {key.decode() if isinstance(key, bytes) else key}"
            )

        # Delete vector memories
        for key in vector_keys:
            await r.delete(key)
            print(
                f"Deleted vector memory: {key.decode() if isinstance(key, bytes) else key}"
            )

        print("All memories have been deleted successfully!")

    except Exception as e:
        print(f"Error deleting memories: {str(e)}")
    finally:
        await r.close()


if __name__ == "__main__":
    asyncio.run(delete_memories())
