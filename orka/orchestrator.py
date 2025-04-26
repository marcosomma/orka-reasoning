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

import importlib
import os
import json
from time import time
from jinja2 import Template
from datetime import datetime
from .loader import YAMLLoader
from .agents import agents, llm_agents, google_duck_agents, router_agent, failover_agent, failing_agent
from .memory_logger import RedisMemoryLogger

AGENT_TYPES = {
    "binary": agents.BinaryAgent,
    "classification": agents.ClassificationAgent,
    "openai-binary": llm_agents.OpenAIBinaryAgent,
    "openai-classification": llm_agents.OpenAIClassificationAgent,
    "openai-answer": llm_agents.OpenAIAnswerBuilder,
    "google-search": google_duck_agents.GoogleSearchAgent,
    "duckduckgo": google_duck_agents.DuckDuckGoAgent,
    "router": router_agent.RouterAgent,
    "failover": failover_agent.FailoverAgent,
    "failing": failing_agent.FailingAgent,
}


class Orchestrator:
    def __init__(self, config_path):
        self.loader = YAMLLoader(config_path)
        self.loader.validate()
        self.orchestrator_cfg = self.loader.get_orchestrator()
        self.agent_cfgs = self.loader.get_agents()
        self.memory = RedisMemoryLogger()
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
            clean_cfg["agent_id"] = agent_id
            clean_cfg.pop("id", None)
            clean_cfg.pop("type", None)

            # print(f"[INIT] Instantiating agent {agent_id} of type '**********'")
            print(f"[INIT] Instantiating agent {agent_id} of type {agent_type}")

            if agent_type == "router":
                clean_cfg.pop("prompt", None)
                clean_cfg.pop("queue", None)
                params = clean_cfg.pop("params", {})
                clean_cfg.pop("agent_id", None)
                return agent_cls(agent_id=agent_id, params=params, **clean_cfg)

            elif agent_type == "failover":
                # Recursively init children
                child_instances = []
                for child_cfg in cfg.get("children", []):
                    child_agent = init_single_agent(child_cfg)
                    child_instances.append(child_agent)
                return agent_cls(agent_id=agent_id, children=child_instances, queue=cfg.get("queue"))

            else:
                prompt = clean_cfg.pop("prompt", None)
                queue = clean_cfg.pop("queue", None)
                clean_cfg.pop("agent_id", None)
                return agent_cls(agent_id=agent_id, prompt=prompt, queue=queue, **clean_cfg)

        for cfg in self.agent_cfgs:
            agent = init_single_agent(cfg)
            instances[cfg["id"]] = agent

        return instances

    def render_prompt(self, template_str, payload):
        if not isinstance(template_str, str):
            raise ValueError(
                f"Expected template_str to be str, got {type(template_str)} instead.")
        return Template(template_str).render(**payload)

    @staticmethod
    def normalize_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.strip().lower()
            return value in ["true", "yes"]
        return False

    def run(self, input_data):
        logs = []
        queue = self.orchestrator_cfg["agents"][:]

        while queue:
            agent_id = queue.pop(0)
            agent = self.agents[agent_id]
            agent_type = agent.type
            print(f"[ORKA] Running agent '{agent_id}' of type '{agent_type}'")
            # print(f"[ORKA] Running agent '{agent_id}' of type '**********'")

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

            if agent_type == "routeragent":
                decision_key = agent.params.get("decision_key")
                routing_map = agent.params.get("routing_map")
                if decision_key is None:
                    raise ValueError("Router agent must have 'decision_key' in params.")
                raw_decision_value = payload["previous_outputs"].get(decision_key)
                normalized = self.normalize_bool(raw_decision_value)
                normalized_key = "true" if normalized else "false"
                payload["previous_outputs"][decision_key] = normalized_key
                result = agent.run(payload)
                next_agents = result if isinstance(result, list) else [result]
                queue = next_agents
                payload_out = {
                    "input": input_data,
                    "decision_key": decision_key,
                    "decision_value":  str(raw_decision_value),
                    "routing_map":  str(routing_map),
                    "next_agents":  str(next_agents)
                }
            elif hasattr(agent, "prompt") and isinstance(agent.prompt, str):
                rendered_prompt = self.render_prompt(agent.prompt, payload)
                payload["prompt"] = rendered_prompt
                result = agent.run(payload)
                payload_out = {
                    "input": input_data,
                    "prompt": rendered_prompt,
                    "result": result
                }
            else:
                result = agent.run(payload)
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
            if agent_type == "routeragent":
                print(f"[ORKA][ROUTER] Injecting agents into queue: {next_agents}")

        # Save log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
        self.memory.save_to_file(log_path)

        return logs  # Return raw logs, just like stored
