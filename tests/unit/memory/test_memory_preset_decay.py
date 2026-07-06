# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""Regression tests (deep-review 2026-07): memory_preset decay/TTL must actually
take effect on the RedisStack backend.

Previously three stacked defects made `memory_preset:` inert for decay:
1. presets nest decay settings under a "decay" key that _init_decay_config never read,
2. RedisStackMemoryLogger.memory_decay_config was assigned the raw (un-resolved) input,
3. the decay mixin read bare `long_term_hours`/`short_term_hours` keys that neither
   presets nor the orchestrator config ever write,
4. OrchestratorBase._init_decay_config baked hardcoded defaults that deep-merged
   over any preset.
"""

from unittest.mock import patch

from orka.memory.presets import get_memory_preset
from orka.memory.redisstack_logger import RedisStackMemoryLogger
from orka.orchestrator.base import OrchestratorBase


def _make_logger(**kwargs):
    """Construct a RedisStackMemoryLogger without touching the network or threads."""
    with patch.object(RedisStackMemoryLogger, "_start_decay_scheduler", lambda self: None):
        return RedisStackMemoryLogger(redis_url="redis://fake:6379/0", **kwargs)


class TestPresetDecayResolution:
    def test_semantic_preset_ttls_reach_decay_config(self):
        logger = _make_logger(memory_preset="semantic")

        assert logger.decay_config["enabled"] is True
        assert logger.decay_config["default_short_term_hours"] == 72.0
        assert logger.decay_config["default_long_term_hours"] == 2160.0

    def test_memory_decay_config_is_preset_resolved(self):
        """The decay/metrics mixins read memory_decay_config; it must be the
        resolved config, not the raw constructor input."""
        logger = _make_logger(memory_preset="semantic")

        assert logger.memory_decay_config is logger.decay_config
        assert logger.memory_decay_config["default_long_term_hours"] == 2160.0

    def test_expiry_hours_use_preset_ttls(self):
        logger = _make_logger(memory_preset="semantic")

        # importance 0.0 -> multiplier 1.0, so expiry == base hours
        assert logger._calculate_expiry_hours("long_term", 0.0, None) == 2160.0
        assert logger._calculate_expiry_hours("short_term", 0.0, None) == 72.0

    def test_all_six_presets_expose_their_ttls(self):
        for preset in ("sensory", "working", "episodic", "semantic", "procedural", "meta"):
            expected = get_memory_preset(preset)["decay"]
            logger = _make_logger(memory_preset=preset)
            assert (
                logger.decay_config["default_short_term_hours"]
                == expected["default_short_term_hours"]
            ), preset
            assert (
                logger.decay_config["default_long_term_hours"]
                == expected["default_long_term_hours"]
            ), preset

    def test_explicit_decay_config_overrides_preset(self):
        logger = _make_logger(
            memory_preset="semantic",
            decay_config={"default_long_term_hours": 720.0},
        )

        assert logger.decay_config["default_long_term_hours"] == 720.0
        # untouched preset values survive
        assert logger.decay_config["default_short_term_hours"] == 72.0

    def test_agent_level_bare_keys_still_work(self):
        """Agent-level overrides may use bare (unprefixed) hour keys."""
        logger = _make_logger(memory_preset="semantic")

        agent_cfg = {"enabled": True, "long_term_hours": 10.0, "short_term_hours": 1.0}
        assert logger._calculate_expiry_hours("long_term", 0.0, agent_cfg) == 10.0
        assert logger._calculate_expiry_hours("short_term", 0.0, agent_cfg) == 1.0

    def test_no_preset_keeps_legacy_defaults(self):
        logger = _make_logger()

        assert logger.decay_config["enabled"] is False
        assert logger.decay_config["default_short_term_hours"] == 1.0
        assert logger.decay_config["default_long_term_hours"] == 24.0


class TestOrchestratorDecayConfigWithPreset:
    def _base_with_cfg(self, orchestrator_cfg):
        base = OrchestratorBase.__new__(OrchestratorBase)
        base.orchestrator_cfg = orchestrator_cfg
        return base

    def test_preset_present_no_baked_defaults(self, monkeypatch):
        """With memory_preset set, the orchestrator must not inject its own
        hardcoded TTL defaults - they would deep-merge over the preset.
        (Env vars remain a legitimate override; cleared here.)"""
        monkeypatch.delenv("ORKA_MEMORY_DECAY_ENABLED", raising=False)
        base = self._base_with_cfg({"memory_preset": "semantic"})

        cfg = base._init_decay_config()

        assert "default_short_term_hours" not in cfg
        assert "default_long_term_hours" not in cfg
        assert "enabled" not in cfg

    def test_env_var_still_overrides_preset(self, monkeypatch):
        monkeypatch.setenv("ORKA_MEMORY_DECAY_ENABLED", "false")
        base = self._base_with_cfg({"memory_preset": "semantic"})

        cfg = base._init_decay_config()

        assert cfg["enabled"] is False

    def test_preset_with_explicit_yaml_decay_kept(self):
        base = self._base_with_cfg(
            {
                "memory_preset": "semantic",
                "memory": {"decay": {"default_long_term_hours": 500.0}},
            }
        )

        cfg = base._init_decay_config()

        assert cfg["default_long_term_hours"] == 500.0

    def test_no_preset_keeps_defaults(self):
        base = self._base_with_cfg({})

        cfg = base._init_decay_config()

        assert cfg["enabled"] is False
        assert cfg["default_short_term_hours"] == 1.0
        assert cfg["default_long_term_hours"] == 24.0
