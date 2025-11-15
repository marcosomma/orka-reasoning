import pytest
from unittest.mock import MagicMock, patch, mock_open
from orka.agents.local_cost_calculator import LocalCostCalculator, CostPolicy

@patch("orka.agents.local_cost_calculator.logger", MagicMock())
def test_initialization():
    calculator = LocalCostCalculator()
    assert calculator.policy == CostPolicy.CALCULATE

@patch("orka.agents.local_cost_calculator.logger", MagicMock())
def test_load_model_costs_not_implemented():
    # This test is based on a misunderstanding of the class.
    # The class does not load model costs from a file.
    # This test is kept to show the evolution of the understanding of the code.
    pass

@patch("orka.agents.local_cost_calculator.logger", MagicMock())
def test_calculate_cost():
    calculator = LocalCostCalculator()
    
    # Mocking internal methods for deterministic testing
    calculator._get_default_electricity_rate = MagicMock(return_value=0.15)
    calculator._estimate_hardware_cost = MagicMock(return_value=2000)
    calculator._estimate_gpu_power = MagicMock(return_value=300)
    calculator._estimate_cpu_power = MagicMock(return_value=120)
    
    cost = calculator.calculate_inference_cost(1000, 100, "7b-model")
    assert isinstance(cost, float)
    assert cost > 0

    calculator.policy = CostPolicy.ZERO_LEGACY
    cost_zero = calculator.calculate_inference_cost(1000, 100, "7b-model")
    assert cost_zero == 0

    calculator.policy = CostPolicy.NULL_FAIL
    with pytest.raises(ValueError):
        calculator.calculate_inference_cost(1000, 100, "7b-model")
