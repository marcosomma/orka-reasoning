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
    def __init__(self, redis_client):
        self.redis = redis_client

    def create_group(self, fork_group_id, agent_ids):
        """Create a new fork group with agent IDs."""
        if not agent_ids:
            raise ValueError(f"Cannot create fork group '{fork_group_id}' with empty agent list.")
        self.redis.sadd(self._group_key(fork_group_id), *agent_ids)

    def mark_agent_done(self, fork_group_id, agent_id):
        """Remove agent ID from fork group."""
        self.redis.srem(self._group_key(fork_group_id), agent_id)

    def is_group_done(self, fork_group_id):
        """Return True if all agents are done."""
        return self.redis.scard(self._group_key(fork_group_id)) == 0

    def list_pending_agents(self, fork_group_id):
        """Return list of agents still pending."""
        pending = self.redis.smembers(self._group_key(fork_group_id))
        return [i.decode() if isinstance(i, bytes) else i for i in pending]

    def delete_group(self, fork_group_id):
        """Delete the fork group key from Redis."""
        self.redis.delete(self._group_key(fork_group_id))

    def generate_group_id(self, base_id):
        """Generate a unique fork group ID based on agent ID + timestamp."""
        return f"{base_id}_{int(time.time())}"

    def _group_key(self, fork_group_id):
        """Internal helper to standardize Redis key naming."""
        return f"fork_group:{fork_group_id}"
