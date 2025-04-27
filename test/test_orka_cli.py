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
import pytest
import tempfile
import os
import yaml
import asyncio
from orka.orka_cli import run_cli_entrypoint

@pytest.mark.asyncio
async def test_run_cli_entrypoint(tmp_path):
    # Create a fake YAML configuration
    example_yaml = {
        "orchestrator": {
            "id": "test_orchestrator",
            "strategy": "decision-tree",
            "queue": "orka:test",
            "agents": ["dummy_agent"]
        },
        "agents": [
            {
                "id": "dummy_agent",
                "type": "openai-binary",
                "prompt": "Is '{{ input }}' a valid project?",
                "queue": "orka:dummy"
            }
        ]
    }

    config_file = tmp_path / "example_config.yml"
    config_file.write_text(yaml.dump(example_yaml))

    # Run the CLI entrypoint
    result = await run_cli_entrypoint(str(config_file), "Is OrKa a project?", log_to_file=False)

    # Assertions
    assert isinstance(result, list)  # Should be list of logs
    assert any(event["agent_id"] == "dummy_agent" for event in result)

    # Now test log-to-file mode
    logfile_path = tmp_path / "orka_trace.log"
    os.chdir(tmp_path)  # Make sure log gets created in tmp
    await run_cli_entrypoint(str(config_file), "Another question?", log_to_file=True)

    assert logfile_path.exists()
    content = logfile_path.read_text()
    assert "dummy_agent" in content

