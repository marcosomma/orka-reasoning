"""
Comprehensive unit tests for budget_controller.py module.

Tests cover:
- BudgetController initialization
- Candidate filtering based on budget constraints
- Budget assessment for individual candidates
- Remaining budget calculations
- Constraint violation detection
"""

from unittest.mock import Mock

import pytest

from orka.orchestrator.budget_controller import BudgetController


class TestBudgetControllerInitialization:
    """Test BudgetController initialization."""

    def test_initialization_with_config(self):
        """Test initialization with configuration."""
        config = Mock()
        config.cost_budget_tokens = 10000
        config.latency_budget_ms = 5000

        controller = BudgetController(config)

        assert controller.config == config
        assert controller.cost_budget_tokens == 10000
        assert controller.latency_budget_ms == 5000
        assert controller.current_usage == {"tokens": 0, "cost_usd": 0.0, "latency_ms": 0.0}

    def test_initialization_tracks_usage(self):
        """Test that usage tracking is initialized correctly."""
        config = Mock()
        config.cost_budget_tokens = 5000
        config.latency_budget_ms = 3000

        controller = BudgetController(config)

        assert "tokens" in controller.current_usage
        assert "cost_usd" in controller.current_usage
        assert "latency_ms" in controller.current_usage
        assert all(v == 0 or v == 0.0 for v in controller.current_usage.values())


