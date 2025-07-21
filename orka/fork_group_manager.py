# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Fork Group Manager
=================

The Fork Group Manager is responsible for coordinating parallel execution branches
in the OrKa orchestration framework. It provides functionality to create, track, and
manage groups of agents that need to run in parallel, with synchronization points
for gathering their results.

Primary responsibilities:
------------------------
1. Creating fork groups and registering agents within them
2. Tracking the completion status of parallel-executing agents
3. Determining when all branches of execution have completed
4. Managing the sequence of agents within each execution branch
5. Providing utilities for generating unique group IDs and Redis keys

This module enables complex workflow patterns like:
- Parallel processing of the same input with different agents
- Fan-out/fan-in patterns where work is distributed and then collected
- Sequential chains of agents within parallel branches
- Dynamic branching based on intermediate results

The implementation uses Redis as a coordination mechanism to ensure reliable
operation in distributed environments.
"""

import time
from typing import Any, Dict, List, Optional, Set, Union

from redis import Redis
from redis.client import Redis as RedisType


class ForkGroupManager:
    """
    Manages fork groups in the OrKa orchestrator.
    Handles the creation, tracking, and cleanup of fork groups for parallel execution.

    A fork group represents a set of agent execution paths that need to run in parallel
    and eventually be synchronized. This manager keeps track of which agents are part of
    each group and which ones have completed their execution.
    """

    def __init__(self, redis_client: RedisType) -> None:
        """
        Initialize the fork group manager with a Redis client.

        Args:
            redis_client: The Redis client instance.
        """
        self.redis = redis_client

    def create_group(self, fork_group_id: str, agent_ids: List[Union[str, List[str]]]) -> None:
        """
        Create a new fork group with the given agent IDs.

        Args:
            fork_group_id (str): ID of the fork group.
            agent_ids (list): List of agent IDs to include in the group.
        """
        # Flatten any nested branch sequences (e.g., [[a, b, c], [x, y]])
        flat_ids: List[str] = []
        for el in agent_ids:
            if isinstance(el, list):
                flat_ids.extend(el)
            else:
                flat_ids.append(el)
        self.redis.sadd(self._group_key(fork_group_id), *flat_ids)

    def mark_agent_done(self, fork_group_id: str, agent_id: str) -> None:
        """
        Mark an agent as done in the fork group.

        Args:
            fork_group_id (str): ID of the fork group.
            agent_id (str): ID of the agent to mark as done.
        """
        self.redis.srem(self._group_key(fork_group_id), agent_id)

    def is_group_done(self, fork_group_id: str) -> bool:
        """
        Check if all agents in the fork group are done.

        Args:
            fork_group_id (str): ID of the fork group.

        Returns:
            bool: True if all agents are done, False otherwise.
        """
        return self.redis.scard(self._group_key(fork_group_id)) == 0

    def list_pending_agents(self, fork_group_id: str) -> List[str]:
        """
        Get a list of agents still pending in the fork group.

        Args:
            fork_group_id (str): ID of the fork group.

        Returns:
            list: List of pending agent IDs.
        """
        pending = self.redis.smembers(self._group_key(fork_group_id))
        return [i.decode() if isinstance(i, bytes) else i for i in pending]

    def delete_group(self, fork_group_id: str) -> None:
        """
        Delete the fork group from Redis.

        Args:
            fork_group_id (str): ID of the fork group to delete.
        """
        self.redis.delete(self._group_key(fork_group_id))

    def generate_group_id(self, base_id: str) -> str:
        """
        Generate a unique fork group ID based on the base ID and timestamp.

        Args:
            base_id (str): Base ID for the fork group.

        Returns:
            str: A unique fork group ID.
        """
        return f"{base_id}_{int(time.time())}"

    def _group_key(self, fork_group_id: str) -> str:
        """
        Generate the Redis key for a fork group.

        Args:
            fork_group_id (str): ID of the fork group.

        Returns:
            str: The Redis key for the fork group.
        """
        return f"fork_group:{fork_group_id}"

    def _branch_seq_key(self, fork_group_id: str) -> str:
        """
        Generate the Redis key for a branch sequence.

        Args:
            fork_group_id (str): ID of the fork group.

        Returns:
            str: The Redis key for the branch sequence.
        """
        return f"fork_branch:{fork_group_id}"

    def track_branch_sequence(self, fork_group_id: str, agent_sequence: List[str]) -> None:
        """
        Track the sequence of agents in a branch.

        Args:
            fork_group_id (str): ID of the fork group.
            agent_sequence (list): List of agent IDs in sequence.
        """
        for i in range(len(agent_sequence) - 1):
            current = agent_sequence[i]
            next_one = agent_sequence[i + 1]
            self.redis.hset(self._branch_seq_key(fork_group_id), current, next_one)

    def next_in_sequence(self, fork_group_id: str, agent_id: str) -> Optional[str]:
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


class SimpleForkGroupManager:
    """
    A simple in-memory fork group manager for use with non-Redis backends like Kafka.
    Provides the same interface as ForkGroupManager but stores data in memory.

    Note: This implementation is not distributed and will not work across multiple
    orchestrator instances. Use only for single-instance deployments with Kafka.
    """

    def __init__(self) -> None:
        """Initialize the simple fork group manager with in-memory storage."""
        self._groups: Dict[str, Set[str]] = {}  # fork_group_id -> set of agent_ids
        self._branch_sequences: Dict[str, Dict[str, str]] = (
            {}
        )  # fork_group_id -> {agent_id -> next_agent_id}

    def create_group(self, fork_group_id: str, agent_ids: List[Union[str, List[str]]]) -> None:
        """
        Create a new fork group with the given agent IDs.

        Args:
            fork_group_id (str): ID of the fork group.
            agent_ids (list): List of agent IDs to include in the group.
        """
        # Flatten any nested branch sequences (e.g., [[a, b, c], [x, y]])
        flat_ids: List[str] = []
        for el in agent_ids:
            if isinstance(el, list):
                flat_ids.extend(el)
            else:
                flat_ids.append(el)
        self._groups[fork_group_id] = set(flat_ids)

    def mark_agent_done(self, fork_group_id: str, agent_id: str) -> None:
        """
        Mark an agent as done in the fork group.

        Args:
            fork_group_id (str): ID of the fork group.
            agent_id (str): ID of the agent to mark as done.
        """
        if fork_group_id in self._groups:
            self._groups[fork_group_id].discard(agent_id)

    def is_group_done(self, fork_group_id: str) -> bool:
        """
        Check if all agents in the fork group are done.

        Args:
            fork_group_id (str): ID of the fork group.

        Returns:
            bool: True if all agents are done, False otherwise.
        """
        if fork_group_id not in self._groups:
            return True
        return len(self._groups[fork_group_id]) == 0

    def list_pending_agents(self, fork_group_id: str) -> List[str]:
        """
        Get a list of agents still pending in the fork group.

        Args:
            fork_group_id (str): ID of the fork group.

        Returns:
            list: List of pending agent IDs.
        """
        if fork_group_id not in self._groups:
            return []
        return list(self._groups[fork_group_id])

    def delete_group(self, fork_group_id: str) -> None:
        """
        Delete the fork group from memory.

        Args:
            fork_group_id (str): ID of the fork group to delete.
        """
        self._groups.pop(fork_group_id, None)
        self._branch_sequences.pop(fork_group_id, None)

    def generate_group_id(self, base_id: str) -> str:
        """
        Generate a unique fork group ID based on the base ID and timestamp.

        Args:
            base_id (str): Base ID for the fork group.

        Returns:
            str: A unique fork group ID.
        """
        return f"{base_id}_{int(time.time())}"

    def track_branch_sequence(self, fork_group_id: str, agent_sequence: List[str]) -> None:
        """
        Track the sequence of agents in a branch.

        Args:
            fork_group_id (str): ID of the fork group.
            agent_sequence (list): List of agent IDs in sequence.
        """
        if fork_group_id not in self._branch_sequences:
            self._branch_sequences[fork_group_id] = {}

        for i in range(len(agent_sequence) - 1):
            current = agent_sequence[i]
            next_one = agent_sequence[i + 1]
            self._branch_sequences[fork_group_id][current] = next_one

    def next_in_sequence(self, fork_group_id: str, agent_id: str) -> Optional[str]:
        """
        Get the next agent in the sequence after the current agent.

        Args:
            fork_group_id (str): ID of the fork group.
            agent_id (str): ID of the current agent.

        Returns:
            str: ID of the next agent, or None if there is no next agent.
        """
        if fork_group_id not in self._branch_sequences:
            return None
        return self._branch_sequences[fork_group_id].get(agent_id)

    def remove_group(self, group_id: str) -> None:
        """
        Remove a group (for compatibility with existing code).

        Args:
            group_id (str): ID of the group to remove.

        Raises:
            KeyError: If the group doesn't exist.
        """
        if group_id not in self._groups:
            raise KeyError(f"Group {group_id} not found")
        self.delete_group(group_id)
