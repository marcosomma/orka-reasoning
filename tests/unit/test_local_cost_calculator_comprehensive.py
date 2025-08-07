"""Test suite for local cost calculator."""

import os
from unittest.mock import Mock, patch

import pytest

from orka.agents.local_cost_calculator import (
    CostPolicy,
    LocalCostCalculator,
    calculate_local_llm_cost,
    get_cost_calculator,
)


class TestLocalCostCalculatorInitialization:
    """Test initialization of LocalCostCalculator."""

    def test_default_initialization(self):
        """Test initialization with default parameters."""
        with patch("GPUtil.getGPUs") as mock_gpus, patch("psutil.cpu_count") as mock_cpu_count:
            mock_gpus.return_value = []
            mock_cpu_count.return_value = 8

            calculator = LocalCostCalculator()

            assert calculator.policy == CostPolicy.CALCULATE
            assert calculator.electricity_rate > 0
            assert calculator.hardware_cost > 0
            assert calculator.hardware_lifespan_months == 36
            assert calculator.gpu_tdp > 0
            assert calculator.cpu_tdp > 0

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        calculator = LocalCostCalculator(
            policy="calculate",
            electricity_rate_usd_per_kwh=0.15,
            hardware_cost_usd=2000,
            hardware_lifespan_months=24,
            gpu_tdp_watts=300,
            cpu_tdp_watts=100,
        )

        assert calculator.policy == CostPolicy.CALCULATE
        assert calculator.electricity_rate == 0.15
        assert calculator.hardware_cost == 2000
        assert calculator.hardware_lifespan_months == 24
        assert calculator.gpu_tdp == 300
        assert calculator.cpu_tdp == 100

    def test_initialization_with_environment_variables(self):
        """Test initialization with environment variables."""
        with patch.dict(
            os.environ,
            {
                "ORKA_ELECTRICITY_RATE_USD_KWH": "0.25",
                "ORKA_HARDWARE_COST_USD": "3000",
                "ORKA_GPU_TDP_WATTS": "400",
                "ORKA_CPU_TDP_WATTS": "150",
                "ORKA_REGION": "US",
            },
        ):
            calculator = LocalCostCalculator()

            assert calculator.electricity_rate == 0.25
            assert calculator.hardware_cost == 3000
            assert calculator.gpu_tdp == 400
            assert calculator.cpu_tdp == 150

    def test_initialization_with_gpu_detection(self):
        """Test initialization with GPU detection."""
        mock_gpu = Mock()
        mock_gpu.name = "NVIDIA RTX 4090"
        with patch("GPUtil.getGPUs", return_value=[mock_gpu]):
            calculator = LocalCostCalculator()

            assert calculator.gpu_tdp == 450  # RTX 4090 TDP
            assert calculator.hardware_cost > 1800  # RTX 4090 cost + system


class TestLocalCostCalculatorCostCalculation:
    """Test cost calculation functionality."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator with fixed parameters for testing."""
        return LocalCostCalculator(
            electricity_rate_usd_per_kwh=0.20,
            hardware_cost_usd=2000,
            hardware_lifespan_months=36,
            gpu_tdp_watts=300,
            cpu_tdp_watts=100,
        )

    def test_calculate_inference_cost_basic(self, calculator):
        """Test basic cost calculation."""
        cost = calculator.calculate_inference_cost(
            latency_ms=1000,  # 1 second
            tokens=100,
            model="llama2-7b",
            provider="ollama",
        )

        assert cost > 0
        assert cost < 0.01  # Should be a small amount for 1 second

    def test_calculate_inference_cost_null_fail(self):
        """Test null_fail policy."""
        calculator = LocalCostCalculator(policy="null_fail")

        with pytest.raises(ValueError):
            calculator.calculate_inference_cost(1000, 100, "llama2-7b")

    def test_calculate_inference_cost_zero_legacy(self):
        """Test zero_legacy policy."""
        calculator = LocalCostCalculator(policy="zero_legacy")

        cost = calculator.calculate_inference_cost(1000, 100, "llama2-7b")
        assert cost == 0.0

    def test_calculate_inference_cost_large_model(self, calculator):
        """Test cost calculation for large models."""
        cost_large = calculator.calculate_inference_cost(
            latency_ms=1000,
            tokens=100,
            model="llama2-70b",
            provider="ollama",
        )

        cost_small = calculator.calculate_inference_cost(
            latency_ms=1000,
            tokens=100,
            model="llama2-7b",
            provider="ollama",
        )

        assert cost_large > cost_small  # Large models should cost more

    def test_calculate_inference_cost_long_inference(self, calculator):
        """Test cost calculation for long inference times."""
        cost_long = calculator.calculate_inference_cost(
            latency_ms=10000,  # 10 seconds
            tokens=1000,
            model="llama2-7b",
            provider="ollama",
        )

        cost_short = calculator.calculate_inference_cost(
            latency_ms=1000,  # 1 second
            tokens=100,
            model="llama2-7b",
            provider="ollama",
        )

        assert cost_long > cost_short * 5  # Should scale roughly with time