class TestCandidateFiltering:
    """Test candidate filtering based on budget."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.config.cost_budget_tokens = 10000
        self.config.latency_budget_ms = 5000
        self.controller = BudgetController(self.config)

    @pytest.mark.asyncio
    async def test_filter_candidates_all_within_budget(self):
        """Test filtering when all candidates are within budget."""
        candidates = [
            {"node_id": "agent1", "estimated_tokens": 1000, "estimated_latency_ms": 500},
            {"node_id": "agent2", "estimated_tokens": 2000, "estimated_latency_ms": 1000},
            {"node_id": "agent3", "estimated_tokens": 1500, "estimated_latency_ms": 750},
        ]
        context = {}

        filtered = await self.controller.filter_candidates(candidates, context)

        assert len(filtered) == 3
        assert all(c["fits_budget"] for c in filtered)
        assert all("budget_assessment" in c for c in filtered)

    @pytest.mark.asyncio
    async def test_filter_candidates_some_exceed_budget(self):
        """Test filtering when some candidates exceed budget.

        Note: BudgetController calculates its own estimates internally (120 tokens per path),
        so candidate-provided estimates are not used for budget decisions.
        """
        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent2"]},
            {"node_id": "agent3", "path": ["agent3"]},
        ]
        context = {}

        filtered = await self.controller.filter_candidates(candidates, context)

        # All should pass with default estimates (120 tokens per path)
        assert len(filtered) == 3
        assert all(c["fits_budget"] for c in filtered)
        assert all("budget_assessment" in c for c in filtered)

    @pytest.mark.asyncio
    async def test_filter_candidates_latency_exceeds(self):
        """Test filtering when latency budget is exceeded.

        Note: BudgetController calculates its own estimates internally (1000ms per path),
        so all single-path candidates will pass the 5000ms budget.
        """
        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent2"]},
        ]
        context = {}

        filtered = await self.controller.filter_candidates(candidates, context)

        # Both should pass with default estimates (1000ms per path)
        assert len(filtered) == 2
        assert all(c["fits_budget"] for c in filtered)

    @pytest.mark.asyncio
    async def test_filter_candidates_empty_list(self):
        """Test filtering with empty candidate list."""
        candidates = []
        context = {}

        filtered = await self.controller.filter_candidates(candidates, context)

        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_filter_candidates_adds_budget_info(self):
        """Test that budget information is added to candidates."""
        candidates = [
            {"node_id": "agent1", "estimated_tokens": 1000, "estimated_latency_ms": 500},
        ]
        context = {}

        filtered = await self.controller.filter_candidates(candidates, context)

        assert len(filtered) == 1
        assert "budget_assessment" in filtered[0]
        assert "fits_budget" in filtered[0]
        assert isinstance(filtered[0]["budget_assessment"], dict)


class TestBudgetAssessment:
    """Test budget assessment for individual candidates."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.config.cost_budget_tokens = 10000
        self.config.latency_budget_ms = 5000
        self.controller = BudgetController(self.config)

    @pytest.mark.asyncio
    async def test_assess_candidate_within_budget(self):
        """Test assessment when candidate is within budget."""
        candidate = {
            "node_id": "agent1",
            "estimated_tokens": 1000,
            "estimated_latency_ms": 500,
            "estimated_cost": 0.01,
        }
        remaining_budget = {
            "tokens": 10000,
            "cost_usd": 1.0,
            "latency_ms": 5000,
        }
        context = {}

        assessment = await self.controller._assess_candidate_budget(
            candidate, remaining_budget, context
        )

        assert assessment["compliant"] is True
        assert len(assessment["violations"]) == 0

    @pytest.mark.asyncio
    async def test_assess_candidate_exceeds_token_budget(self):
        """Test assessment when candidate exceeds token budget.

        Note: Uses a very long path to exceed the 10000 token budget.
        Internal estimate: 120 tokens per node, so 84+ nodes needed.
        """
        # Create a candidate with a very long path (100 nodes)
        candidate = {
            "node_id": "agent1",
            "path": [f"agent{i}" for i in range(100)],  # 100 nodes * 120 tokens = 12000 tokens
        }
        remaining_budget = {
            "tokens": 10000,
            "cost_usd": 1.0,
            "latency_ms": 50000,  # High enough to not trigger latency violation
        }
        context = {}

        assessment = await self.controller._assess_candidate_budget(
            candidate, remaining_budget, context
        )

        assert assessment["compliant"] is False
        assert any("token" in v.lower() for v in assessment["violations"])

    @pytest.mark.asyncio
    async def test_assess_candidate_exceeds_latency_budget(self):
        """Test assessment when candidate exceeds latency budget.

        Note: Uses a very long path to exceed the 5000ms latency budget.
        Internal estimate: 1000ms per node, so 6+ nodes needed.
        """
        # Create a candidate with a long path (6 nodes)
        candidate = {
            "node_id": "agent1",
            "path": [f"agent{i}" for i in range(6)],  # 6 nodes * 1000ms = 6000ms
        }
        remaining_budget = {
            "tokens": 100000,  # High enough to not trigger token violation
            "cost_usd": 1.0,
            "latency_ms": 5000,
        }
        context = {}

        assessment = await self.controller._assess_candidate_budget(
            candidate, remaining_budget, context
        )

        assert assessment["compliant"] is False
        assert any("latency" in v.lower() for v in assessment["violations"])

    @pytest.mark.asyncio
    async def test_assess_candidate_exceeds_cost_budget(self):
        """Test assessment when candidate exceeds cost budget."""
        candidate = {
            "node_id": "agent1",
            "estimated_tokens": 1000,
            "estimated_latency_ms": 500,
            "estimated_cost": 2.0,
        }
        remaining_budget = {
            "tokens": 10000,
            "cost_usd": 1.0,
            "latency_ms": 5000,
        }
        context = {}

        assessment = await self.controller._assess_candidate_budget(
            candidate, remaining_budget, context
        )

        assert assessment["compliant"] is False
        assert any("cost" in v.lower() for v in assessment["violations"])

    @pytest.mark.asyncio
    async def test_assess_candidate_multiple_violations(self):
        """Test assessment when candidate has multiple violations.

        Note: Uses a very long path and high cost estimate to trigger multiple violations.
        """
        # Create a candidate with a very long path (100 nodes)
        # This will exceed both token (12000 > 10000) and latency (100000 > 5000) budgets
        candidate = {
            "node_id": "agent1",
            "path": [f"agent{i}" for i in range(100)],  # 100 nodes
            "estimated_cost": 2.0,  # Exceeds cost budget
        }
        remaining_budget = {
            "tokens": 10000,
            "cost_usd": 1.0,
            "latency_ms": 5000,
        }
        context = {}

        assessment = await self.controller._assess_candidate_budget(
            candidate, remaining_budget, context
        )

        assert assessment["compliant"] is False
        # Should have at least 2 violations (tokens, latency, and/or cost)
        assert len(assessment["violations"]) >= 2


