# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for ClassificationMixin."""

import pytest

from orka.memory.base_logger_mixins.classification_mixin import ClassificationMixin


class ConcreteClassificationMixin(ClassificationMixin):
    """Concrete implementation for testing."""

    def __init__(self):
        self.decay_config = {
            "memory_type_rules": {
                "long_term_events": ["success", "completion", "write"],
                "short_term_events": ["debug", "processing", "start"],
            },
            "importance_rules": {
                "base_score": 0.5,
                "event_type_boosts": {"write": 0.3, "success": 0.2},
                "agent_type_boosts": {"memory": 0.2},
            },
        }


class TestClassificationMixin:
    """Tests for ClassificationMixin."""

    @pytest.fixture
    def classifier(self):
        return ConcreteClassificationMixin()

    def test_calculate_importance_score_base(self, classifier):
        """Test base importance score."""
        score = classifier._calculate_importance_score("info", "agent1", {})
        assert score == 0.5

    def test_calculate_importance_score_event_boost(self, classifier):
        """Test event type boost."""
        score = classifier._calculate_importance_score("write", "agent1", {})
        assert score == 0.8  # 0.5 + 0.3

    def test_calculate_importance_score_agent_boost(self, classifier):
        """Test agent type boost."""
        score = classifier._calculate_importance_score("info", "memory_agent", {})
        assert score == 0.7  # 0.5 + 0.2

    def test_calculate_importance_score_result_boost(self, classifier):
        """Test result presence boost."""
        score = classifier._calculate_importance_score("info", "agent1", {"result": "test"})
        assert score == 0.6  # 0.5 + 0.1

    def test_calculate_importance_score_error_penalty(self, classifier):
        """Test error presence penalty."""
        score = classifier._calculate_importance_score("info", "agent1", {"error": "fail"})
        assert score == 0.4  # 0.5 - 0.1

    def test_calculate_importance_score_clamped(self, classifier):
        """Test score is clamped to 0-1."""
        # Add many boosts
        score = classifier._calculate_importance_score(
            "write", "memory_agent", {"result": "test"}
        )
        assert 0.0 <= score <= 1.0

    def test_classify_memory_type_log_always_short(self, classifier):
        """Test log category is always short-term."""
        result = classifier._classify_memory_type("success", 0.9, "log")
        assert result == "short_term"

    def test_classify_memory_type_stored_long_term(self, classifier):
        """Test stored category with long-term event."""
        result = classifier._classify_memory_type("success", 0.5, "stored")
        assert result == "long_term"

    def test_classify_memory_type_stored_short_term(self, classifier):
        """Test stored category with short-term event."""
        result = classifier._classify_memory_type("debug", 0.5, "stored")
        assert result == "short_term"

    def test_classify_memory_type_by_importance(self, classifier):
        """Test classification by importance score."""
        result = classifier._classify_memory_type("unknown", 0.8, "stored")
        assert result == "long_term"

        result = classifier._classify_memory_type("unknown", 0.5, "stored")
        assert result == "short_term"

    def test_classify_memory_category_explicit(self, classifier):
        """Test explicit log_type parameter."""
        result = classifier._classify_memory_category("info", "agent1", {}, "memory")
        assert result == "stored"

        result = classifier._classify_memory_category("info", "agent1", {}, "log")
        assert result == "log"

    def test_classify_memory_category_legacy_detection(self, classifier):
        """Test legacy memory writer detection."""
        result = classifier._classify_memory_category(
            "write", "memory_writer", {}, "unknown"
        )
        assert result == "stored"

    def test_classify_memory_category_payload_detection(self, classifier):
        """Test payload-based detection."""
        payload = {"content": "test", "metadata": {"key": "value"}}
        result = classifier._classify_memory_category("info", "agent1", payload, "unknown")
        assert result == "stored"

    def test_classify_memory_category_default(self, classifier):
        """Test default classification."""
        result = classifier._classify_memory_category("info", "agent1", {}, "unknown")
        assert result == "log"

