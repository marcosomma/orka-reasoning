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
import pytest
from dotenv import load_dotenv

# Load environment
load_dotenv()

@pytest.fixture
def example_yaml(tmp_path):
    yaml_content = '''\
orchestrator:
  id: orka-ui-full
  strategy: sequential
  queue: orka:full
  agents:
    - domain_classifier
    - need_answer
    - router_decision
    - failover_search
    - wait_results
    - final_router
    - build_final_answer

agents:
  # Basic classifiers
  - id: domain_classifier
    type: openai-classification
    prompt: >
      Classify this input "{{ input }}" into: science, technology, nonsense.
    options: [science, technology, nonsense]
    queue: orka:domain

  - id: need_answer
    type: openai-binary
    prompt: >
      Is "{{ input }}" a question requiring an answer? (TRUE/FALSE)
    queue: orka:is_fact

  # First router decision
  - id: router_decision
    type: router
    params:
      decision_key: need_answer
      routing_map:
        true: ["failover_search"]
        false: ["failover_search"]

  # Failover search path
  - id: failover_search
    type: failover
    queue: orka:search
    children:
      - id: fail_broken_search
        type: failing
        queue: orka:broken_search
      - id: backup_duck_search
        type: duckduckgo
        prompt: Search the internet for "{{ input }}"
        queue: orka:backup_search

  # Wait for multiple inputs
  - id: wait_results
    type: waitfor
    queue: orka:wait
    inputs:
      - domain_classifier
      - failover_search

  # Router based on domain
  - id: final_router
    type: router
    params:
      decision_key: domain_classifier
      routing_map:
        science: ["build_final_answer"]
        technology: ["build_final_answer"]
        nonsense: ["build_final_answer"]

  # Final answer building
  - id: build_final_answer
    type: openai-answer
    prompt: |
      Create a final answer combining:
      - Domain: {{ previous_outputs.domain_classifier }}
      - Search Results: {{ previous_outputs.backup_duck_search }}
    queue: orka:final
    '''
    config_file = tmp_path / "example_valid.yml"
    config_file.write_text(yaml_content)
    print(f"YAML config file created at: {config_file}")
    return config_file

def test_env_variables():
    assert os.getenv("OPENAI_API_KEY") is not None
    assert os.getenv("BASE_OPENAI_MODEL") is not None

def test_yaml_structure(example_yaml):
    import yaml
    data = yaml.safe_load(example_yaml.read_text())
    assert "agents" in data
    assert "orchestrator" in data
    assert isinstance(data["agents"], list)
    assert isinstance(data["orchestrator"]["agents"], list)
    assert len(data["agents"]) == len(data["orchestrator"]["agents"])

def test_run_orka(monkeypatch, example_yaml):
    # Mock env vars
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    monkeypatch.setenv("BASE_OPENAI_MODEL", os.getenv("BASE_OPENAI_MODEL"))

    from orka.orka_cli import run_cli_entrypoint

    try:
        result_router_true = run_cli_entrypoint(
            config_path=str(example_yaml),
            input_text="What is the capital of France?",
            log_to_file=False,
        )

        # Make sure result is iterable
        assert isinstance(result_router_true, list), f"Expected list of events, got {type(result_router_true)}"

        # Extract agent_ids from events
        true_agent_ids = {entry["agent_id"] for entry in result_router_true if "agent_id" in entry}

        # Check expected outputs are somewhere in the true_agent_ids
        assert any(agent_id in true_agent_ids for agent_id in ['need_answer', 'test_failover2', 'router_answer', 'validate_fact']), \
            f"Expected ['need_answer', 'test_failover2', 'router_answer', 'validate_fact'], but got {true_agent_ids}"

    except Exception as e:
        pytest.fail(f"Execution failed: {e}")

