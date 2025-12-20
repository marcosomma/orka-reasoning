# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
"""Tests for OrchestrationLoggingMixin - event logging functionality."""

import json
from unittest.mock import MagicMock

import pytest

from orka.memory.redisstack.logging_mixin import OrchestrationLoggingMixin


class MockLoggingLogger(OrchestrationLoggingMixin):
    """Mock class to test OrchestrationLoggingMixin."""

    def __init__(self):
        self.memory = []
        self.debug_keep_previous_outputs = False
        self.log_memory_calls = []

    def log_memory(self, **kwargs):
        self.log_memory_calls.append(kwargs)
        return "orka_memory:mock"

    def _calculate_expiry_hours(self, memory_type, importance_score, agent_decay_config):
        if memory_type == "long_term":
            return 24.0
        return 1.0

    def _classify_memory_category(self, event_type, agent_id, payload, log_type):
        if log_type == "memory":
            return "stored"
        return "log"


class TestLoggingMixinLog:
    """Tests for log method."""

    def test_log_basic_event(self):
        logger = MockLoggingLogger()

        logger.log(
            agent_id="agent_1",
            event_type="agent.start",
            payload={"message": "Starting"},
            run_id="run_123",
        )

        assert len(logger.log_memory_calls) == 1
        assert logger.log_memory_calls[0]["node_id"] == "agent_1"
        assert logger.log_memory_calls[0]["trace_id"] == "run_123"

    def test_log_with_step_and_fork(self):
        logger = MockLoggingLogger()

        logger.log(
            agent_id="agent_1",
            event_type="agent.end",
            payload={"result": "Success"},
            step=5,
            run_id="run_123",
            fork_group="fork_1",
            parent="parent_agent",
        )

        assert len(logger.log_memory_calls) == 1
        metadata = logger.log_memory_calls[0]["metadata"]
        assert metadata["step"] == 5
        assert metadata["fork_group"] == "fork_1"
        assert metadata["parent"] == "parent_agent"

    def test_log_memory_type(self):
        logger = MockLoggingLogger()

        logger.log(
            agent_id="agent_1",
            event_type="agent.end",
            payload={"result": "Done"},
            run_id="run_123",
            log_type="memory",
        )

        call = logger.log_memory_calls[0]
        assert call["metadata"]["log_type"] == "memory"
        assert call["memory_type"] == "long_term"

    def test_log_orchestration_short_expiry(self):
        logger = MockLoggingLogger()

        logger.log(
            agent_id="agent_1",
            event_type="agent.start",
            payload={},
            run_id="run_123",
            log_type="log",
        )

        call = logger.log_memory_calls[0]
        assert call["expiry_hours"] == 0.2  # 12 minutes

    def test_log_appends_to_memory_trace(self):
        logger = MockLoggingLogger()

        logger.log(
            agent_id="agent_1",
            event_type="agent.start",
            payload={"data": "test"},
            run_id="run_123",
        )

        assert len(logger.memory) == 1
        assert logger.memory[0]["agent_id"] == "agent_1"
        assert logger.memory[0]["event_type"] == "agent.start"


class TestLoggingMixinExtractContent:
    """Tests for _extract_content_from_payload method."""

    def test_extract_content_with_result(self):
        logger = MockLoggingLogger()
        payload = {"result": "Test result"}

        content = logger._extract_content_from_payload(payload, "agent.end")

        assert "Test result" in content
        assert "agent.end" in content

    def test_extract_content_with_component_type(self):
        logger = MockLoggingLogger()
        payload = {
            "component_type": "agent",
            "result": "Agent output",
            "internal_reasoning": "Thought process",
        }

        content = logger._extract_content_from_payload(payload, "agent.end")

        assert "Agent output" in content
        assert "Reasoning: Thought process" in content

    def test_extract_content_with_error(self):
        logger = MockLoggingLogger()
        payload = {"component_type": "agent", "error": "Something failed"}

        content = logger._extract_content_from_payload(payload, "agent.error")

        assert "Error: Something failed" in content

    def test_extract_content_empty_payload(self):
        logger = MockLoggingLogger()
        payload = {}

        content = logger._extract_content_from_payload(payload, "agent.start")

        assert "agent.start" in content


class TestLoggingMixinImportance:
    """Tests for _calculate_importance_score method."""

    def test_importance_agent_error(self):
        logger = MockLoggingLogger()

        score = logger._calculate_importance_score("agent.error", "agent_1", {})

        assert score == 0.9

    def test_importance_orchestrator_end(self):
        logger = MockLoggingLogger()

        score = logger._calculate_importance_score("orchestrator.end", "orch", {})

        assert score == 0.9

    def test_importance_with_result(self):
        logger = MockLoggingLogger()
        payload = {"result": "Success"}

        score = logger._calculate_importance_score("agent.end", "agent_1", payload)

        assert score == 1.0  # 0.8 + 0.2 capped at 1.0

    def test_importance_with_error_in_payload(self):
        logger = MockLoggingLogger()
        payload = {"error": "Failed"}

        score = logger._calculate_importance_score("llm.query", "agent_1", payload)

        assert score == 0.8  # 0.5 + 0.3


class TestLoggingMixinMemoryType:
    """Tests for _determine_memory_type method."""

    def test_memory_type_long_term_event(self):
        logger = MockLoggingLogger()

        mem_type = logger._determine_memory_type("orchestrator.end", 0.5)

        assert mem_type == "long_term"

    def test_memory_type_high_importance(self):
        logger = MockLoggingLogger()

        mem_type = logger._determine_memory_type("agent.start", 0.9)

        assert mem_type == "long_term"

    def test_memory_type_short_term(self):
        logger = MockLoggingLogger()

        mem_type = logger._determine_memory_type("llm.query", 0.5)

        assert mem_type == "short_term"

