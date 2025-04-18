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

class YAMLLoader:
    def __init__(self, path):
        self.path = path
        self.config = self._load_yaml()

    def _load_yaml(self):
        with open(self.path, 'r') as f:
            return yaml.safe_load(f)

    def get_orchestrator(self):
        return self.config.get('orchestrator', {})

    def get_agents(self):
        return self.config.get('agents', [])

    def validate(self):
        if 'orchestrator' not in self.config:
            raise ValueError("Missing 'orchestrator' section in config")
        if 'agents' not in self.config:
            raise ValueError("Missing 'agents' section in config")
        if not isinstance(self.config['agents'], list):
            raise ValueError("'agents' should be a list")
        return True