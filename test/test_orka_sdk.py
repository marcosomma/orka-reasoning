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
  id: orka-ui
  strategy: sequential
  queue: orka:failover
  agents:
    - test_failover
    - need_answer
    - router_answer
    - validate_fact
    - test_failover2

agents:
  - id: test_failover
    type: failover
    queue: orka:test_failover
    children:
      - id: failing_test_agent1
        type: failing
        queue: orka:failing_test_agent1
      - id: actual_working_agent
        type: duckduckgo
        prompt: >
          {{ input }}
        queue: orka:actual_working_agent

  - id: need_answer
    type: openai-binary
    prompt: >
      Is this a {{ input }} is a question that requires an answer or a fact to be validated?
      - TRUE: ia s question and requires an answer
      - FALSE: is an assertion requires a fact to be validated
    queue: orka:is_fact

  - id: router_answer
    type: router
    params:
      decision_key: need_answer
      routing_map:
        true: ["test_failover2"]
        false: ["validate_fact"]

  - id: validate_fact
    type: openai-binary
    prompt: |
      Given the fact "{{ input }}", and the search results "{{ previous_outputs.duck_search }}"?
    queue: orka:validation_queue

  - id: test_failover2
    type: failover
    queue: orka:test_failover2
    children:
      - id: failing_test_agent2
        type: failing
        queue: orka:failing_test_agent2
      - id: build_answer
        type: openai-answer
        prompt: |
          Given this question "{{ input }}", and the search results "{{ previous_outputs.test_failover }}", return a compelling answer.
        queue: orka:validation_queue
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
        assert any(agent_id in true_agent_ids for agent_id in ["test_failover2"]), \
            f"Expected one of build_answer, validate_fact, or duck_search, but got {true_agent_ids}"
        # Check expected outputs are somewhere in the true_agent_ids
        assert not any(agent_id in true_agent_ids for agent_id in ["validate_fact"]), \
            f"Expected one of build_answer, validate_fact, or duck_search, but got {true_agent_ids}"

        result_router_false = run_cli_entrypoint(
            config_path=str(example_yaml),
            input_text="Colosseum is in Rome!",
            log_to_file=False,
        )

        # Make sure result is iterable
        assert isinstance(result_router_false, list), f"Expected list of events, got {type(result_router_false)}"

        # Extract agent_ids from events
        false_agent_ids = {entry["agent_id"] for entry in result_router_false if "agent_id" in entry}

        # Check expected outputs are somewhere in the false_agent_ids
        assert any(agent_id in false_agent_ids for agent_id in ["validate_fact"]), \
            f"Expected one of build_answer, validate_fact, or duck_search, but got {false_agent_ids}"
        # Check expected outputs are somewhere in the false_agent_ids
        assert not any(agent_id in false_agent_ids for agent_id in ["test_failover2"]), \
            f"Expected one of build_answer, validate_fact, or duck_search, but got {false_agent_ids}"

    except Exception as e:
        pytest.fail(f"Execution failed: {e}")