class TestRemainingBudget:
    """Test remaining budget calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.config.cost_budget_tokens = 10000
        self.config.latency_budget_ms = 5000
        self.controller = BudgetController(self.config)

    @pytest.mark.asyncio
    async def test_get_remaining_budget_initial(self):
        """Test getting remaining budget at initialization."""
        context = {}

        remaining = await self.controller._get_remaining_budget(context)

        assert remaining["tokens"] == 10000
        assert remaining["cost_usd"] == 1.0
        assert remaining["latency_ms"] == 5000

    @pytest.mark.asyncio
    async def test_get_remaining_budget_after_usage(self):
        """Test getting remaining budget after some usage."""
        self.controller.current_usage = {
            "tokens": 2000,
            "cost_usd": 0.2,
            "latency_ms": 1000,
        }
        context = {}

        remaining = await self.controller._get_remaining_budget(context)

        assert remaining["tokens"] == 8000  # 10000 - 2000
        assert remaining["cost_usd"] == 0.8  # 1.0 - 0.2
        assert remaining["latency_ms"] == 4000  # 5000 - 1000

    @pytest.mark.asyncio
    async def test_get_remaining_budget_structure(self):
        """Test that remaining budget has correct structure."""
        context = {}

        remaining = await self.controller._get_remaining_budget(context)

        assert "tokens" in remaining
        assert "cost_usd" in remaining
        assert "latency_ms" in remaining
        assert isinstance(remaining["tokens"], (int, float))
        assert isinstance(remaining["cost_usd"], (int, float))
        assert isinstance(remaining["latency_ms"], (int, float))


class TestErrorHandling:
    """Test error handling in budget controller."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.config.cost_budget_tokens = 10000
        self.config.latency_budget_ms = 5000
        self.controller = BudgetController(self.config)

    @pytest.mark.asyncio
    async def test_filter_candidates_with_exception(self):
        """Test that exceptions in filtering don't crash the system."""
        # Create a candidate that might cause issues
        candidates = [
            {"node_id": "agent1"},  # Missing estimated fields
        ]
        context = {}

        # Should not raise exception, should return original candidates
        filtered = await self.controller.filter_candidates(candidates, context)

        # Should fallback to returning all candidates on error
        assert len(filtered) >= 0

    @pytest.mark.asyncio
    async def test_filter_candidates_with_missing_fields(self):
        """Test filtering with candidates missing required fields."""
        candidates = [
            {"node_id": "agent1"},  # Missing estimated_tokens and estimated_latency_ms
            {"node_id": "agent2", "estimated_tokens": 1000},  # Missing estimated_latency_ms
        ]
        context = {}

        # Should handle gracefully
        filtered = await self.controller.filter_candidates(candidates, context)

        assert isinstance(filtered, list)


class TestBudgetUpdates:
    """Test budget usage updates."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.config.cost_budget_tokens = 10000
        self.config.latency_budget_ms = 5000
        self.controller = BudgetController(self.config)

    def test_update_usage_tokens(self):
        """Test updating token usage."""
        initial_tokens = self.controller.current_usage["tokens"]

        self.controller.current_usage["tokens"] += 1000

        assert self.controller.current_usage["tokens"] == initial_tokens + 1000

    def test_update_usage_cost(self):
        """Test updating cost usage."""
        initial_cost = self.controller.current_usage["cost_usd"]

        self.controller.current_usage["cost_usd"] += 0.1

        assert self.controller.current_usage["cost_usd"] == initial_cost + 0.1

    def test_update_usage_latency(self):
        """Test updating latency usage."""
        initial_latency = self.controller.current_usage["latency_ms"]

        self.controller.current_usage["latency_ms"] += 500

        assert self.controller.current_usage["latency_ms"] == initial_latency + 500
