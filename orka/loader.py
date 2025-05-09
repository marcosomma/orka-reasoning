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

import yaml
from typing import Dict, List, Any

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
        with open(self.path, 'r') as f:
            return yaml.safe_load(f)

    def get_orchestrator(self) -> Dict[str, Any]:
        """
        Get the orchestrator configuration section.
        
        Returns:
            The orchestrator configuration.
        """
        return self.config.get('orchestrator', {})

    def get_agents(self) -> List[Dict[str, Any]]:
        """
        Get the agents configuration section.
        
        Returns:
            The list of agent configurations.
        """
        return self.config.get('agents', [])

    def validate(self) -> bool:
        """
        Validate the configuration file.
        Checks for required sections and correct data types.
        
        Returns:
            True if the configuration is valid.
        
        Raises:
            ValueError: If the configuration is invalid.
        """
        if 'orchestrator' not in self.config:
            raise ValueError("Missing 'orchestrator' section in config")
        if 'agents' not in self.config:
            raise ValueError("Missing 'agents' section in config")
        if not isinstance(self.config['agents'], list):
            raise ValueError("'agents' should be a list")
        return True