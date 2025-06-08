# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Simple test cases for local cost calculator functionality
"""

import os
from unittest.mock import patch

import pytest

from orka.agents.local_cost_calculator import (
    CostPolicy,
    LocalCostCalculator,
    calculate_local_llm_cost,
    get_cost_calculator,
)


class TestLocalCostCalculator:
    """Test suite for local cost calculator functionality"""

    def test_initialization_default(self):
        """Test default initialization"""
        calculator = LocalCostCalculator()

        assert calculator.policy == CostPolicy.CALCULATE
        assert calculator.electricity_rate > 0
        assert calculator.hardware_cost > 0
        assert calculator.hardware_lifespan_months == 36
        assert calculator.gpu_tdp > 0
        assert calculator.cpu_tdp > 0

    def test_initialization_with_custom_values(self):
        """Test initialization with custom values"""
        calculator = LocalCostCalculator(
            policy="null_fail",
            electricity_rate_usd_per_kwh=0.15,
            hardware_cost_usd=3000.0,
            hardware_lifespan_months=48,
            gpu_tdp_watts=400.0,
            cpu_tdp_watts=200.0,
        )

        assert calculator.policy == CostPolicy.NULL_FAIL
        assert calculator.electricity_rate == 0.15
        assert calculator.hardware_cost == 3000.0
        assert calculator.hardware_lifespan_months == 48
        assert calculator.gpu_tdp == 400.0
        assert calculator.cpu_tdp == 200.0

    def test_initialization_invalid_policy(self):
        """Test initialization with invalid policy raises error"""
        with pytest.raises(ValueError):
            LocalCostCalculator(policy="invalid_policy")

    def test_calculate_inference_cost_calculate_policy(self):
        """Test cost calculation with calculate policy"""
        calculator = LocalCostCalculator(
            policy="calculate",
            electricity_rate_usd_per_kwh=0.10,
            hardware_cost_usd=1000.0,
            hardware_lifespan_months=24,
            gpu_tdp_watts=300.0,
            cpu_tdp_watts=100.0,
        )

        cost = calculator.calculate_inference_cost(
            latency_ms=5000,  # 5 seconds
            tokens=1000,
            model="llama-7b",
            provider="ollama",
        )

        # Should return a positive cost
        assert cost > 0
        assert isinstance(cost, float)

    def test_calculate_inference_cost_null_fail_policy(self):
        """Test cost calculation with null_fail policy"""
        calculator = LocalCostCalculator(policy="null_fail")

        with pytest.raises(ValueError, match="Local LLM cost is null"):
            calculator.calculate_inference_cost(
                latency_ms=1000,
                tokens=500,
                model="llama-7b",
            )

    def test_calculate_inference_cost_zero_legacy_policy(self):
        """Test cost calculation with zero_legacy policy"""
        calculator = LocalCostCalculator(policy="zero_legacy")

        cost = calculator.calculate_inference_cost(
            latency_ms=1000,
            tokens=500,
            model="llama-7b",
        )

        assert cost == 0.0

    def test_get_default_electricity_rate_from_env(self):
        """Test getting electricity rate from environment variable"""
        with patch.dict(os.environ, {"ORKA_ELECTRICITY_RATE_USD_KWH": "0.25"}):
            calculator = LocalCostCalculator()
            assert calculator.electricity_rate == 0.25

    def test_get_default_electricity_rate_by_region(self):
        """Test getting electricity rate by region"""
        with patch.dict(os.environ, {"ORKA_REGION": "US"}):
            calculator = LocalCostCalculator()
            # Should use US rate or default
            assert calculator.electricity_rate > 0

    def test_estimate_hardware_cost_from_env(self):
        """Test hardware cost estimation from environment"""
        with patch.dict(os.environ, {"ORKA_HARDWARE_COST_USD": "5000"}):
            calculator = LocalCostCalculator()
            assert calculator.hardware_cost == 5000.0

    def test_estimate_gpu_utilization_large_model(self):
        """Test GPU utilization estimation for large models"""
        calculator = LocalCostCalculator()

        # Test with large model
        utilization = calculator._estimate_gpu_utilization("llama-70b", "ollama", 1000)
        assert 0.0 <= utilization <= 1.0

        # Large models should have higher utilization
        large_util = calculator._estimate_gpu_utilization("llama-70b", "ollama", 1000)
        small_util = calculator._estimate_gpu_utilization("llama-7b", "ollama", 1000)
        assert large_util >= small_util

    def test_estimate_cpu_utilization(self):
        """Test CPU utilization estimation"""
        calculator = LocalCostCalculator()

        utilization = calculator._estimate_cpu_utilization("llama-7b", "ollama")
        assert 0.0 <= utilization <= 1.0

    def test_cost_calculation_components(self):
        """Test that cost calculation includes both electricity and amortization"""
        calculator = LocalCostCalculator(
            policy="calculate",
            electricity_rate_usd_per_kwh=0.20,
            hardware_cost_usd=2000.0,
            hardware_lifespan_months=36,
            gpu_tdp_watts=300.0,
            cpu_tdp_watts=100.0,
        )

        # Test with reasonable inference time
        cost = calculator.calculate_inference_cost(
            latency_ms=10000,  # 10 seconds
            tokens=2000,
            model="llama-13b",
        )

        # Cost should be reasonable (not too high or too low)
        assert 0.0001 < cost < 0.01  # Between 0.01 cents and 1 cent

    def test_zero_latency_zero_cost(self):
        """Test that zero latency results in zero cost"""
        calculator = LocalCostCalculator(policy="calculate")

        cost = calculator.calculate_inference_cost(
            latency_ms=0,
            tokens=1000,
            model="llama-7b",
        )

        assert cost == 0.0


class TestModuleFunctions:
    """Test module-level functions"""

    def test_get_cost_calculator(self):
        """Test get_cost_calculator function"""
        calculator = get_cost_calculator()

        assert isinstance(calculator, LocalCostCalculator)
        assert calculator.policy == CostPolicy.CALCULATE

    def test_calculate_local_llm_cost_function(self):
        """Test calculate_local_llm_cost function"""
        cost = calculate_local_llm_cost(
            latency_ms=5000,
            tokens=1000,
            model="llama-7b",
            provider="ollama",
        )

        # Should return a reasonable cost
        assert cost is None or (isinstance(cost, float) and cost >= 0)

    def test_calculate_local_llm_cost_basic_functionality(self):
        """Test basic functionality of calculate_local_llm_cost"""
        cost = calculate_local_llm_cost(
            latency_ms=1000,
            tokens=500,
            model="llama-7b",
        )

        # Should return a reasonable cost or None
        assert cost is None or (isinstance(cost, float) and cost >= 0)
