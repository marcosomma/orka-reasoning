# Local LLM Cost Calculation

## Overview

OrKa now calculates **real operating costs** for local LLM inference instead of fantasy $0.00 costs. Local models aren't free - they consume electricity and require hardware investment.

## Cost Components

### 1. Electricity Consumption
- GPU power consumption during inference (based on TDP and utilization)  
- CPU power consumption for preprocessing and coordination
- Time-based calculation using actual inference latency

### 2. Hardware Amortization  
- Depreciation of GPU, CPU, RAM, storage over expected lifespan
- Conservative 3-year depreciation period (configurable)
- Spread across 24/7 usage for realistic cost-per-hour

### 3. Model-Aware Utilization
- Larger models (70B+) → Higher GPU utilization (95%)
- Medium models (7B-13B) → Moderate utilization (60-70%)  
- Small models (1B-3B) → Lower utilization (40%)

## Cost Policies

### `calculate` (Default)
Calculates real costs including electricity and hardware amortization.

```bash
export ORKA_LOCAL_COST_POLICY=calculate
```

**Example Output:**
```
Model: llama3.2:7b
Tokens: 1,500
Latency: 5,000ms
Cost: $0.000166 (vs GPT-4o-mini: $0.000450)
```

### `null_fail` (Strict)
Sets cost to `null` and **hard-fails pipelines** on any null costs.

```bash
export ORKA_LOCAL_COST_POLICY=null_fail
```

**Result:** Pipeline crashes with detailed error message requiring real cost configuration.

### `zero_legacy` (Deprecated)
Legacy $0.00 cost behavior - **not recommended**.

```bash
export ORKA_LOCAL_COST_POLICY=zero_legacy
```

## Configuration

### Environment Variables

```bash
# Cost policy
export ORKA_LOCAL_COST_POLICY=calculate

# Electricity pricing (USD per kWh)
export ORKA_ELECTRICITY_RATE_USD_KWH=0.15

# Hardware costs (total system cost in USD)
export ORKA_HARDWARE_COST_USD=3000

# Power consumption (watts TDP)
export ORKA_GPU_TDP_WATTS=350
export ORKA_CPU_TDP_WATTS=120

# Regional defaults
export ORKA_REGION=US  # US, EU, DE, NO, CN, JP, etc.
```

### Auto-Detection

Without explicit configuration, OrKa attempts to:
- Detect GPU model and estimate TDP
- Detect CPU cores and calculate power consumption  
- Use regional electricity rates
- Estimate hardware costs based on detected GPU

## Cost Examples

### Typical Gaming Rig
- **Hardware:** RTX 4080 + i7 CPU (~$2,500 total)
- **Electricity:** $0.16/kWh (US average)
- **7B model cost:** ~$0.0001 per 1K tokens
- **4.5x cheaper than GPT-4o-mini**

### High-End Workstation  
- **Hardware:** RTX 4090 + high-end CPU (~$4,000 total)
- **Electricity:** $0.12/kWh (cheap region)
- **7B model cost:** ~$0.00015 per 1K tokens

### Cloud GPU Instance
- **Hardware:** A100 equivalent (~$8,000 amortized)
- **Electricity:** $0.25/kWh (cloud pricing)
- **7B model cost:** ~$0.0003 per 1K tokens

## Cost Breakdown Analysis

```
Local cost breakdown: 
  electricity=$0.000034 (power consumption)
  amortization=$0.000066 (hardware depreciation) 
  total=$0.000100
```

**Key Insight:** Hardware amortization typically dominates electricity costs for most setups.

## Integration

### LocalLLMAgent
All local LLM agents now use real cost calculation:

```python
# Before (fantasy)
"cost_usd": 0.0  # Local models are free

# After (reality)  
"cost_usd": 0.000166  # Real electricity + hardware costs
```

### Pipeline Failure
With `null_fail` policy, pipelines crash on null costs:

```python
ValueError: Pipeline failed due to null cost in agent 'local_llm_summary' 
(model: llama3.2:7b). Configure real cost calculation or use cloud models.
```

### Meta Reports
Cost aggregation handles null values appropriately:
- `calculate`: Includes real costs in totals
- `null_fail`: Crashes before reaching meta report
- `zero_legacy`: Uses deprecated $0.00 with warnings

## Best Practices

### 1. Use Real Costs
Set `ORKA_LOCAL_COST_POLICY=calculate` for accurate cost tracking.

### 2. Configure Your Setup
Provide actual electricity rates and hardware costs for precise calculations:

```bash
export ORKA_ELECTRICITY_RATE_USD_KWH=0.12  # Your actual rate
export ORKA_HARDWARE_COST_USD=3500         # Your actual hardware cost
```

### 3. Enforce Real Costs
Use `null_fail` policy in production to prevent cost blind spots:

```bash
export ORKA_LOCAL_COST_POLICY=null_fail
```

### 4. Monitor Costs
Compare local vs cloud costs to optimize model selection:

```
GPT-4o-mini: $0.000450 per 1K tokens
Local 7B:    $0.000100 per 1K tokens (4.5x cheaper)
Local 70B:   $0.000110 per 1K tokens (4.1x cheaper)
```

## Migration Guide

### From Fantasy $0.00
1. **Immediate:** Set `ORKA_LOCAL_COST_POLICY=calculate`
2. **Optional:** Configure environment variables for accuracy
3. **Production:** Consider `null_fail` policy for strict cost tracking

### Cost Impact
- **Typical local inference:** $0.0001-0.0003 per 1K tokens
- **Still much cheaper than cloud:** 3-10x cost advantage
- **Realistic for budgeting:** Actual operating expenses

## Troubleshooting

### "Failed to calculate local LLM cost"
- Install `GPUtil` for GPU detection: `pip install GPUtil`
- Install `psutil` for CPU detection: `pip install psutil`  
- Or set manual values via environment variables

### Pipeline Failures with null_fail
- Configure real cost calculation environment variables
- Or switch to `calculate` policy: `ORKA_LOCAL_COST_POLICY=calculate`
- Or use cloud models for guaranteed cost tracking

### Unrealistic Costs
- Verify electricity rate: `ORKA_ELECTRICITY_RATE_USD_KWH=0.15`
- Check hardware cost: `ORKA_HARDWARE_COST_USD=3000`
- Validate power consumption: `ORKA_GPU_TDP_WATTS=350`

## Technical Details

### Cost Formula
```
total_cost = electricity_cost + amortization_cost

electricity_cost = (gpu_power + cpu_power) * time_hours * rate_per_kwh
amortization_cost = hardware_cost / lifespan_hours * time_hours

gpu_power = gpu_tdp * utilization_factor
cpu_power = cpu_tdp * utilization_factor  
```

### Utilization Factors
- GPU: 0.4-0.95 based on model size and token count
- CPU: 0.25-0.35 based on provider efficiency

### Default Values
- Electricity: $0.16/kWh (US average) or regional rates
- Hardware: $2,000 (estimated from GPU detection)
- GPU TDP: 250W (typical high-end GPU)
- CPU TDP: 120W (typical 8-core CPU)
- Lifespan: 36 months hardware depreciation 