# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
# 
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

import os
import json
import redis
from datetime import datetime

class RedisMemoryLogger:
    """
    A memory logger that uses Redis to store and retrieve orchestration events.
    Supports logging events, saving logs to files, and querying recent events.
    """

    def __init__(self, redis_url=None, stream_key="orka:memory"):
        """
        Initialize the Redis memory logger.
        
        Args:
            redis_url (str, optional): URL for the Redis server. Defaults to environment variable REDIS_URL or redis service name.
            stream_key (str, optional): Key for the Redis stream. Defaults to "orka:memory".
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.stream_key = stream_key
        self.client = redis.from_url(self.redis_url)
        self.memory = []  # Local memory buffer for in-memory storage
    
    @property
    def redis(self):
        """Return the Redis client instance."""
        return self.client

    def log(self, agent_id, event_type, payload, step=None, run_id=None, fork_group=None, parent=None, previous_outputs=None):
        """
        Log an event to Redis and local memory.
        
        Args:
            agent_id (str): ID of the agent generating the event.
            event_type (str): Type of the event.
            payload (dict): Event payload.
            step (int, optional): Step number in the orchestration. Defaults to None.
            run_id (str, optional): ID of the orchestration run. Defaults to None.
            fork_group (str, optional): ID of the fork group. Defaults to None.
            parent (str, optional): ID of the parent event. Defaults to None.
            previous_outputs (dict, optional): Previous outputs from agents. Defaults to None.
        """
        event = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        if step is not None:
            event["step"] = step
        if run_id:
            event["run_id"] = run_id
        if fork_group:
            event["fork_group"] = fork_group
        if parent:
            event["parent"] = parent
        if previous_outputs:
            event["previous_outputs"] = previous_outputs

        self.memory.append(event)

        self.client.xadd(self.stream_key, {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": event["timestamp"],
            "payload": json.dumps(payload),
            "run_id": run_id or "default",
            "step": str(step or -1),
        })

    def save_to_file(self, file_path):
        """
        Save the logged events to a JSON file.
        
        Args:
            file_path (str): Path to the output JSON file.
        """
        with open(file_path, 'w') as f:
            json.dump(self.memory, f, indent=2)
        print(f"[MemoryLogger] Logs saved to {file_path}")

    def tail(self, count=10):
        """
        Retrieve the most recent events from the Redis stream.
        
        Args:
            count (int, optional): Number of events to retrieve. Defaults to 10.
        
        Returns:
            list: List of recent events.
        """
        return self.client.xrevrange(self.stream_key, count=count)
    
    def hset(self, name, key, value):
        """
        Set a field in a Redis hash.
        
        Args:
            name (str): Name of the hash.
            key (str): Field key.
            value (str): Field value.
        
        Returns:
            int: Number of fields added.
        """
        return self.client.hset(name, key, value)

    def hget(self, name, key):
        """
        Get a field from a Redis hash.
        
        Args:
            name (str): Name of the hash.
            key (str): Field key.
        
        Returns:
            str: Field value.
        """
        return self.client.hget(name, key)

    def hkeys(self, name):
        """
        Get all keys in a Redis hash.
        
        Args:
            name (str): Name of the hash.
        
        Returns:
            list: List of keys.
        """
        return self.client.hkeys(name)

    def hdel(self, name, *keys):
        """
        Delete fields from a Redis hash.
        
        Args:
            name (str): Name of the hash.
            *keys (str): Keys to delete.
        
        Returns:
            int: Number of fields deleted.
        """
        return self.client.hdel(name, *keys)
    
    def smembers(self, name):
        """
        Get all members of a Redis set.
        
        Args:
            name (str): Name of the set.
        
        Returns:
            set: Set of members.
        """
        return self.client.smembers(name)


# Future stub
class KafkaMemoryLogger:
    """
    A placeholder for a future Kafka-based memory logger.
    Raises NotImplementedError as it is not yet implemented.
    """
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Kafka backend not implemented yet")