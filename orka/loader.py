# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
YAML Configuration Loader
==========================

The YAML Loader is responsible for loading, parsing, and validating configuration
files for OrKa workflows. It serves as the bridge between the declarative YAML
specifications and the runtime orchestration system.

Configuration Structure
-----------------------

OrKa configuration files consist of two main sections:

**Orchestrator Section**
    Global settings for the orchestration engine:

    * ``id`` - Unique identifier for the workflow
    * ``strategy`` - Execution strategy (e.g., sequential, parallel)
    * ``queue`` - Initial execution queue for agents
    * ``agents`` - List of agent IDs in execution order

**Agents Section**
    List of agent definitions, each containing:

    * ``id`` - Unique identifier for the agent
    * ``type`` - Agent type (e.g., llm, search, memory)
    * ``prompt`` - Template string for agent input
    * ``config`` - Type-specific configuration options
    * Additional agent-specific fields

Example Configuration
---------------------

.. code-block:: yaml

    orchestrator:
      id: knowledge_qa
      strategy: sequential
      queue: orka:knowledge_qa
      agents: [retriever, answerer]

    agents:
      - id: retriever
        type: memory
        config:
          operation: read
        namespace: knowledge_base
        prompt: "Retrieve information about {{ input }}"

      - id: answerer
        type: openai-answer
        prompt: "Answer the question based on this context: {{ previous_outputs.retriever }}"

Validation Features
-------------------

The YAMLLoader validates configuration to ensure:

* All required sections are present
* Data types are correct
* Agent references are valid
* Template syntax is properly formatted

This validation happens before the Orchestrator initializes the workflow,
preventing runtime errors from malformed configurations.

Usage Example
-------------

.. code-block:: python

    from orka.loader import YAMLLoader

    # Load and validate configuration
    loader = YAMLLoader("workflow.yml")
    loader.validate()

    # Access configuration sections
    orchestrator_config = loader.get_orchestrator()
    agents_config = loader.get_agents()
"""

import yaml
from typing import Any, Dict, List
import orka.utils.template_validator as template_validator


class YAMLLoader:
    """
    A loader for YAML configuration files.
    Loads and validates the configuration for the OrKa orchestrator.
    """

    def __init__(self, path: str) -> None:
        """
        Initialize the YAML loader with the path to the configuration file.

        Args:
            path: Path to the YAML configuration file.
        """
        self.path = path
        self.config = self._load_yaml()

    def _load_yaml(self) -> Dict[str, Any]:
        """
        Load the YAML configuration from the file.

        Returns:
            The loaded YAML configuration.
        """
        with open(self.path, encoding='utf-8') as f:
            return yaml.safe_load(f)  # type: ignore

    def get_orchestrator(self) -> Dict[str, Any]:
        """
        Get the orchestrator configuration section.

        Returns:
            The orchestrator configuration.
        """
        return self.config.get("orchestrator", {})  # type: ignore

    def get_agents(self) -> List[Dict[str, Any]]:
        """
        Get the agents configuration section.

        Returns:
            The list of agent configurations.
        """
        return self.config.get("agents", [])  # type: ignore

    def validate(self) -> bool:
        """
        Validate the configuration file.
        Checks for required sections and correct data types.

        Returns:
            True if the configuration is valid.

        Raises:
            ValueError: If the configuration is invalid.
        """
        if "orchestrator" not in self.config:
            raise ValueError("Missing 'orchestrator' section in config")
        if "agents" not in self.config:
            raise ValueError("Missing 'agents' section in config")
        if not isinstance(self.config["agents"], list):
            raise ValueError("'agents' should be a list")
        
        # Validate all agent prompt templates
        self._validate_agent_templates()
        
        return True

    def _validate_agent_templates(self) -> None:
        """
        Validate Jinja2 syntax in all agent prompts.
        
        Raises:
            ValueError: If any template has syntax errors
        """
        
        validator = template_validator.TemplateValidator()
        errors = []
        
        for agent_cfg in self.config.get("agents", []):
            agent_id = agent_cfg.get("id", "unknown")
            prompt = agent_cfg.get("prompt", "")
            
            if prompt:
                is_valid, error_msg, variables = validator.validate_template(prompt)
                if not is_valid:
                    errors.append(f"Agent '{agent_id}': {error_msg}")
        
        if errors:
            error_report = "\n".join(errors)
            raise ValueError(f"Template validation failed:\n{error_report}")
