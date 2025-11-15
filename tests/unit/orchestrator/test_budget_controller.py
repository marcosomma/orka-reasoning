"""Unit tests for orka.orchestrator.budget_controller."""

import pytest
from unittest.mock import Mock, AsyncMock

from orka.orchestrator.budget_controller import BudgetController

# Mark all tests in this module for unit testing
pytestmark = [pytest.mark.unit]


class TestBudgetController:
    """Test suite for BudgetController class."""

    def create_mock_config(self, cost_budget_tokens=1000, latency_budget_ms=10000):
        """Helper to create a mock config object."""
        config = Mock()
        config.cost_budget_tokens = cost_budget_tokens
        config.latency_budget_ms = latency_budget_ms
        return config

    def test_init(self):
        """Test BudgetController initialization."""
        config = self.create_mock_config(cost_budget_tokens=2000, latency_budget_ms=5000)
        controller = BudgetController(config)

        assert controller.cost_budget_tokens == 2000
        assert controller.latency_budget_ms == 5000
        assert controller.current_usage["tokens"] == 0
        assert controller.current_usage["cost_usd"] == 0.0
        assert controller.current_usage["latency_ms"] == 0.0

    @pytest.mark.asyncio
    async def test_get_remaining_budget_initial(self):
        """Test _get_remaining_budget with no usage."""
        config = self.create_mock_config(cost_budget_tokens=1000, latency_budget_ms=10000)
        controller = BudgetController(config)

        context = {}
        remaining = await controller._get_remaining_budget(context)

        assert remaining["tokens"] == 1000
        assert remaining["cost_usd"] == 1.0
        assert remaining["latency_ms"] == 10000

    @pytest.mark.asyncio
    async def test_get_remaining_budget_with_usage(self):
        """Test _get_remaining_budget with existing usage."""
        config = self.create_mock_config(cost_budget_tokens=1000, latency_budget_ms=10000)
        controller = BudgetController(config)
        controller.current_usage = {"tokens": 200, "cost_usd": 0.1, "latency_ms": 2000}

        context = {}
        remaining = await controller._get_remaining_budget(context)

        assert remaining["tokens"] == 800
        assert remaining["cost_usd"] == 0.9
        assert remaining["latency_ms"] == 8000

    @pytest.mark.asyncio
    async def test_get_remaining_budget_exception(self):
        """Test _get_remaining_budget handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)
        controller.cost_budget_tokens = None  # Cause exception

        context = {}
        remaining = await controller._get_remaining_budget(context)

        # Should return default values on error
        assert "tokens" in remaining
        assert "cost_usd" in remaining
        assert "latency_ms" in remaining

    @pytest.mark.asyncio
    async def test_estimate_tokens_with_path(self):
        """Test _estimate_tokens with path."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "path": ["agent1", "agent2", "agent3"]}
        context = {}

        tokens = await controller._estimate_tokens(candidate, context)

        # 3 nodes * 100 base * 1.2 buffer = 360
        assert tokens == 360

    @pytest.mark.asyncio
    async def test_estimate_tokens_without_path(self):
        """Test _estimate_tokens without path (uses node_id)."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1"}  # No path
        context = {}

        tokens = await controller._estimate_tokens(candidate, context)

        # 1 node * 100 base * 1.2 buffer = 120
        assert tokens == 120

    @pytest.mark.asyncio
    async def test_estimate_tokens_exception(self):
        """Test _estimate_tokens handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {}  # Missing node_id
        context = {}

        tokens = await controller._estimate_tokens(candidate, context)

        # Should return fallback value
        assert tokens == 200

    @pytest.mark.asyncio
    async def test_estimate_cost_with_estimated_cost(self):
        """Test _estimate_cost uses pre-calculated estimate."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "estimated_cost": 0.05}
        context = {}

        cost = await controller._estimate_cost(candidate, context)

        assert cost == 0.05

    @pytest.mark.asyncio
    async def test_estimate_cost_fallback(self):
        """Test _estimate_cost uses fallback estimation."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "path": ["agent1", "agent2"]}
        context = {}

        cost = await controller._estimate_cost(candidate, context)

        # Should calculate based on token estimate
        assert cost > 0
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_exception(self):
        """Test _estimate_cost handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {}  # Missing node_id
        context = {}

        cost = await controller._estimate_cost(candidate, context)

        # Token estimation fails and returns 200, then cost is calculated from that
        # 200 tokens / 1000 * 0.002 = 0.0004
        assert cost > 0
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_latency_with_estimated_latency(self):
        """Test _estimate_latency uses pre-calculated estimate."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "estimated_latency": 5000}
        context = {}

        latency = await controller._estimate_latency(candidate, context)

        assert latency == 5000.0

    @pytest.mark.asyncio
    async def test_estimate_latency_fallback(self):
        """Test _estimate_latency uses fallback estimation."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "path": ["agent1", "agent2", "agent3"]}
        context = {}

        latency = await controller._estimate_latency(candidate, context)

        # 3 nodes * 1000ms = 3000ms
        assert latency == 3000.0

    @pytest.mark.asyncio
    async def test_estimate_latency_exception(self):
        """Test _estimate_latency handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {}  # Missing node_id
        context = {}

        latency = await controller._estimate_latency(candidate, context)

        # Should return fallback value
        assert latency == 2000.0

    @pytest.mark.asyncio
    async def test_assess_candidate_budget_compliant(self):
        """Test _assess_candidate_budget with compliant candidate."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1"],
            "estimated_cost": 0.01,
            "estimated_latency": 1000,
        }
        remaining_budget = {"tokens": 500, "cost_usd": 0.5, "latency_ms": 5000}
        context = {}

        assessment = await controller._assess_candidate_budget(candidate, remaining_budget, context)

        assert assessment["compliant"] is True
        assert len(assessment["violations"]) == 0
        assert "estimates" in assessment
        assert "remaining_budget" in assessment

    @pytest.mark.asyncio
    async def test_assess_candidate_budget_token_violation(self):
        """Test _assess_candidate_budget with token violation."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "path": ["agent1"] * 10}  # Long path
        remaining_budget = {"tokens": 100, "cost_usd": 1.0, "latency_ms": 10000}
        context = {}

        assessment = await controller._assess_candidate_budget(candidate, remaining_budget, context)

        assert assessment["compliant"] is False
        assert len(assessment["violations"]) > 0
        assert any("tokens" in v for v in assessment["violations"])

    @pytest.mark.asyncio
    async def test_assess_candidate_budget_cost_violation(self):
        """Test _assess_candidate_budget with cost violation."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "estimated_cost": 0.6}
        remaining_budget = {"tokens": 1000, "cost_usd": 0.5, "latency_ms": 10000}
        context = {}

        assessment = await controller._assess_candidate_budget(candidate, remaining_budget, context)

        assert assessment["compliant"] is False
        assert any("cost" in v for v in assessment["violations"])

    @pytest.mark.asyncio
    async def test_assess_candidate_budget_latency_violation(self):
        """Test _assess_candidate_budget with latency violation."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {"node_id": "agent1", "estimated_latency": 15000}
        remaining_budget = {"tokens": 1000, "cost_usd": 1.0, "latency_ms": 10000}
        context = {}

        assessment = await controller._assess_candidate_budget(candidate, remaining_budget, context)

        assert assessment["compliant"] is False
        assert any("latency" in v for v in assessment["violations"])

    @pytest.mark.asyncio
    async def test_assess_candidate_budget_exception(self):
        """Test _assess_candidate_budget handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidate = {}  # Invalid candidate - will use fallback estimates
        remaining_budget = {"tokens": 1000, "cost_usd": 1.0, "latency_ms": 10000}
        context = {}

        assessment = await controller._assess_candidate_budget(candidate, remaining_budget, context)

        # Should default to compliant on error (fallback estimates are small)
        assert assessment["compliant"] is True
        assert "estimates" in assessment

    @pytest.mark.asyncio
    async def test_filter_candidates_all_compliant(self):
        """Test filter_candidates with all compliant candidates."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidates = [
            {"node_id": "agent1", "estimated_cost": 0.01, "estimated_latency": 1000},
            {"node_id": "agent2", "estimated_cost": 0.02, "estimated_latency": 2000},
        ]
        context = {}

        filtered = await controller.filter_candidates(candidates, context)

        assert len(filtered) == 2
        assert all(c["fits_budget"] for c in filtered)

    @pytest.mark.asyncio
    async def test_filter_candidates_some_non_compliant(self):
        """Test filter_candidates with some non-compliant candidates."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidates = [
            {"node_id": "agent1", "estimated_cost": 0.01, "estimated_latency": 1000},
            {"node_id": "agent2", "estimated_cost": 2.0, "estimated_latency": 2000},  # Exceeds budget
        ]
        context = {}

        filtered = await controller.filter_candidates(candidates, context)

        assert len(filtered) == 1
        assert filtered[0]["node_id"] == "agent1"

    @pytest.mark.asyncio
    async def test_filter_candidates_all_non_compliant(self):
        """Test filter_candidates with all non-compliant candidates."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidates = [
            {"node_id": "agent1", "estimated_cost": 2.0, "estimated_latency": 20000},
            {"node_id": "agent2", "estimated_cost": 3.0, "estimated_latency": 30000},
        ]
        context = {}

        filtered = await controller.filter_candidates(candidates, context)

        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_filter_candidates_exception(self):
        """Test filter_candidates handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        candidates = [{"invalid": "candidate"}]
        context = {}

        # Should return all candidates on error
        filtered = await controller.filter_candidates(candidates, context)

        assert len(filtered) == 1

    @pytest.mark.asyncio
    async def test_update_usage(self):
        """Test update_usage updates current usage."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        await controller.update_usage(tokens_used=100, cost_incurred=0.01, latency_ms=500)

        assert controller.current_usage["tokens"] == 100
        assert controller.current_usage["cost_usd"] == 0.01
        assert controller.current_usage["latency_ms"] == 500.0

    @pytest.mark.asyncio
    async def test_update_usage_accumulative(self):
        """Test update_usage accumulates usage."""
        config = self.create_mock_config()
        controller = BudgetController(config)

        await controller.update_usage(tokens_used=100, cost_incurred=0.01, latency_ms=500)
        await controller.update_usage(tokens_used=50, cost_incurred=0.005, latency_ms=300)

        assert controller.current_usage["tokens"] == 150
        assert controller.current_usage["cost_usd"] == 0.015
        assert controller.current_usage["latency_ms"] == 800.0

    @pytest.mark.asyncio
    async def test_update_usage_exception(self):
        """Test update_usage handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)
        controller.current_usage = None  # Cause exception

        # Should not raise exception
        await controller.update_usage(tokens_used=100, cost_incurred=0.01, latency_ms=500)

    def test_get_usage_summary(self):
        """Test get_usage_summary returns correct summary."""
        config = self.create_mock_config(cost_budget_tokens=1000, latency_budget_ms=10000)
        controller = BudgetController(config)
        controller.current_usage = {"tokens": 200, "cost_usd": 0.1, "latency_ms": 2000}

        summary = controller.get_usage_summary()

        assert "current_usage" in summary
        assert "budget_limits" in summary
        assert "utilization" in summary
        assert summary["current_usage"]["tokens"] == 200
        assert summary["budget_limits"]["tokens"] == 1000
        assert summary["utilization"]["tokens"] == 0.2  # 200/1000

    def test_get_usage_summary_exception(self):
        """Test get_usage_summary handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)
        controller.current_usage = None  # Cause exception

        summary = controller.get_usage_summary()

        assert "error" in summary

    def test_is_budget_exhausted_false(self):
        """Test is_budget_exhausted returns False when budget not exhausted."""
        config = self.create_mock_config(cost_budget_tokens=1000, latency_budget_ms=10000)
        controller = BudgetController(config)
        controller.current_usage = {"tokens": 100, "cost_usd": 0.1, "latency_ms": 1000}

        exhausted = controller.is_budget_exhausted(threshold=0.9)

        assert exhausted is False

    def test_is_budget_exhausted_true(self):
        """Test is_budget_exhausted returns True when budget exhausted."""
        config = self.create_mock_config(cost_budget_tokens=1000, latency_budget_ms=10000)
        controller = BudgetController(config)
        controller.current_usage = {"tokens": 950, "cost_usd": 0.95, "latency_ms": 9500}

        exhausted = controller.is_budget_exhausted(threshold=0.9)

        assert exhausted is True

    def test_is_budget_exhausted_custom_threshold(self):
        """Test is_budget_exhausted with custom threshold."""
        config = self.create_mock_config(cost_budget_tokens=1000, latency_budget_ms=10000)
        controller = BudgetController(config)
        controller.current_usage = {"tokens": 800, "cost_usd": 0.8, "latency_ms": 8000}

        exhausted_high = controller.is_budget_exhausted(threshold=0.9)
        exhausted_low = controller.is_budget_exhausted(threshold=0.7)

        assert exhausted_high is False
        assert exhausted_low is True

    def test_is_budget_exhausted_exception(self):
        """Test is_budget_exhausted handles exceptions."""
        config = self.create_mock_config()
        controller = BudgetController(config)
        controller.current_usage = None  # Cause exception

        exhausted = controller.is_budget_exhausted()

        assert exhausted is False