class TestLocalCostCalculatorUtilities:
    """Test utility functions."""

    def test_get_default_electricity_rate(self):
        """Test default electricity rate detection."""
        calculator = LocalCostCalculator()

        with patch.dict(os.environ, {"ORKA_REGION": "DE"}):
            rate_de = calculator._get_default_electricity_rate()
            assert rate_de == 0.32  # Germany rate

        with patch.dict(os.environ, {"ORKA_REGION": "US"}):
            rate_us = calculator._get_default_electricity_rate()
            assert rate_us == 0.16  # US rate

    def test_estimate_hardware_cost(self):
        """Test hardware cost estimation."""
        calculator = LocalCostCalculator()

        mock_gpu = Mock()
        mock_gpu.name = "NVIDIA RTX 3090"
        with patch("GPUtil.getGPUs", return_value=[mock_gpu]):
            cost = calculator._estimate_hardware_cost()
            assert cost == 1500  # RTX 3090 + system cost

    def test_estimate_gpu_power(self):
        """Test GPU power estimation."""
        calculator = LocalCostCalculator()

        mock_gpu = Mock()
        mock_gpu.name = "NVIDIA A100"
        with patch("GPUtil.getGPUs", return_value=[mock_gpu]):
            power = calculator._estimate_gpu_power()
            assert power == 400  # A100 TDP

    def test_estimate_cpu_power(self):
        """Test CPU power estimation."""
        calculator = LocalCostCalculator()

        with patch("psutil.cpu_count", return_value=16):
            power = calculator._estimate_cpu_power()
            assert power == 240  # 16 cores * 15W

    def test_estimate_gpu_utilization(self):
        """Test GPU utilization estimation."""
        calculator = LocalCostCalculator()

        util_70b = calculator._estimate_gpu_utilization("llama2-70b", "ollama", 2000)
        util_7b = calculator._estimate_gpu_utilization("llama2-7b", "ollama", 100)

        assert util_70b > util_7b  # Larger models should have higher utilization
        assert 0 <= util_70b <= 1
        assert 0 <= util_7b <= 1

    def test_estimate_cpu_utilization(self):
        """Test CPU utilization estimation."""
        calculator = LocalCostCalculator()

        util_ollama = calculator._estimate_cpu_utilization("llama2-7b", "ollama")
        util_lmstudio = calculator._estimate_cpu_utilization("llama2-7b", "lm_studio")

        assert util_ollama > util_lmstudio  # Ollama uses more CPU
        assert 0 <= util_ollama <= 1
        assert 0 <= util_lmstudio <= 1


class TestGlobalCalculator:
    """Test global calculator functions."""

    def test_get_cost_calculator(self):
        """Test global calculator singleton."""
        calc1 = get_cost_calculator()
        calc2 = get_cost_calculator()

        assert calc1 is calc2  # Should return same instance

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        import sys

        from orka.agents import local_cost_calculator

        # Save original state
        original_calculator = local_cost_calculator._default_calculator

        # Reset state
        local_cost_calculator._default_calculator = None

        yield

        # Restore original state
        local_cost_calculator._default_calculator = original_calculator

    def test_calculate_local_llm_cost(self):
        """Test convenience function."""
        from orka.agents import local_cost_calculator

        # Common environment variables for consistent behavior
        base_env = {
            "ORKA_ELECTRICITY_RATE_USD_KWH": "0.15",
            "ORKA_HARDWARE_COST_USD": "2000",
            "ORKA_GPU_TDP_WATTS": "300",
            "ORKA_CPU_TDP_WATTS": "100",
            "ORKA_REGION": "US",
        }

        # Test calculate policy
        with (
            patch.dict(os.environ, {**base_env, "ORKA_LOCAL_COST_POLICY": "calculate"}),
            patch("GPUtil.getGPUs", return_value=[]),
            patch("psutil.cpu_count", return_value=8),
        ):
            # Reset global calculator
            local_cost_calculator._default_calculator = None
            cost = calculate_local_llm_cost(1000, 100, "llama2-7b", "ollama")
            assert cost > 0

        # Test zero_legacy policy
        with (
            patch.dict(os.environ, {**base_env, "ORKA_LOCAL_COST_POLICY": "zero_legacy"}),
            patch("GPUtil.getGPUs", return_value=[]),
            patch("psutil.cpu_count", return_value=8),
        ):
            # Reset global calculator
            local_cost_calculator._default_calculator = None
            cost = calculate_local_llm_cost(1000, 100, "llama2-7b", "ollama")
            assert cost == 0.0

        # Test null_fail policy
        with (
            patch.dict(os.environ, {**base_env, "ORKA_LOCAL_COST_POLICY": "null_fail"}),
            patch("GPUtil.getGPUs", return_value=[]),
            patch("psutil.cpu_count", return_value=8),
        ):
            # Reset global calculator
            local_cost_calculator._default_calculator = None
            with pytest.raises(ValueError):
                calculate_local_llm_cost(1000, 100, "llama2-7b", "ollama")
