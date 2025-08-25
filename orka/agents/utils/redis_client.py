import redis


def get_redis_client():
    """Get a Redis client instance."""
    return redis.Redis(host="localhost", port=6380, db=0)
