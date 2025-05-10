# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
import os
from unittest.mock import patch

import pytest
import yaml
from fake_redis import FakeRedisClient

from orka.orka_cli import run_cli_entrypoint


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_run_cli_entrypoint(tmp_path):
    fake_redis = FakeRedisClient()

    # Patch RedisMemoryLogger to inject fake client
    with patch("orka.memory_logger.redis.from_url", return_value=fake_redis):
        example_yaml = {
            "orchestrator": {
                "id": "test_orchestrator",
                "strategy": "decision-tree",
                "queue": "orka:test",
                "agents": ["dummy_agent"],
            },
            "agents": [
                {
                    "id": "dummy_agent",
                    "type": "openai-binary",
                    "prompt": "Is '{{ input }}' a valid project?",
                    "queue": "orka:dummy",
                }
            ],
        }

        config_file = tmp_path / "example_config.yml"
        config_file.write_text(yaml.dump(example_yaml))

        result = await run_cli_entrypoint(
            str(config_file), "Is OrKa a project?", log_to_file=False
        )

        assert isinstance(result, list)
        assert any(event["agent_id"] == "dummy_agent" for event in result)

        logfile_path = tmp_path / "orka_trace.log"
        os.chdir(tmp_path)
        await run_cli_entrypoint(
            str(config_file), "Another question?", log_to_file=True
        )

        assert logfile_path.exists()
        content = logfile_path.read_text()
        assert "dummy_agent" in content
