"""
Unit tests for local cost calculator module.
Tests cost calculation, hardware estimation, and policy handling.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from orka.agents.local_cost_calculator import (
    CostPolicy,
    LocalCostCalculator,
    calculate_local_llm_cost,
    get_cost_calculator,
)


class TestCostPolicy:
    """Test cost policy enumeration."""

    def test_cost_policy_values(self):
        """Test cost policy enum values."""
        assert CostPolicy.CALCULATE.value == "calculate"
        assert CostPolicy.NULL_FAIL.value == "null_fail"
        assert CostPolicy.ZERO_LEGACY.value == "zero_legacy"

    def test_cost_policy_creation(self):
        """Test creating cost policy from string."""
        assert CostPolicy("calculate") == CostPolicy.CALCULATE
        assert CostPolicy("null_fail") == CostPolicy.NULL_FAIL
        assert CostPolicy("zero_legacy") == CostPolicy.ZERO_LEGACY

    def test_invalid_cost_policy(self):
        """Test invalid cost policy raises error."""
        with pytest.raises(ValueError):
            CostPolicy("invalid_policy")


class TestLocalCostCalculator:
    """Test local cost calculator functionality."""

    def test_initialization_default_values(self):
        """Test calculator initialization with default values."""
        with patch.object(
            LocalCostCalculator,
            "_get_default_electricity_rate",
            return_value=0.20,
        ), patch.object(
            LocalCostCalculator,
            "_estimate_hardware_cost",
            return_value=1000.0,
        ), patch.object(
            LocalCostCalculator,
            "_estimate_gpu_power",
            return_value=300.0,
        ), patch.object(LocalCostCalculator, "_estimate_cpu_power", return_value=100.0):
            calculator = LocalCostCalculator()

            assert calculator.policy == CostPolicy.CALCULATE
            assert calculator.electricity_rate == 0.20
            assert calculator.hardware_cost == 1000.0
            assert calculator.hardware_lifespan_months == 36
            assert calculator.gpu_tdp == 300.0
            assert calculator.cpu_tdp == 100.0

    def test_initialization_custom_values(self):
        """Test calculator initialization with custom values."""
        calculator = LocalCostCalculator(
            policy="null_fail",
            electricity_rate_usd_per_kwh=0.15,
            hardware_cost_usd=2000.0,
            hardware_lifespan_months=24,
            gpu_tdp_watts=400.0,
            cpu_tdp_watts=150.0,
        )

        assert calculator.policy == CostPolicy.NULL_FAIL
        assert calculator.electricity_rate == 0.15
        assert calculator.hardware_cost == 2000.0
        assert calculator.hardware_lifespan_months == 24
        assert calculator.gpu_tdp == 400.0
        assert calculator.cpu_tdp == 150.0

    def test_get_default_electricity_rate_from_env(self):
        """Test getting electricity rate from environment variable."""
        with patch.dict(os.environ, {"ORKA_ELECTRICITY_RATE_USD_KWH": "0.25"}):
            calculator = LocalCostCalculator()
            assert calculator._get_default_electricity_rate() == 0.25

    def test_get_default_electricity_rate_invalid_env(self):
        """Test invalid environment variable falls back to default."""
        with patch.dict(os.environ, {"ORKA_ELECTRICITY_RATE_USD_KWH": "invalid"}):
            calculator = LocalCostCalculator()
            rate = calculator._get_default_electricity_rate()
            assert isinstance(rate, float)
            assert rate > 0

    def test_get_default_electricity_rate_by_region(self):
        """Test electricity rate detection by region."""
        calculator = LocalCostCalculator()

        with patch.dict(os.environ, {"ORKA_REGION": "US"}):
            assert calculator._get_default_electricity_rate() == 0.16

        with patch.dict(os.environ, {"ORKA_REGION": "DE"}):
            assert calculator._get_default_electricity_rate() == 0.32

        with patch.dict(os.environ, {"ORKA_REGION": "UNKNOWN"}):
            assert calculator._get_default_electricity_rate() == 0.20

    def test_estimate_hardware_cost_from_env(self):
        """Test getting hardware cost from environment variable."""
        with patch.dict(os.environ, {"ORKA_HARDWARE_COST_USD": "5000"}):
            calculator = LocalCostCalculator()
            assert calculator._estimate_hardware_cost() == 5000.0

    def test_estimate_hardware_cost_invalid_env(self):
        """Test invalid environment variable falls back to estimation."""
        with patch.dict(os.environ, {"ORKA_HARDWARE_COST_USD": "invalid"}):
            with patch("builtins.__import__", side_effect=ImportError("GPUtil not available")):
                calculator = LocalCostCalculator()
                cost = calculator._estimate_hardware_cost()
                assert isinstance(cost, (int, float))
                assert cost > 0

    def test_estimate_hardware_cost_with_gpu(self):
        """Test hardware cost estimation with detected GPU."""
        # Mock GPU detection
        mock_gpu = MagicMock()
        mock_gpu.name = "RTX 4090"

        mock_gputil = MagicMock()
        mock_gputil.getGPUs.return_value = [mock_gpu]

        with patch("builtins.__import__", return_value=mock_gputil):
            calculator = LocalCostCalculator()
            cost = calculator._estimate_hardware_cost()

            # Should recognize RTX 4090 and estimate accordingly
            assert cost >= 1000  # Should be reasonable estimate

    def test_estimate_hardware_cost_no_gpu_import(self):
        """Test hardware cost estimation when GPUtil import fails."""
        with patch("builtins.__import__", side_effect=ImportError("GPUtil not available")):
            calculator = LocalCostCalculator()
            cost = calculator._estimate_hardware_cost()

            # Should fall back to default estimation
            assert isinstance(cost, (int, float))
            assert cost > 0

    def test_estimate_gpu_power_from_env(self):
        """Test GPU power estimation from environment."""
        with patch.dict(os.environ, {"ORKA_GPU_TDP_WATTS": "350"}):
            calculator = LocalCostCalculator()
            assert calculator._estimate_gpu_power() == 350.0

    def test_estimate_gpu_power_with_detection(self):
        """Test GPU power estimation with GPU detection."""
        mock_gpu = MagicMock()
        mock_gpu.name = "RTX 3080"

        mock_gputil = MagicMock()
        mock_gputil.getGPUs.return_value = [mock_gpu]

        with patch("builtins.__import__", return_value=mock_gputil):
            calculator = LocalCostCalculator()
            power = calculator._estimate_gpu_power()

            assert isinstance(power, (int, float))
            assert power > 0

    def test_estimate_cpu_power(self):
        """Test CPU power estimation."""
        calculator = LocalCostCalculator()

        with patch.dict(os.environ, {"ORKA_CPU_TDP_WATTS": "125"}):
            assert calculator._estimate_cpu_power() == 125.0

        # Test default estimation
        with patch.dict(os.environ, {}, clear=True):
            power = calculator._estimate_cpu_power()
            assert isinstance(power, (int, float))
            assert power > 0

    def test_calculate_inference_cost_null_fail_policy(self):
        """Test null fail policy raises exception."""
        calculator = LocalCostCalculator(policy="null_fail")

        with pytest.raises(ValueError, match="Local LLM cost is null"):
            calculator.calculate_inference_cost(
                latency_ms=1000,
                tokens=100,
                model="llama2-7b",
                provider="ollama",
            )

    def test_calculate_inference_cost_zero_legacy_policy(self):
        """Test zero legacy policy returns zero."""
        calculator = LocalCostCalculator(policy="zero_legacy")

        cost = calculator.calculate_inference_cost(
            latency_ms=1000,
            tokens=100,
            model="llama2-7b",
            provider="ollama",
        )

        assert cost == 0.0

    def test_calculate_inference_cost_calculate_policy(self):
        """Test calculate policy computes real costs."""
        calculator = LocalCostCalculator(
            policy="calculate",
            electricity_rate_usd_per_kwh=0.20,
            hardware_cost_usd=1000.0,
            gpu_tdp_watts=300.0,
            cpu_tdp_watts=100.0,
        )

        with patch.object(calculator, "_estimate_gpu_utilization", return_value=0.8), patch.object(
            calculator,
            "_estimate_cpu_utilization",
            return_value=0.3,
        ):
            cost = calculator.calculate_inference_cost(
                latency_ms=2000,  # 2 seconds
                tokens=100,
                model="llama2-7b",
                provider="ollama",
            )

            assert isinstance(cost, float)
            assert cost > 0
            assert cost < 1.0  # Should be reasonable for 2 second inference

    def test_estimate_gpu_utilization(self):
        """Test GPU utilization estimation."""
        calculator = LocalCostCalculator()

        # Test different model sizes
        utilization_7b = calculator._estimate_gpu_utilization("llama2-7b", "ollama", 100)
        utilization_13b = calculator._estimate_gpu_utilization("llama2-13b", "ollama", 100)
        utilization_70b = calculator._estimate_gpu_utilization("llama2-70b", "ollama", 100)

        assert isinstance(utilization_7b, float)
        assert isinstance(utilization_13b, float)
        assert isinstance(utilization_70b, float)

        assert 0.0 <= utilization_7b <= 1.0
        assert 0.0 <= utilization_13b <= 1.0
        assert 0.0 <= utilization_70b <= 1.0

        # Larger models should generally use more GPU
        assert utilization_70b >= utilization_7b

    def test_estimate_cpu_utilization(self):
        """Test CPU utilization estimation."""
        calculator = LocalCostCalculator()

        utilization_ollama = calculator._estimate_cpu_utilization("llama2-7b", "ollama")
        utilization_lm_studio = calculator._estimate_cpu_utilization("llama2-7b", "lm_studio")

        assert isinstance(utilization_ollama, float)
        assert isinstance(utilization_lm_studio, float)

        assert 0.0 <= utilization_ollama <= 1.0
        assert 0.0 <= utilization_lm_studio <= 1.0

    def test_cost_calculation_components(self):
        """Test that cost calculation includes both electricity and amortization."""
        calculator = LocalCostCalculator(
            electricity_rate_usd_per_kwh=0.20,
            hardware_cost_usd=1000.0,
            hardware_lifespan_months=36,
            gpu_tdp_watts=300.0,
            cpu_tdp_watts=100.0,
        )

        with patch.object(calculator, "_estimate_gpu_utilization", return_value=0.8), patch.object(
            calculator,
            "_estimate_cpu_utilization",
            return_value=0.3,
        ):
            # Calculate for a measurable inference time
            cost = calculator.calculate_inference_cost(
                latency_ms=5000,  # 5 seconds
                tokens=200,
                model="llama2-13b",
                provider="ollama",
            )

            assert cost > 0
            # Cost should be reasonable (not too high or too low)
            assert cost < 0.01  # Less than 1 cent for 5 second inference

    def test_cost_precision(self):
        """Test cost calculation precision."""
        calculator = LocalCostCalculator(
            electricity_rate_usd_per_kwh=0.20,
            hardware_cost_usd=1000.0,
        )

        with patch.object(calculator, "_estimate_gpu_utilization", return_value=0.5), patch.object(
            calculator,
            "_estimate_cpu_utilization",
            return_value=0.2,
        ):
            cost = calculator.calculate_inference_cost(1000, 50, "test-model")

            # Should be rounded to 6 decimal places
            assert isinstance(cost, float)
            str_cost = str(cost)
            if "." in str_cost:
                decimal_places = len(str_cost.split(".")[1])
                assert decimal_places <= 6


class TestModuleFunctions:
    """Test module-level functions."""

    @patch("orka.agents.local_cost_calculator.LocalCostCalculator")
    def test_get_cost_calculator(self, mock_calculator_class):
        """Test get_cost_calculator function."""
        mock_instance = MagicMock()
        mock_calculator_class.return_value = mock_instance

        calculator = get_cost_calculator()

        assert calculator == mock_instance
        mock_calculator_class.assert_called_once()

    @patch("orka.agents.local_cost_calculator.get_cost_calculator")
    def test_calculate_local_llm_cost(self, mock_get_calculator):
        """Test calculate_local_llm_cost function."""
        mock_calculator = MagicMock()
        mock_calculator.calculate_inference_cost.return_value = 0.001234
        mock_get_calculator.return_value = mock_calculator

        cost = calculate_local_llm_cost(
            latency_ms=1500,
            tokens=75,
            model="test-model",
            provider="ollama",
        )

        assert cost == 0.001234
        mock_get_calculator.assert_called_once()
        mock_calculator.calculate_inference_cost.assert_called_once_with(
            1500,
            75,
            "test-model",
            "ollama",
        )

    def test_integration_real_calculation(self):
        """Test integration with real cost calculation."""
        # Test with known values to verify calculation logic
        calculator = LocalCostCalculator(
            policy="calculate",
            electricity_rate_usd_per_kwh=0.10,  # Cheap electricity
            hardware_cost_usd=1000.0,
            hardware_lifespan_months=36,
            gpu_tdp_watts=200.0,
            cpu_tdp_watts=50.0,
        )

        # Mock utilization to known values
        with patch.object(calculator, "_estimate_gpu_utilization", return_value=1.0), patch.object(
            calculator,
            "_estimate_cpu_utilization",
            return_value=0.5,
        ):
            # 1 second inference
            cost = calculator.calculate_inference_cost(1000, 100, "test-model")

            # Verify cost is reasonable and positive
            assert cost > 0
            assert cost < 0.001  # Should be fractions of a cent for 1 second
