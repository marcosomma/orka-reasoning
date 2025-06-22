# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import os

import pytest
from dotenv import load_dotenv

# Load environment
load_dotenv()


@pytest.fixture
def example_yaml(tmp_path, valid_orka_yaml):
    """Create example YAML file using the valid OrKa YAML structure."""
    config_file = tmp_path / "example_valid.yml"
    config_file.write_text(valid_orka_yaml, encoding="utf-8")
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
