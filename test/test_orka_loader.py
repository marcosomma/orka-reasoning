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

def test_loader_valid_file(tmp_path):
    from orka.loader import YAMLLoader
    file = tmp_path / "orka.yaml"
    file.write_text("orchestrator:\n  id: test\nagents: []")
    loader = YAMLLoader(str(file))
    assert loader.get_orchestrator()['id'] == "test"
    assert loader.get_agents() == []

def test_loader_validation_errors(tmp_path):
    from orka.loader import YAMLLoader
    file = tmp_path / "invalid.yaml"
    file.write_text("agents: []")
    loader = YAMLLoader(str(file))
    try:
        loader.validate()
    except ValueError as e:
        assert "orchestrator" in str(e)
