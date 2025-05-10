# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import os

import pytest
from dotenv import load_dotenv

# Load environment
load_dotenv()


@pytest.fixture
def example_yaml(tmp_path):
    yaml_content = """\
orchestrator:
  id: full_nodes_test_orchestrator
  strategy: decision-tree
  queue: orka:test
  agents:
    - initial_classify
    - search_required
    - fork_parallel_checks   # 🔥 Insert fork node here
    - join_parallel_checks   # 🔥 Insert join node here
    - router_search_path
    - failover_search
    - final_router
    - final_builder_true
    - final_builder_false

agents:
  # First simple classification
  - id: initial_classify
    type: openai-classification
    prompt: >
      Classify this input "{{ input }}" into science, history, or nonsense.
    options: [tech, science, history, nonsense]
    queue: orka:domain

  # Is search needed?
  - id: search_required
    type: openai-binary
    prompt: >
      Is "{{ input }}" a question that requires deep internet research?
    queue: orka:need_search

  # 🔥 Fork node: splits into two parallel validation checks
  - id: fork_parallel_checks
    type: fork
    targets:
      - topic_validity_check
      - need_for_summary_check

  # Parallel branch 1: Check topic validity
  - id: topic_validity_check
    type: openai-binary
    prompt: >
      Is "{{ input }}" a valid, meaningful topic to investigate?
    queue: orka:topic_check

  # Parallel branch 2: Check if we need a summary
  - id: need_for_summary_check
    type: openai-binary
    prompt: >
      Should we build a detailed summary for "{{ input }}"?
    queue: orka:summary_check

  # 🔥 Join node: waits for both topic_validity_check and need_for_summary_check
  - id: join_parallel_checks
    type: join
    group: fork_parallel_checks

  # Router to different paths
  - id: router_search_path
    type: router
    params:
      decision_key: search_required
      routing_map:
        true: ["failover_search", "final_router"]
        false: ["info_completed", "final_router"]

  # Failover node: tries failing agent first, fallback to real search if crash
  - id: failover_search
    type: failover
    children:
      - id: broken_search
        type: failing
        prompt: "This search will fail because agent is broken."
        queue: orka:broken_search

      - id: backup_duck_search
        type: duckduckgo
        prompt: Perform a backup web search for "{{ input }}"
        queue: orka:duck_backup

  # Additional info check
  - id: info_completed
    type: openai-binary
    prompt: >
      Did we retrieve extra data for this input "{{ input }}"?
      {{ previous_outputs }}
    queue: orka:info_completed

  # Final router based on info check
  - id: final_router
    type: router
    params:
      decision_key: info_completed
      routing_map:
        true: ["final_builder_true"]
        false: ["final_builder_false"]

  # Final answer building if extra info was found
  - id: final_builder_true
    type: openai-answer
    prompt: |
      Build a detailed answer combining:
      - Classification result: {{ previous_outputs.initial_classify }}
      - Search result: {{ previous_outputs.failover_search }}
    queue: orka:final_output

  # Final answer building if no extra info
  - id: final_builder_false
    type: openai-answer
    prompt: |
      Build a detailed answer based on the classification result:
      - Classification result: {{ previous_outputs.initial_classify }}
    queue: orka:final_output
    """
    config_file = tmp_path / "example_valid.yml"
    config_file.write_text(yaml_content, encoding="utf-8")
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
