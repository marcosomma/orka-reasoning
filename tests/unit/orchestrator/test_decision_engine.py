"""Unit tests for orka.orchestrator.decision_engine."""

import pytest
from unittest.mock import Mock

from orka.orchestrator.decision_engine import DecisionEngine

# Mark all tests in this module for unit testing
pytestmark = [pytest.mark.unit]


class TestDecisionEngine:
    """Test suite for DecisionEngine class."""

    def create_mock_config(
        self,
        commit_margin=0.1,
        k_beam=3,
        require_terminal=True,
        max_depth=4,
        optimal_path_length=(2, 3),
    ):
        """Helper to create a mock config object."""
        config = Mock()
        config.commit_margin = commit_margin
        config.k_beam = k_beam
        config.require_terminal = require_terminal
        config.max_depth = max_depth
        config.optimal_path_length = optimal_path_length
        return config

    def test_init(self):
        """Test DecisionEngine initialization."""
        config = self.create_mock_config(commit_margin=0.15, k_beam=5, require_terminal=False)
        engine = DecisionEngine(config)

        assert engine.commit_margin == 0.15
        assert engine.k_beam == 5
        assert engine.require_terminal is False

    def test_init_default_require_terminal(self):
        """Test DecisionEngine initialization with default require_terminal."""
        # Use a simple object instead of Mock to avoid auto-attribute creation
        class SimpleConfig:
            commit_margin = 0.1
            k_beam = 3
            # require_terminal not set, should use default True

        config = SimpleConfig()
        engine = DecisionEngine(config)

        assert engine.require_terminal is True

    @pytest.mark.asyncio
    async def test_make_decision_empty_candidates(self):
        """Test make_decision with empty candidates."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        decision = await engine.make_decision([], {})

        assert decision["decision_type"] == "fallback"
        assert decision["target"] is None
        assert decision["confidence"] == 0.0
        assert "No candidates available" in decision["reasoning"]

    @pytest.mark.asyncio
    async def test_make_decision_single_candidate_high_score(self):
        """Test make_decision with single high-score candidate."""
        config = self.create_mock_config(require_terminal=False)
        engine = DecisionEngine(config)

        candidates = [{"node_id": "agent1", "path": ["agent1"], "score": 0.8, "confidence": 0.7}]
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "commit_next"
        assert decision["target"] == "agent1"
        assert decision["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_make_decision_single_candidate_low_score(self):
        """Test make_decision with single low-score candidate."""
        config = self.create_mock_config(require_terminal=False)
        engine = DecisionEngine(config)

        candidates = [{"node_id": "agent1", "path": ["agent1"], "score": 0.5, "confidence": 0.4}]
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "shortlist"
        assert decision["target"] == candidates

    @pytest.mark.asyncio
    async def test_make_decision_single_candidate_path(self):
        """Test make_decision with single candidate that has a path."""
        config = self.create_mock_config(require_terminal=False)
        engine = DecisionEngine(config)

        candidates = [
            {
                "node_id": "agent1",
                "path": ["agent1", "agent2"],
                "score": 0.8,
                "confidence": 0.7,
            }
        ]
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "commit_path"
        assert decision["target"] == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_make_decision_high_confidence_single_node(self):
        """Test make_decision with high confidence margin, single node."""
        config = self.create_mock_config(commit_margin=0.1, require_terminal=False)
        engine = DecisionEngine(config)

        candidates = [
            {"node_id": "agent1", "path": ["agent1"], "score": 0.9, "confidence": 0.8},
            {"node_id": "agent2", "path": ["agent2"], "score": 0.7, "confidence": 0.6},
        ]
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "commit_next"
        assert decision["target"] == "agent1"
        assert decision["confidence"] > 0.8  # Boosted by margin

    @pytest.mark.asyncio
    async def test_make_decision_high_confidence_path(self):
        """Test make_decision with high confidence margin, path."""
        config = self.create_mock_config(commit_margin=0.1, require_terminal=False)
        engine = DecisionEngine(config)

        candidates = [
            {
                "node_id": "agent1",
                "path": ["agent1", "agent2"],
                "score": 0.9,
                "confidence": 0.8,
            },
            {"node_id": "agent3", "path": ["agent3"], "score": 0.7, "confidence": 0.6},
        ]
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "commit_path"
        assert decision["target"] == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_make_decision_low_confidence_shortlist(self):
        """Test make_decision with low confidence margin returns shortlist."""
        config = self.create_mock_config(commit_margin=0.1, k_beam=2, require_terminal=False)
        engine = DecisionEngine(config)

        candidates = [
            {"node_id": "agent1", "path": ["agent1"], "score": 0.75, "confidence": 0.7},
            {"node_id": "agent2", "path": ["agent2"], "score": 0.74, "confidence": 0.69},
            {"node_id": "agent3", "path": ["agent3"], "score": 0.5, "confidence": 0.4},
        ]
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "shortlist"
        assert len(decision["target"]) == 2  # k_beam = 2
        assert decision["confidence"] < 0.7  # Penalized

    @pytest.mark.asyncio
    async def test_make_decision_exception(self):
        """Test make_decision handles exceptions."""
        config = self.create_mock_config(require_terminal=False)
        engine = DecisionEngine(config)

        # Create candidates that will cause exception in sorting
        candidates = [None]  # Invalid candidate type
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "fallback"
        assert "error" in decision["reasoning"]

    def test_find_terminal_paths_2_hop(self):
        """Test _find_terminal_paths finds 2-hop terminal paths."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidates = [
            {
                "node_id": "agent1",
                "path": ["agent1", "response_builder"],
                "score": 0.9,
            },
            {"node_id": "agent2", "path": ["agent2"], "score": 0.8},
        ]
        context = {}

        terminal_paths = engine._find_terminal_paths(candidates, context)

        assert len(terminal_paths) == 1
        assert terminal_paths[0]["node_id"] == "agent1"

    def test_find_terminal_paths_longer_paths(self):
        """Test _find_terminal_paths finds longer terminal paths."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidates = [
            {
                "node_id": "agent1",
                "path": ["agent1", "agent2", "agent3", "response_builder"],
                "score": 0.9,
            },
            {"node_id": "agent2", "path": ["agent2"], "score": 0.8},
        ]
        context = {}

        terminal_paths = engine._find_terminal_paths(candidates, context)

        assert len(terminal_paths) == 1

    def test_find_terminal_paths_no_terminals(self):
        """Test _find_terminal_paths returns empty when no terminals."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidates = [
            {"node_id": "agent1", "path": ["agent1", "agent2"], "score": 0.9},
            {"node_id": "agent2", "path": ["agent2"], "score": 0.8},
        ]
        context = {}

        terminal_paths = engine._find_terminal_paths(candidates, context)

        assert len(terminal_paths) == 0

    def test_find_terminal_paths_sorted_by_score(self):
        """Test _find_terminal_paths sorts by score."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidates = [
            {
                "node_id": "agent1",
                "path": ["agent1", "response_builder"],
                "score": 0.7,
            },
            {
                "node_id": "agent2",
                "path": ["agent2", "response_builder"],
                "score": 0.9,
            },
        ]
        context = {}

        terminal_paths = engine._find_terminal_paths(candidates, context)

        assert len(terminal_paths) == 2
        assert terminal_paths[0]["score"] == 0.9  # Highest first

    def test_find_terminal_paths_exception(self):
        """Test _find_terminal_paths handles exceptions."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidates = [{"invalid": "candidate"}]
        context = {}

        terminal_paths = engine._find_terminal_paths(candidates, context)

        assert terminal_paths == []

    def test_get_dynamic_margin_factual(self):
        """Test _get_dynamic_margin for factual queries."""
        config = self.create_mock_config(commit_margin=0.1)
        engine = DecisionEngine(config)

        context = {
            "previous_outputs": {
                "input_classifier": {"response": "This is a factual query"}
            }
        }

        margin = engine._get_dynamic_margin(context)

        assert margin == 0.08

    def test_get_dynamic_margin_analytical(self):
        """Test _get_dynamic_margin for analytical queries."""
        config = self.create_mock_config(commit_margin=0.1)
        engine = DecisionEngine(config)

        context = {
            "previous_outputs": {
                "input_classifier": {"response": "This is an analytical query"}
            }
        }

        margin = engine._get_dynamic_margin(context)

        assert margin == 0.15

    def test_get_dynamic_margin_technical(self):
        """Test _get_dynamic_margin for technical queries."""
        config = self.create_mock_config(commit_margin=0.1)
        engine = DecisionEngine(config)

        context = {
            "previous_outputs": {
                "input_classifier": {"response": "This is a technical query"}
            }
        }

        margin = engine._get_dynamic_margin(context)

        assert margin == 0.12

    def test_get_dynamic_margin_creative(self):
        """Test _get_dynamic_margin for creative queries."""
        config = self.create_mock_config(commit_margin=0.1)
        engine = DecisionEngine(config)

        context = {
            "previous_outputs": {
                "input_classifier": {"response": "This is a creative query"}
            }
        }

        margin = engine._get_dynamic_margin(context)

        assert margin == 0.2

    def test_get_dynamic_margin_fallback(self):
        """Test _get_dynamic_margin falls back to base margin."""
        config = self.create_mock_config(commit_margin=0.1)
        engine = DecisionEngine(config)

        context = {"previous_outputs": {}}

        margin = engine._get_dynamic_margin(context)

        assert margin == 0.1

    def test_get_dynamic_margin_string_classification(self):
        """Test _get_dynamic_margin with string classification."""
        config = self.create_mock_config(commit_margin=0.1)
        engine = DecisionEngine(config)

        context = {
            "previous_outputs": {"input_classifier": "factual query response"}
        }

        margin = engine._get_dynamic_margin(context)

        assert margin == 0.08

    def test_get_dynamic_margin_exception(self):
        """Test _get_dynamic_margin handles exceptions."""
        config = self.create_mock_config(commit_margin=0.1)
        engine = DecisionEngine(config)

        context = None  # Cause exception

        margin = engine._get_dynamic_margin(context)

        assert margin == 0.1  # Fallback to base

    def test_is_response_builder_by_capabilities(self):
        """Test _is_response_builder detects by capabilities."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        mock_node = Mock()
        mock_node.capabilities = ["answer_emit", "text_generation"]

        mock_graph_state = Mock()
        mock_graph_state.nodes = {"response_agent": mock_node}

        context = {"graph_state": mock_graph_state}

        is_builder = engine._is_response_builder("response_agent", context)

        assert is_builder is True

    def test_is_response_builder_by_name_pattern(self):
        """Test _is_response_builder detects by name pattern."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        context = {}

        is_builder = engine._is_response_builder("response_builder", context)

        assert is_builder is True

    def test_is_response_builder_by_name_pattern_variations(self):
        """Test _is_response_builder detects various name patterns."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        context = {}

        assert engine._is_response_builder("answer_builder", context) is True
        assert engine._is_response_builder("final_response", context) is True
        assert engine._is_response_builder("llm_response", context) is True
        assert engine._is_response_builder("openai_response", context) is True

    def test_is_response_builder_not_builder(self):
        """Test _is_response_builder returns False for non-builders."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        context = {}

        is_builder = engine._is_response_builder("search_agent", context)

        assert is_builder is False

    def test_is_response_builder_exception(self):
        """Test _is_response_builder handles exceptions."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        context = None  # Cause exception

        is_builder = engine._is_response_builder("agent1", context)

        assert is_builder is False

    @pytest.mark.asyncio
    async def test_handle_single_candidate_high_quality_single_node(self):
        """Test _handle_single_candidate with high quality single node."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidate = {"node_id": "agent1", "path": ["agent1"], "score": 0.8, "confidence": 0.7}
        context = {}

        decision = await engine._handle_single_candidate(candidate, context)

        assert decision["decision_type"] == "commit_next"
        assert decision["target"] == "agent1"

    @pytest.mark.asyncio
    async def test_handle_single_candidate_high_quality_path(self):
        """Test _handle_single_candidate with high quality path."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1", "agent2"],
            "score": 0.8,
            "confidence": 0.7,
        }
        context = {}

        decision = await engine._handle_single_candidate(candidate, context)

        assert decision["decision_type"] == "commit_path"
        assert decision["target"] == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_handle_single_candidate_moderate_quality(self):
        """Test _handle_single_candidate with moderate quality."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidate = {"node_id": "agent1", "path": ["agent1"], "score": 0.6, "confidence": 0.5}
        context = {}

        decision = await engine._handle_single_candidate(candidate, context)

        assert decision["decision_type"] == "shortlist"
        assert decision["target"] == [candidate]

    @pytest.mark.asyncio
    async def test_handle_single_candidate_exception(self):
        """Test _handle_single_candidate handles exceptions."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        # Candidate that will cause exception when accessing .get()
        candidate = None  # Invalid candidate type
        context = {}

        decision = await engine._handle_single_candidate(candidate, context)

        assert decision["decision_type"] == "fallback"

    @pytest.mark.asyncio
    async def test_handle_high_confidence_decision_single_node(self):
        """Test _handle_high_confidence_decision with single node."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidate = {"node_id": "agent1", "path": ["agent1"], "score": 0.9, "confidence": 0.8}
        context = {}
        margin = 0.2

        decision = await engine._handle_high_confidence_decision(candidate, margin, context)

        assert decision["decision_type"] == "commit_next"
        assert decision["target"] == "agent1"
        assert decision["confidence"] > 0.8  # Boosted

    @pytest.mark.asyncio
    async def test_handle_high_confidence_decision_path(self):
        """Test _handle_high_confidence_decision with path."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1", "agent2"],
            "score": 0.9,
            "confidence": 0.8,
        }
        context = {}
        margin = 0.2

        decision = await engine._handle_high_confidence_decision(candidate, margin, context)

        assert decision["decision_type"] == "commit_path"
        assert decision["target"] == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_handle_high_confidence_decision_confidence_capped(self):
        """Test _handle_high_confidence_decision caps confidence at 1.0."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidate = {"node_id": "agent1", "path": ["agent1"], "score": 0.9, "confidence": 0.95}
        context = {}
        margin = 0.2  # Large margin would push over 1.0

        decision = await engine._handle_high_confidence_decision(candidate, margin, context)

        assert decision["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_handle_high_confidence_decision_exception(self):
        """Test _handle_high_confidence_decision handles exceptions."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidate = {}  # Invalid candidate
        context = {}
        margin = 0.1

        decision = await engine._handle_high_confidence_decision(candidate, margin, context)

        assert decision["decision_type"] == "fallback"

    @pytest.mark.asyncio
    async def test_handle_low_confidence_decision(self):
        """Test _handle_low_confidence_decision returns shortlist."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidates = [
            {"node_id": "agent1", "score": 0.75, "confidence": 0.7},
            {"node_id": "agent2", "score": 0.74, "confidence": 0.69},
        ]
        context = {}
        margin = 0.01

        decision = await engine._handle_low_confidence_decision(candidates, margin, context)

        assert decision["decision_type"] == "shortlist"
        assert decision["target"] == candidates
        assert decision["confidence"] < 0.7  # Penalized

    @pytest.mark.asyncio
    async def test_handle_low_confidence_decision_empty_candidates(self):
        """Test _handle_low_confidence_decision with empty candidates."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        candidates = []
        context = {}
        margin = 0.01

        decision = await engine._handle_low_confidence_decision(candidates, margin, context)

        assert decision["decision_type"] == "shortlist"
        assert decision["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_handle_low_confidence_decision_exception(self):
        """Test _handle_low_confidence_decision handles exceptions."""
        config = self.create_mock_config()
        engine = DecisionEngine(config)

        # Candidates that will cause exception when accessing .get()
        candidates = [None]  # Invalid candidate type
        context = {}
        margin = 0.01

        decision = await engine._handle_low_confidence_decision(candidates, margin, context)

        assert decision["decision_type"] == "fallback"

    def test_create_decision(self):
        """Test _create_decision creates proper decision object."""
        config = self.create_mock_config(commit_margin=0.15, k_beam=5)
        engine = DecisionEngine(config)

        decision = engine._create_decision(
            "commit_path", ["agent1", "agent2"], 0.8, "Test reasoning"
        )

        assert decision["decision_type"] == "commit_path"
        assert decision["target"] == ["agent1", "agent2"]
        assert decision["confidence"] == 0.8
        assert decision["reasoning"] == "Test reasoning"
        assert "trace" in decision
        assert decision["trace"]["commit_margin"] == 0.15
        assert decision["trace"]["k_beam"] == 5

    @pytest.mark.asyncio
    async def test_make_decision_with_terminal_path(self):
        """Test make_decision prioritizes terminal paths."""
        config = self.create_mock_config(require_terminal=True)
        engine = DecisionEngine(config)

        candidates = [
            {
                "node_id": "agent1",
                "path": ["agent1", "response_builder"],
                "score": 0.8,
                "confidence": 0.7,
            },
            {
                "node_id": "agent2",
                "path": ["agent2", "agent3"],
                "score": 0.9,  # Higher score but not terminal
                "confidence": 0.8,
            },
        ]
        context = {}

        decision = await engine.make_decision(candidates, context)

        assert decision["decision_type"] == "commit_path"
        assert decision["target"] == ["agent1", "response_builder"]

    @pytest.mark.asyncio
    async def test_make_decision_no_terminal_paths_continues(self):
        """Test make_decision continues with normal logic when no terminals."""
        config = self.create_mock_config(require_terminal=True)
        engine = DecisionEngine(config)

        candidates = [
            {"node_id": "agent1", "path": ["agent1", "agent2"], "score": 0.9, "confidence": 0.8},
            {"node_id": "agent2", "path": ["agent2"], "score": 0.7, "confidence": 0.6},
        ]
        context = {}

        decision = await engine.make_decision(candidates, context)

        # Should use normal decision logic (not fallback)
        assert decision["decision_type"] in ["commit_path", "commit_next", "shortlist"]

    @pytest.mark.asyncio
    async def test_make_decision_sorts_candidates(self):
        """Test make_decision sorts candidates by score."""
        config = self.create_mock_config(require_terminal=False)
        engine = DecisionEngine(config)

        candidates = [
            {"node_id": "agent2", "path": ["agent2"], "score": 0.7, "confidence": 0.6},
            {"node_id": "agent1", "path": ["agent1"], "score": 0.9, "confidence": 0.8},
        ]
        context = {}

        decision = await engine.make_decision(candidates, context)

        # Should select agent1 (highest score) even though it was second in list
        assert decision["target"] == "agent1" or decision["target"] == ["agent1"]

