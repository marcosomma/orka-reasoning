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
import time

class ForkGroupManager:
    """
    Manages fork groups in the OrKa orchestrator.
    Handles the creation, tracking, and cleanup of fork groups for parallel execution.
    """

    def __init__(self, redis_client):
        """
        Initialize the fork group manager with a Redis client.
        
        Args:
            redis_client: The Redis client instance.
        """
        self.redis = redis_client

    def create_group(self, fork_group_id, agent_ids):
        """
        Create a new fork group with the given agent IDs.
        
        Args:
            fork_group_id (str): ID of the fork group.
            agent_ids (list): List of agent IDs to include in the group.
        """
        # Flatten any nested branch sequences (e.g., [[a, b, c], [x, y]])
        flat_ids = []
        for el in agent_ids:
            if isinstance(el, list):
                flat_ids.extend(el)
            else:
                flat_ids.append(el)
        self.redis.sadd(self._group_key(fork_group_id), *flat_ids)

    def mark_agent_done(self, fork_group_id, agent_id):
        """
        Mark an agent as done in the fork group.
        
        Args:
            fork_group_id (str): ID of the fork group.
            agent_id (str): ID of the agent to mark as done.
        """
        self.redis.srem(self._group_key(fork_group_id), agent_id)

    def is_group_done(self, fork_group_id):
        """
        Check if all agents in the fork group are done.
        
        Args:
            fork_group_id (str): ID of the fork group.
        
        Returns:
            bool: True if all agents are done, False otherwise.
        """
        return self.redis.scard(self._group_key(fork_group_id)) == 0

    def list_pending_agents(self, fork_group_id):
        """
        Get a list of agents still pending in the fork group.
        
        Args:
            fork_group_id (str): ID of the fork group.
        
        Returns:
            list: List of pending agent IDs.
        """
        pending = self.redis.smembers(self._group_key(fork_group_id))
        return [i.decode() if isinstance(i, bytes) else i for i in pending]

    def delete_group(self, fork_group_id):
        """
        Delete the fork group from Redis.
        
        Args:
            fork_group_id (str): ID of the fork group to delete.
        """
        self.redis.delete(self._group_key(fork_group_id))

    def generate_group_id(self, base_id):
        """
        Generate a unique fork group ID based on the base ID and timestamp.
        
        Args:
            base_id (str): Base ID for the fork group.
        
        Returns:
            str: A unique fork group ID.
        """
        return f"{base_id}_{int(time.time())}"

    def _group_key(self, fork_group_id):
        """
        Generate the Redis key for a fork group.
        
        Args:
            fork_group_id (str): ID of the fork group.
        
        Returns:
            str: The Redis key for the fork group.
        """
        return f"fork_group:{fork_group_id}"

    def _branch_seq_key(self, fork_group_id):
        """
        Generate the Redis key for a branch sequence.
        
        Args:
            fork_group_id (str): ID of the fork group.
        
        Returns:
            str: The Redis key for the branch sequence.
        """
        return f"fork_branch:{fork_group_id}"

    def track_branch_sequence(self, fork_group_id, agent_sequence):
        """
        Track the sequence of agents in a branch.
        
        Args:
            fork_group_id (str): ID of the fork group.
            agent_sequence (list): List of agent IDs in sequence.
        """
        for i in range(len(agent_sequence) - 1):
            current = agent_sequence[i]
            next_one = agent_sequence[i+1]
            self.redis.hset(self._branch_seq_key(fork_group_id), current, next_one)

    def next_in_sequence(self, fork_group_id, agent_id):
        """
        Get the next agent in the sequence after the current agent.
        
        Args:
            fork_group_id (str): ID of the fork group.
            agent_id (str): ID of the current agent.
        
        Returns:
            str: ID of the next agent, or None if there is no next agent.
        """
        next_one = self.redis.hget(self._branch_seq_key(fork_group_id), agent_id)
        if next_one:
            return next_one.decode() if isinstance(next_one, bytes) else next_one
        return None
