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
# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: CC BY-NC 4.0

import os
import json
from time import time
from datetime import datetime
from jinja2 import Template

from .loader import YAMLLoader
from .agents import agents, llm_agents, google_duck_agents
from .nodes import router_node, failover_node, failing_node, join_node, fork_node
from .memory_logger import RedisMemoryLogger
from .fork_group_manager import ForkGroupManager

AGENT_TYPES = {
    "binary": agents.BinaryAgent,
    "classification": agents.ClassificationAgent,
    "openai-binary": llm_agents.OpenAIBinaryAgent,
    "openai-classification": llm_agents.OpenAIClassificationAgent,
    "openai-answer": llm_agents.OpenAIAnswerBuilder,
    "google-search": google_duck_agents.GoogleSearchAgent,
    "duckduckgo": google_duck_agents.DuckDuckGoAgent,
    "router": router_node.RouterNode,
    "failover": failover_node.FailoverNode,
    "failing": failing_node.FailingNode,
    "join": join_node.JoinNode,
    "fork": fork_node.ForkNode
}

class Orchestrator:
    def __init__(self, config_path):
        self.loader = YAMLLoader(config_path)
        self.loader.validate()

        self.orchestrator_cfg = self.loader.get_orchestrator()
        self.agent_cfgs = self.loader.get_agents()

        self.memory = RedisMemoryLogger()
        self.fork_manager = ForkGroupManager(self.memory.redis)

        self.agents = self._init_agents()

    def _init_agents(self):
        instances = {}

        def init_single_agent(cfg):
            agent_cls = AGENT_TYPES.get(cfg["type"])
            if not agent_cls:
                raise ValueError(f"Unsupported agent type: {cfg['type']}")

            agent_type = cfg["type"].strip().lower()
            agent_id = cfg["id"]

            clean_cfg = cfg.copy()
            clean_cfg.pop("id", None)
            clean_cfg.pop("type", None)
            clean_cfg.pop("prompt", None)
            clean_cfg.pop("queue", None)

            print(f"[INIT] Instantiating agent {agent_id} of type {agent_type}")

            if agent_type in ("router"):
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(node_id=agent_id, **clean_cfg)

            if agent_type in ("fork", "join"):
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(node_id=agent_id, prompt=prompt, queue=queue, memory_logger=self.memory, **clean_cfg)

            if agent_type == "failover":
                queue = cfg.get("queue", None)
                child_instances = [init_single_agent(child_cfg) for child_cfg in cfg.get("children", [])]
                return agent_cls(node_id=agent_id, children=child_instances, queue=queue)

            if agent_type == "failing":
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(node_id=agent_id, prompt=prompt, queue=queue, **clean_cfg)

            prompt = cfg.get("prompt", None)
            queue = cfg.get("queue", None)
            return agent_cls(agent_id=agent_id, prompt=prompt, queue=queue, **clean_cfg)

        for cfg in self.agent_cfgs:
            agent = init_single_agent(cfg)
            instances[cfg["id"]] = agent

        return instances

    def render_prompt(self, template_str, payload):
        if not isinstance(template_str, str):
            raise ValueError(f"Expected template_str to be str, got {type(template_str)} instead.")
        return Template(template_str).render(**payload)

    @staticmethod
    def normalize_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes"]
        return False

    def run(self, input_data):
        logs = []
        queue = self.orchestrator_cfg["agents"][:]

        while queue:
            agent_id = queue.pop(0)
            agent = self.agents[agent_id]
            agent_type = agent.type
            print(f"[ORKA] Running agent '{agent_id}' of type '{agent_type}'")

            payload = {
                "input": input_data,
                "previous_outputs": {
                    log["agent_id"]: log["payload"]["result"]
                    for log in logs
                    if "result" in log["payload"]
                }
            }
            log_entry = {
                "agent_id": agent_id,
                "event_type": agent.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat()
            }

            start_time = time()

            if agent_type == "routernode":
                decision_key = agent.params.get("decision_key")
                routing_map = agent.params.get("routing_map")
                if decision_key is None:
                    raise ValueError("Router agent must have 'decision_key' in params.")
                raw_decision_value = payload["previous_outputs"].get(decision_key)
                normalized = self.normalize_bool(raw_decision_value)
                payload["previous_outputs"][decision_key] = "true" if normalized else "false"

                result = agent.run(payload)
                next_agents = result if isinstance(result, list) else [result]
                queue = next_agents

                payload_out = {
                    "input": input_data,
                    "decision_key": decision_key,
                    "decision_value": str(raw_decision_value),
                    "routing_map": str(routing_map),
                    "next_agents": str(next_agents)
                }

            elif agent_type == "forknode":
                result = agent.run(payload)
                fork_targets = agent.config.get("targets", [])
                if not fork_targets:
                    raise ValueError(f"ForkNode '{agent_id}' requires non-empty 'targets' list.")

                fork_group_id = self.fork_manager.generate_group_id(agent_id)
                self.fork_manager.create_group(fork_group_id, fork_targets)

                queue = fork_targets + queue

                payload_out = {
                    "input": input_data,
                    "fork_group": fork_group_id,
                    "fork_targets": fork_targets
                }

            elif agent_type == "joinnode":
                result = agent.run(payload)
                fork_group_id = getattr(agent, "group_id", None)
                if not fork_group_id:
                    raise ValueError(f"JoinNode '{agent_id}' missing required group_id.")

                if not self.fork_manager.is_group_done(fork_group_id):
                    print(f"[ORKA][JOIN][WAITING] Node '{agent_id}' is still waiting on fork group: {fork_group_id}")
                    queue.append(agent_id)
                    continue  # Skip logging this round

                payload_out = {
                    "input": input_data,
                    "joined_group": fork_group_id,
                    "result": result
                }
                self.fork_manager.delete_group(fork_group_id)  # Clean up fork group after join

            else:
                # Normal Agent
                result = agent.run(payload)

                if isinstance(result, dict) and result.get("status") == "waiting":
                    print(f"[ORKA][WAITING] Node '{agent_id}' is still waiting: {result.get('received')}")
                    queue.append(agent_id)
                    continue

                # After normal agent finishes, mark it done if it's part of a fork
                fork_group = payload.get("input", {})
                if fork_group:
                    self.fork_manager.mark_agent_done(fork_group, agent_id)

                payload_out = {
                    "input": input_data,
                    "result": result
                }

            duration = round(time() - start_time, 4)
            log_entry["duration"] = duration
            log_entry["payload"] = payload_out
            logs.append(log_entry)
            self.memory.log(agent_id, agent.__class__.__name__, payload_out)

            print(f"[ORKA] Agent '{agent_id}' returned: {result}")

        # Save logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
        self.memory.save_to_file(log_path)

        return logs
