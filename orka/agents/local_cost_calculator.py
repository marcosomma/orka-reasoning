"""
Local LLM Cost Calculator
========================

Calculates real operating costs for local LLM inference including:
1. Electricity consumption during inference
2. Hardware amortization (GPU/CPU depreciation)
3. Optional cloud compute costs

No more fantasy $0.00 costs - local models have real expenses.
"""

import logging
import os
import shutil
import subprocess
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class CostPolicy(Enum):
    """Cost calculation policies for local LLMs"""

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
        electricity_rate_usd_per_kwh: float | None = None,
        hardware_cost_usd: float | None = None,
        hardware_lifespan_months: int = 36,
        gpu_tdp_watts: float | None = None,
        cpu_tdp_watts: float | None = None,
    ):
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
        self.electricity_rate = electricity_rate_usd_per_kwh or self._get_default_electricity_rate()

        # Hardware costs
        self.hardware_cost = hardware_cost_usd or self._estimate_hardware_cost()
        self.hardware_lifespan_months = hardware_lifespan_months

        # Power consumption (watts)
        self.gpu_tdp = gpu_tdp_watts or self._estimate_gpu_power()
        self.cpu_tdp = cpu_tdp_watts or self._estimate_cpu_power()

        logger.info(
            f"LocalCostCalculator initialized: policy={policy}, "
            f"electricity=${self.electricity_rate:.4f}/kWh, "
            f"hardware=${self.hardware_cost:,.0f}, "
            f"gpu={self.gpu_tdp}W, cpu={self.cpu_tdp}W",
        )

    _gpu_name_checked: bool = False
    _cached_gpu_name: str | None = None

    def _detect_gpu_name(self) -> str | None:
        """Best-effort GPU name detection without importing GPUtil.

        Notes:
        - Uses `nvidia-smi` if available.
        - Skips probing during pytest runs for speed and determinism.
        """
        if LocalCostCalculator._gpu_name_checked:
            return LocalCostCalculator._cached_gpu_name

        LocalCostCalculator._gpu_name_checked = True

        if os.environ.get("PYTEST_RUNNING", "").lower() == "true":
            LocalCostCalculator._cached_gpu_name = None
            return None

        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            LocalCostCalculator._cached_gpu_name = None
            return None

        try:
            result = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )

            if result.returncode != 0:
                LocalCostCalculator._cached_gpu_name = None
                return None

            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            LocalCostCalculator._cached_gpu_name = lines[0] if lines else None
            return LocalCostCalculator._cached_gpu_name
        except Exception:
            LocalCostCalculator._cached_gpu_name = None
            return None

    def calculate_inference_cost(
        self,
        latency_ms: float,
        tokens: int,
        model: str,
        provider: str = "unknown",
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
            logger.info("Using zero cost policy for local LLMs (set via ORKA_LOCAL_COST_POLICY)")
            return 0.0

        # Calculate electricity cost
        inference_time_hours = latency_ms / (1000 * 3600)  # Convert ms to hours

        # Estimate GPU utilization based on model size and provider
        gpu_utilization = self._estimate_gpu_utilization(model, provider, tokens)
        cpu_utilization = self._estimate_cpu_utilization(model, provider)

        # Power consumption during inference
        gpu_power_kwh = (self.gpu_tdp * gpu_utilization * inference_time_hours) / 1000
        cpu_power_kwh = (self.cpu_tdp * cpu_utilization * inference_time_hours) / 1000

        electricity_cost = (gpu_power_kwh + cpu_power_kwh) * self.electricity_rate

        # Hardware amortization cost
        # Spread hardware cost over expected lifespan and usage
        hours_per_month = 24 * 30  # Assume 24/7 usage for conservative estimate
        total_hardware_hours = self.hardware_lifespan_months * hours_per_month
        hardware_cost_per_hour = self.hardware_cost / total_hardware_hours
        amortization_cost = hardware_cost_per_hour * inference_time_hours

        total_cost = electricity_cost + amortization_cost

        logger.debug(
            f"Local cost breakdown: electricity=${electricity_cost:.6f}, "
            f"amortization=${amortization_cost:.6f}, total=${total_cost:.6f} "
            f"(model={model}, {tokens}tok, {latency_ms}ms)",
        )

        return round(total_cost, 6)

    def _get_default_electricity_rate(self) -> float:
        """Get default electricity rate based on environment or region."""
        # Try environment variable first
        rate = os.environ.get("ORKA_ELECTRICITY_RATE_USD_KWH")
        if rate:
            try:
                return float(rate)
            except ValueError:
                pass

        # Default rates by common regions (USD per kWh, 2025)
        default_rates = {
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
        """Estimate total hardware cost for amortization."""
        # Try environment variable
        cost = os.environ.get("ORKA_HARDWARE_COST_USD")
        if cost:
            try:
                return float(cost)
            except ValueError:
                pass

        gpu_name = (self._detect_gpu_name() or "").lower()
        if gpu_name:
            # Hardware cost estimates (USD, 2025 prices)
            gpu_costs = {
                "rtx 4090": 1800,
                "rtx 4080": 1200,
                "rtx 4070": 800,
                "rtx 3090": 1000,
                "rtx 3080": 700,
                "a100": 15000,
                "h100": 30000,
                "v100": 8000,
                "a6000": 5000,
                "a5000": 2500,
                "titan": 2500,
            }

            for name_pattern, gpu_cost in gpu_costs.items():
                if name_pattern in gpu_name:
                    # Add estimated system cost (CPU, RAM, storage, etc.)
                    system_cost = gpu_cost * 0.5  # System typically 50% of GPU cost
                    return gpu_cost + system_cost

        # Conservative default for unknown hardware
        return 2000  # ~$2K total system cost

    def _estimate_gpu_power(self) -> float:
        """Estimate GPU power consumption in watts."""
        # Try environment variable
        power = os.environ.get("ORKA_GPU_TDP_WATTS")
        if power:
            try:
                return float(power)
            except ValueError:
                pass

        gpu_name = (self._detect_gpu_name() or "").lower()
        if gpu_name:
            # TDP estimates for common GPUs (watts)
            gpu_tdp = {
                "rtx 4090": 450,
                "rtx 4080": 320,
                "rtx 4070": 200,
                "rtx 3090": 350,
                "rtx 3080": 320,
                "a100": 400,
                "h100": 700,
                "v100": 300,
                "a6000": 300,
                "a5000": 230,
                "titan": 250,
            }

            for name_pattern, tdp in gpu_tdp.items():
                if name_pattern in gpu_name:
                    return tdp

        # Conservative default
        return 250  # Typical high-end GPU

    def _estimate_cpu_power(self) -> float:
        """Estimate CPU power consumption in watts."""
        # Try environment variable
        power = os.environ.get("ORKA_CPU_TDP_WATTS")
        if power:
            try:
                return float(power)
            except ValueError:
                pass

        # Estimate based on CPU cores

        if HAS_PSUTIL:
            cpu_count = psutil.cpu_count(logical=False)  # Physical cores
            if cpu_count is not None:
                # Estimate ~15W per physical core for modern CPUs under load
                return cpu_count * 15

        # Conservative default
        return 120  # Typical 8-core CPU

    def _estimate_gpu_utilization(self, model: str, provider: str, tokens: int) -> float:
        """Estimate GPU utilization during inference (0-1)."""
        # Larger models and more tokens = higher utilization
        model_lower = model.lower()

        # Base utilization by model size
        if any(size in model_lower for size in ["70b", "72b", "405b"]):
            base_util = 0.95  # Large models max out GPU
        elif any(size in model_lower for size in ["30b", "32b", "34b"]):
            base_util = 0.85  # Medium-large models
        elif any(size in model_lower for size in ["13b", "14b", "15b"]):
            base_util = 0.70  # Medium models
        elif any(size in model_lower for size in ["7b", "8b", "9b"]):
            base_util = 0.60  # Small models
        elif any(size in model_lower for size in ["3b", "1b", "1.5b"]):
            base_util = 0.40  # Tiny models
        else:
            base_util = 0.70  # Unknown, assume medium

        # Adjust for token count (more tokens = sustained load)
        if tokens > 2000:
            token_multiplier = 1.1
        elif tokens > 1000:
            token_multiplier = 1.05
        else:
            token_multiplier = 1.0

        return min(1.0, base_util * token_multiplier)

    def _estimate_cpu_utilization(self, model: str, provider: str) -> float:
        """Estimate CPU utilization during inference (0-1)."""
        # CPU usage depends on provider and model
        if provider.lower() == "ollama":
            return 0.30  # Ollama uses CPU for preprocessing
        elif provider.lower() in ["lm_studio", "lmstudio"]:
            return 0.25  # LM Studio optimized
        else:
            return 0.35  # Generic providers


# Global instance - can be configured via environment
_default_calculator: LocalCostCalculator | None = None


def get_cost_calculator() -> LocalCostCalculator:
    """
    Get the global cost calculator instance.
    
    Default policy provides realistic cost estimates for local models based on
    electricity and hardware costs. Users can opt-in to zero cost via
    ORKA_LOCAL_COST_POLICY=zero_legacy
    """
    global _default_calculator
    if _default_calculator is None:
        # Default to "calculate" to provide realistic cost estimates for local models
        # Users can set ORKA_LOCAL_COST_POLICY=zero_legacy if they prefer $0.00
        policy = os.environ.get("ORKA_LOCAL_COST_POLICY", "calculate")
        _default_calculator = LocalCostCalculator(policy=policy)
    return _default_calculator


def calculate_local_llm_cost(
    latency_ms: float,
    tokens: int,
    model: str,
    provider: str = "unknown",
) -> Optional[float]:
    """
    Calculate local LLM inference cost.

    Convenience function that uses the global calculator.

    Returns:
        Cost in USD, or None if null_fail policy

    Raises:
        ValueError: If null_fail policy is enabled
    """
    calculator = get_cost_calculator()
    return calculator.calculate_inference_cost(latency_ms, tokens, model, provider)
