import redis

def get_redis_client():
    """Get a Redis client instance."""
    return redis.Redis(host='localhost', port=6379, db=0) 