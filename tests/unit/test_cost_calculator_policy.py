# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Tests for Cost Calculator Policy Changes
=========================================

Tests the updated default policy for local cost calculation.
"""

import os
from unittest.mock import patch

import pytest

from orka.agents.local_cost_calculator import (
    CostPolicy,
    LocalCostCalculator,
    get_cost_calculator,
)


class TestCostCalculatorPolicy:
    """Test suite for cost calculator policy updates."""

    def test_default_policy_is_calculate(self):
        """Test that the default policy is now 'calculate'."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing cached calculator
            import orka.agents.local_cost_calculator as calc_module
            calc_module._default_calculator = None
            
            calculator = get_cost_calculator()
            
            assert calculator.policy == CostPolicy.CALCULATE

    def test_zero_legacy_via_env_variable(self):
        """Test that zero_legacy can be set via environment variable."""
        with patch.dict(os.environ, {"ORKA_LOCAL_COST_POLICY": "zero_legacy"}, clear=True):
            # Clear cache
            import orka.agents.local_cost_calculator as calc_module
            calc_module._default_calculator = None
            
            calculator = get_cost_calculator()
            
            assert calculator.policy == CostPolicy.ZERO_LEGACY

    def test_calculate_policy_via_env_variable(self):
        """Test explicit calculate policy via environment variable."""
        with patch.dict(os.environ, {"ORKA_LOCAL_COST_POLICY": "calculate"}, clear=True):
            # Clear cache
            import orka.agents.local_cost_calculator as calc_module
            calc_module._default_calculator = None
            
            calculator = get_cost_calculator()
            
            assert calculator.policy == CostPolicy.CALCULATE

    def test_zero_legacy_returns_zero(self):
        """Test that zero_legacy policy returns 0.0."""
        calculator = LocalCostCalculator(policy="zero_legacy")
        
        cost = calculator.calculate(
            latency_ms=1000.0,
            tokens=100,
            model="test-model",
            provider="ollama"
        )
        
        assert cost == 0.0

    def test_calculate_policy_returns_nonzero(self):
        """Test that calculate policy returns non-zero cost."""
        calculator = LocalCostCalculator(policy="calculate")
        
        cost = calculator.calculate(
            latency_ms=1000.0,
            tokens=100,
            model="test-model:7b",
            provider="ollama"
        )
        
        # Should return some cost > 0
        assert cost > 0.0

    def test_no_deprecation_warning_with_calculate(self, caplog):
        """Test that calculate policy doesn't log warnings."""
        calculator = LocalCostCalculator(policy="calculate")
        
        with caplog.at_level("WARNING"):
            calculator.calculate(
                latency_ms=1000.0,
                tokens=100,
                model="test-model",
                provider="ollama"
            )
        
        # Should not have any warnings
        assert len([r for r in caplog.records if r.levelname == "WARNING"]) == 0

    def test_info_message_with_zero_legacy(self, caplog):
        """Test that zero_legacy logs info (not warning)."""
        calculator = LocalCostCalculator(policy="zero_legacy")
        
        with caplog.at_level("INFO"):
            calculator.calculate(
                latency_ms=1000.0,
                tokens=100,
                model="test-model",
                provider="ollama"
            )
        
        # Should have info message, not warning
        info_messages = [r.message for r in caplog.records if r.levelname == "INFO"]
        assert any("zero cost policy" in msg.lower() for msg in info_messages)
        
        # Should not have warnings
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 0

    def test_policy_enum_values(self):
        """Test that CostPolicy enum has expected values."""
        assert hasattr(CostPolicy, "CALCULATE")
        assert hasattr(CostPolicy, "ZERO_LEGACY")
        assert hasattr(CostPolicy, "NULL_FAIL")

    def test_calculator_initialization_with_string(self):
        """Test that calculator accepts string policy names."""
        calc1 = LocalCostCalculator(policy="calculate")
        calc2 = LocalCostCalculator(policy="zero_legacy")
        calc3 = LocalCostCalculator(policy="null_fail")
        
        assert calc1.policy == CostPolicy.CALCULATE
        assert calc2.policy == CostPolicy.ZERO_LEGACY
        assert calc3.policy == CostPolicy.NULL_FAIL


class TestCostCalculation:
    """Test actual cost calculation logic."""

    def test_calculate_includes_electricity_cost(self):
        """Test that calculate policy includes electricity costs."""
        calculator = LocalCostCalculator(
            policy="calculate",
            electricity_rate=0.28,  # $/kWh
            gpu_tdp=450,  # watts
            cpu_tdp=360,  # watts
        )
        
        # 1 second of inference
        cost = calculator.calculate(
            latency_ms=1000.0,
            tokens=100,
            model="llama3:7b",
            provider="ollama"
        )
        
        # Should be a small but non-zero cost
        assert 0.0 < cost < 0.01  # Less than a cent

    def test_calculate_scales_with_latency(self):
        """Test that cost scales with inference time."""
        calculator = LocalCostCalculator(policy="calculate")
        
        cost_1s = calculator.calculate(
            latency_ms=1000.0, tokens=100, model="test:7b", provider="ollama"
        )
        
        cost_2s = calculator.calculate(
            latency_ms=2000.0, tokens=100, model="test:7b", provider="ollama"
        )
        
        # 2s should cost approximately twice as much as 1s
        assert cost_2s > cost_1s
        assert 1.8 < (cost_2s / cost_1s) < 2.2  # Allow some tolerance

