"""Local LLM Cost Calculator.

Calculates real operating costs for local LLM inference including:
1. Electricity consumption during inference
2. Hardware amortization (GPU/CPU depreciation)
3. Optional cloud compute costs

No more fantasy $0.00 costs - local models have real expenses.
"""

import logging
import os
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CostPolicy(Enum):
    """Cost calculation policies for local LLMs."""

    CALCULATE = "calculate"  # Calculate real costs
    NULL_FAIL = "null_fail"  # Set to null and fail pipeline
    ZERO_LEGACY = "zero_legacy"  # Legacy $0.00 (deprecated)


class LocalCostCalculator:
    """
    Calculate real operating costs for local LLM inference.

    Cost components:
    1. Electricity: GPU/CPU power consumption during inference
    2. Hardware amortization: Depreciation of compute hardware
    3. Cloud costs: If running on rented cloud infrastructure
    """

    def __init__(
        self,
        policy: str = "calculate",
        electricity_rate_usd_per_kwh: Optional[float] = None,
        hardware_cost_usd: Optional[float] = None,
        hardware_lifespan_months: Optional[int] = None,
        gpu_tdp_watts: Optional[float] = None,
        cpu_tdp_watts: Optional[float] = None,
    ) -> None:
        """
        Initialize cost calculator.

        Args:
            policy: "calculate", "null_fail", or "zero_legacy"
            electricity_rate_usd_per_kwh: Local electricity rate (default: auto-detect)
            hardware_cost_usd: Total hardware cost for amortization
            hardware_lifespan_months: Hardware depreciation period
            gpu_tdp_watts: GPU power consumption (default: auto-detect)
            cpu_tdp_watts: CPU power consumption (default: auto-detect)
        """
        self.policy = CostPolicy(policy)

        # Electricity pricing (USD per kWh)
        self.electricity_rate: float = (
            electricity_rate_usd_per_kwh
            if electricity_rate_usd_per_kwh is not None
            else self._get_default_electricity_rate()
        )

        # Hardware costs
        self.hardware_cost: float = (
            hardware_cost_usd if hardware_cost_usd is not None else self._estimate_hardware_cost()
        )
        self.hardware_lifespan_months: int = (
            hardware_lifespan_months
            if hardware_lifespan_months is not None
            else 24  # Default 2 years
        )

        # Power consumption (watts)
        self.gpu_tdp: float = (
            gpu_tdp_watts if gpu_tdp_watts is not None else self._estimate_gpu_power()
        )
        self.cpu_tdp: float = (
            cpu_tdp_watts if cpu_tdp_watts is not None else self._estimate_cpu_power()
        )

        logger.info(
            f"LocalCostCalculator initialized: policy={policy}, "
            f"electricity=${self.electricity_rate:.4f}/kWh, "
            f"hardware=${self.hardware_cost:,.0f}, "
            f"gpu={self.gpu_tdp}W, cpu={self.cpu_tdp}W",
        )

    def _get_default_electricity_rate(self) -> float:
        """
        Get default electricity rate based on environment or region.

        Returns:
            Default electricity rate in USD per kWh
        """
        # Try environment variable first
        rate = os.environ.get("ORKA_ELECTRICITY_RATE_USD_KWH")
        if rate is not None:
            try:
                return float(rate)
            except ValueError:
                pass

        # Default rates by common regions (USD per kWh, 2025)
        default_rates: Dict[str, float] = {
            "US": 0.16,  # US average residential
            "EU": 0.28,  # EU average
            "DE": 0.32,  # Germany (high)
            "NO": 0.10,  # Norway (low, hydro)
            "CN": 0.08,  # China
            "JP": 0.26,  # Japan
            "KR": 0.20,  # South Korea
            "AU": 0.25,  # Australia
            "CA": 0.13,  # Canada
            "UK": 0.31,  # United Kingdom
        }

        # Try to detect region from environment or use conservative estimate
        region = os.environ.get("ORKA_REGION", "EU")
        return default_rates.get(region, 0.20)  # Conservative global average

    def _estimate_hardware_cost(self) -> float:
        """
        Estimate total hardware cost for amortization.

        Returns:
            Estimated hardware cost in USD
        """
        # Try environment variable
        cost = os.environ.get("ORKA_HARDWARE_COST_USD")
        if cost is not None:
            try:
                return float(cost)
            except ValueError:
                pass

        # Estimate based on detected GPU
        try:
            # Ignore GPUtil import error since it's optional
            import GPUtil  # type: ignore

            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_name = gpus[0].name.lower()

                # Hardware cost estimates (USD, 2025 prices)
                gpu_costs: Dict[str, float] = {
                    "rtx 4090": 1800.0,
                    "rtx 4080": 1200.0,
                    "rtx 4070": 800.0,
                    "rtx 3090": 1000.0,
                    "rtx 3080": 700.0,
                    "a100": 15000.0,
                    "h100": 30000.0,
                    "v100": 8000.0,
                    "a6000": 5000.0,
                    "a5000": 2500.0,
                    "titan": 2500.0,
                }

                for name_pattern, cost in gpu_costs.items():
                    if name_pattern in gpu_name:
                        # Add estimated system cost (CPU, RAM, storage, etc.)
                        system_cost = cost * 0.5  # System typically 50% of GPU cost
                        return cost + system_cost

        except ImportError:
            pass

        # Conservative default for unknown hardware
        return 2000.0  # ~$2K total system cost

    def _estimate_gpu_power(self) -> float:
        """
        Estimate GPU power consumption in watts.

        Returns:
            Estimated GPU power consumption in watts
        """
        # Try environment variable
        power = os.environ.get("ORKA_GPU_TDP_WATTS")
        if power is not None:
            try:
                return float(power)
            except ValueError:
                pass

        # Try to detect GPU and estimate TDP
        try:
            # Ignore GPUtil import error since it's optional
            import GPUtil  # type: ignore

            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_name = gpus[0].name.lower()

                # TDP estimates for common GPUs (watts)
                gpu_tdp: Dict[str, float] = {
                    "rtx 4090": 450.0,
                    "rtx 4080": 320.0,
                    "rtx 4070": 200.0,
                    "rtx 3090": 350.0,
                    "rtx 3080": 320.0,
                    "a100": 400.0,
                    "h100": 700.0,
                    "v100": 300.0,
                    "a6000": 300.0,
                    "a5000": 230.0,
                    "titan": 250.0,
                }

                for name_pattern, tdp in gpu_tdp.items():
                    if name_pattern in gpu_name:
                        return tdp

        except ImportError:
            pass

        # Conservative default for unknown GPU
        return 250.0  # Assume mid-range GPU

    def _estimate_cpu_power(self) -> float:
        """
        Estimate CPU power consumption in watts.

        Returns:
            Estimated CPU power consumption in watts
        """
        # Try environment variable
        power = os.environ.get("ORKA_CPU_TDP_WATTS")
        if power is not None:
            try:
                return float(power)
            except ValueError:
                pass

        # Conservative default for unknown CPU
        return 65.0  # Assume mid-range CPU

    def _estimate_gpu_utilization(self, model: str, provider: str, tokens: int) -> float:
        """
        Estimate GPU utilization based on model and workload.

        Args:
            model: Model name
            provider: Local provider
            tokens: Number of tokens processed

        Returns:
            Estimated GPU utilization (0.0-1.0)
        """
        # Base utilization by model size
        model_lower = model.lower()
        if "70b" in model_lower or "65b" in model_lower:
            base_util = 0.95  # Very large models
        elif "30b" in model_lower or "33b" in model_lower:
            base_util = 0.85  # Large models
        elif "13b" in model_lower:
            base_util = 0.75  # Medium models
        elif "7b" in model_lower:
            base_util = 0.65  # Small models
        else:
            base_util = 0.70  # Unknown size

        # Adjust for token count
        if tokens > 2000:
            base_util *= 1.2  # Long sequences need more resources
        elif tokens < 100:
            base_util *= 0.8  # Short sequences need fewer resources

        # Clamp to valid range
        return max(0.0, min(1.0, base_util))

    def _estimate_cpu_utilization(self, model: str, provider: str) -> float:
        """
        Estimate CPU utilization based on model and provider.

        Args:
            model: Model name
            provider: Local provider

        Returns:
            Estimated CPU utilization (0.0-1.0)
        """
        # Base utilization by provider
        if provider == "ollama":
            base_util = 0.3  # Ollama is GPU-focused
        elif provider == "lm_studio":
            base_util = 0.4  # LM Studio uses more CPU
        else:
            base_util = 0.35  # Unknown provider

        # Adjust for model size
        model_lower = model.lower()
        if "70b" in model_lower or "65b" in model_lower:
            base_util *= 1.2  # Very large models need more CPU
        elif "7b" in model_lower:
            base_util *= 0.8  # Small models need less CPU

        # Clamp to valid range
        return max(0.0, min(1.0, base_util))

    def calculate_inference_cost(
        self,
        latency_ms: float,
        tokens: int,
        model: str,
        provider: str = "ollama",
    ) -> Optional[float]:
        """
        Calculate the real cost of local LLM inference.

        Args:
            latency_ms: Inference time in milliseconds
            tokens: Total tokens processed
            model: Model name for optimization estimation
            provider: Local provider (ollama, lm_studio, etc.)

        Returns:
            Cost in USD, or None if null_fail policy

        Raises:
            ValueError: If null_fail policy is enabled
        """
        if self.policy == CostPolicy.NULL_FAIL:
            raise ValueError(
                f"Local LLM cost is null (policy=null_fail). "
                f"Configure real cost calculation or use cloud models. "
                f"Model: {model}, Tokens: {tokens}, Latency: {latency_ms}ms",
            )

        if self.policy == CostPolicy.ZERO_LEGACY:
            logger.warning("Using deprecated zero cost policy for local LLMs")
            return 0.0

        # Calculate electricity cost
        inference_time_hours = latency_ms / (1000.0 * 3600.0)  # Convert ms to hours

        # Estimate GPU utilization based on model size and provider
        gpu_utilization = self._estimate_gpu_utilization(model, provider, tokens)
        cpu_utilization = self._estimate_cpu_utilization(model, provider)

        # Power consumption during inference
        gpu_power_kwh = (self.gpu_tdp * gpu_utilization * inference_time_hours) / 1000.0
        cpu_power_kwh = (self.cpu_tdp * cpu_utilization * inference_time_hours) / 1000.0

        electricity_cost = (gpu_power_kwh + cpu_power_kwh) * self.electricity_rate

        # Hardware amortization cost
        # Spread hardware cost over expected lifespan and usage
        hours_per_month = 24.0 * 30.0  # Assume 24/7 usage for conservative estimate
        total_hardware_hours = float(self.hardware_lifespan_months) * hours_per_month
        hardware_cost_per_hour = self.hardware_cost / total_hardware_hours
        amortization_cost = hardware_cost_per_hour * inference_time_hours

        total_cost = electricity_cost + amortization_cost

        logger.debug(
            f"Local cost breakdown: electricity=${electricity_cost:.6f}, "
            f"amortization=${amortization_cost:.6f}, total=${total_cost:.6f} "
            f"(model={model}, {tokens}tok, {latency_ms}ms)",
        )

        return round(total_cost, 6)


def get_cost_calculator() -> LocalCostCalculator:
    """
    Get a cost calculator instance with default configuration.

    Returns:
        LocalCostCalculator instance
    """
    policy = os.environ.get("ORKA_LOCAL_COST_POLICY", "calculate")
    return LocalCostCalculator(policy=policy)


def calculate_local_llm_cost(
    latency_ms: float,
    tokens: int,
    model: str,
    provider: str = "ollama",
) -> Optional[float]:
    """
    Calculate cost for local LLM inference (convenience function).

    Args:
        latency_ms: Inference time in milliseconds
        tokens: Total tokens processed
        model: Model name for optimization estimation
        provider: Local provider (ollama, lm_studio, etc.)

    Returns:
        Cost in USD, or None if null_fail policy
    """
    calculator = get_cost_calculator()
    return calculator.calculate_inference_cost(
        latency_ms=latency_ms,
        tokens=tokens,
        model=model,
        provider=provider,
    )
