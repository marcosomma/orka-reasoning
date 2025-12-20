# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for PayloadEnhancerMixin."""

import pytest

from orka.orchestrator.prompt_rendering.payload_enhancer import PayloadEnhancerMixin
from orka.orchestrator.prompt_rendering.template_safe_object import TemplateSafeObject


class ConcretePayloadEnhancer(PayloadEnhancerMixin):
    """Concrete implementation for testing."""

    pass


class TestPayloadEnhancerMixin:
    """Tests for PayloadEnhancerMixin."""

    @pytest.fixture
    def enhancer(self):
        return ConcretePayloadEnhancer()

    def test_enhance_payload_for_templates_empty(self, enhancer):
        """Test enhancement with empty payload."""
        result = enhancer._enhance_payload_for_templates({})
        assert result == {}

    def test_enhance_payload_wraps_previous_outputs(self, enhancer):
        """Test that previous_outputs are wrapped."""
        payload = {"previous_outputs": {"agent1": {"result": "test"}}}
        result = enhancer._enhance_payload_for_templates(payload)
        assert "previous_outputs" in result
        assert isinstance(result["previous_outputs"]["agent1"], TemplateSafeObject)

    def test_enhance_payload_wraps_common_fields(self, enhancer):
        """Test that common fields are wrapped."""
        payload = {
            "input": "test input",
            "web_sources": ["source1"],
            "past_context": {"ctx": "data"},
        }
        result = enhancer._enhance_payload_for_templates(payload)

        assert isinstance(result["input"], TemplateSafeObject)
        assert isinstance(result["web_sources"], TemplateSafeObject)
        assert isinstance(result["past_context"], TemplateSafeObject)

    def test_enhance_previous_outputs_orka_response(self, enhancer):
        """Test enhancement of OrkaResponse format."""
        outputs = {
            "agent1": {
                "component_type": "agent",
                "result": "test result",
                "status": "success",
                "confidence": 0.9,
            }
        }
        result = enhancer._enhance_previous_outputs(outputs)

        assert "agent1" in result
        assert result["agent1"]["result"] == "test result"
        assert result["agent1"]["status"] == "success"
        assert result["agent1"]["response"] == "test result"  # Legacy mapping

    def test_enhance_previous_outputs_legacy(self, enhancer):
        """Test enhancement preserves legacy format."""
        outputs = {"agent1": {"response": "legacy result"}}
        result = enhancer._enhance_previous_outputs(outputs)

        assert result["agent1"] == {"response": "legacy result"}

    def test_enhance_previous_outputs_removes_none(self, enhancer):
        """Test that None values are removed."""
        outputs = {
            "agent1": {
                "component_type": "agent",
                "result": "test",
                "error": None,
                "confidence": None,
            }
        }
        result = enhancer._enhance_previous_outputs(outputs)

        assert "error" not in result["agent1"]
        assert "confidence" not in result["agent1"]

