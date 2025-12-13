"""Additional unit tests for orka.orchestrator.safety_controller.

These tests exercise branches not fully covered by the existing suite:
- invalid regex handling in _check_patterns
- capability checks driven by orchestrator agents (via _node_has_capability)
- policy compliance for long paths
- content scoring nuances for domain-only vs PII/harmful
"""

from unittest.mock import Mock

import pytest

from orka.orchestrator.safety_controller import SafetyController


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def _config(profile: str = "default") -> Mock:
    cfg = Mock()
    cfg.safety_threshold = 0.1
    cfg.safety_profile = profile
    return cfg


def test_check_patterns_invalid_regex_returns_empty_list():
    controller = SafetyController(_config())

    matches = controller._check_patterns("anything", patterns=["["])  # invalid regex
    assert matches == []


@pytest.mark.asyncio
async def test_assess_capability_safety_uses_orchestrator_agent_capabilities():
    cfg = _config(profile="strict")

    # Attach an orchestrator with agents to the config, because _node_has_capability
    # reads from config.orchestrator.agents.
    orchestrator = Mock()
    agent = Mock()
    agent.capabilities = ["code_execution", "file_system_access"]
    orchestrator.agents = {"agent1": agent}
    cfg.orchestrator = orchestrator

    controller = SafetyController(cfg)

    res = await controller._assess_capability_safety({"node_id": "agent1"}, context={})

    assert res["score"] < 1.0
    assert any(r.startswith("forbidden_capability_") for r in res["risks"])
    assert "code_execution" in " ".join(res["risks"]) or "file_system_access" in " ".join(res["risks"])


@pytest.mark.asyncio
async def test_assess_policy_compliance_flags_too_long_paths():
    controller = SafetyController(_config())

    candidate = {"node_id": "agent1", "path": ["a", "b", "c", "d", "e", "f"]}
    res = await controller._assess_policy_compliance(candidate, context={})

    assert res["score"] < 1.0
    assert "path_too_long" in res["risks"]
    assert res["details"]["path_length"] == 6


@pytest.mark.asyncio
async def test_assess_content_safety_domain_only_vs_pii():
    controller = SafetyController(_config())

    # Domain-specific only (medical/legal) should be moderate risk
    candidate_med = {"node_id": "agent1", "preview": "Patient diagnosis and treatment plan"}
    res_med = await controller._assess_content_safety(candidate_med, context={"input": ""})

    assert res_med["score"] == 0.7
    assert "medical_content" in res_med["risks"]

    # PII should be high risk
    candidate_pii = {"node_id": "agent2", "preview": "SSN 123-45-6789"}
    res_pii = await controller._assess_content_safety(candidate_pii, context={"input": ""})

    assert res_pii["score"] == 0.3
    assert "pii_detected" in res_pii["risks"]
