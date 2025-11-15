# GraphScout Execution Modes

## Overview

GraphScout can operate in three different modes depending on whether you prioritize **validation**, **execution**, or **both**. This guide explains when to use each mode.

## The Three Modes

### 1. Validation-Only Mode (Planning)

**Location:** GraphScout inside a validation loop  
**Purpose:** Validate execution plans before committing  
**Execution:** NO - plans are validated but never executed

#### How It Works

```yaml
orchestrator:
  agents:
    - validation_loop  # GraphScout + PlanValidator inside
    - report           # Shows validated plan only

agents:
  - id: validation_loop
    type: loop
    internal_workflow:
      agents:
        - graphscout_router    # Proposes path
        - plan_validator       # Validates path
```

**Flow:**
1. GraphScout proposes: `["search", "analyze", "generate"]`
2. PlanValidator scores: `0.72` (below threshold)
3. Loop repeats with feedback
4. GraphScout improves: `["search", "analyze", "validate", "generate"]`
5. PlanValidator scores: `0.88` (approved)
6. **Loop exits** - plan returned but **NOT executed**

#### When to Use

- ✅ Learning/training GraphScout on new domains
- ✅ Expensive operations requiring approval
- ✅ Regulatory environments needing audit trails
- ✅ Plan caching for future execution
- ✅ Quality assurance before deployment

#### Trade-offs

**Pros:**
- Guaranteed quality before execution
- Iterative refinement
- Full audit trail
- Safe exploration

**Cons:**
- Plans never execute (separate step needed)
- Higher latency (validation iterations)
- 2-3x cost (validate then execute separately)
- Complex orchestration

#### Examples

- `plan_validator_with_graphscout.yml` - GraphScout + PlanValidator loop
- `plan_validator_complex.yml` - Enterprise design validation
- `plan_validator_simple.yml` - Simple workflow validation

---

### 2. Real-Time Execution Mode (Production)

**Location:** GraphScout in main orchestrator  
**Purpose:** Immediate routing and execution  
**Execution:** YES - selected agents execute immediately

#### How It Works

```yaml
orchestrator:
  agents:
    - context_builder
    - graphscout_router  # Routes + executes
    - quality_monitor    # Checks after execution
    - synthesizer

agents:
  - id: graphscout_router
    type: graph-scout
    # GraphScout evaluates paths and returns decision
    # Orchestrator EXECUTES the selected agents
```

**Flow:**
1. GraphScout evaluates paths
2. Returns: `{"target": ["search", "analyze", "generate"]}`
3. **Orchestrator executes** `search` agent
4. **Orchestrator executes** `analyze` agent (with search results)
5. **Orchestrator executes** `generate` agent (with all results)
6. Quality monitor reviews execution
7. Final synthesizer creates response

#### When to Use

- ✅ Production user-facing applications
- ✅ Real-time routing decisions
- ✅ Well-tuned, trusted GraphScout
- ✅ Speed-critical scenarios
- ✅ High-throughput workflows

#### Trade-offs

**Pros:**
- Fast (no validation delay)
- Cost-efficient (1x execution only)
- Real results immediately
- Simple orchestration

**Cons:**
- No pre-execution validation
- Mistakes execute before detection
- Quality checked after execution
- Requires trusted GraphScout

#### Examples

- `graphscout_validated_execution.yml` - Basic execution mode
- `graphscout_realtime_execution.yml` - Production-ready with quality monitoring

---

### 3. Hybrid Mode (Validate Then Execute)

**Location:** Validation loop + secondary execution  
**Purpose:** Best of both worlds - validate then execute  
**Execution:** YES (conditional) - only approved plans execute

#### How It Works

```yaml
orchestrator:
  agents:
    - validation_loop      # Phase 1: Validate plan
    - conditional_executor # Phase 2: Execute if approved
    - execution_report     # Phase 3: Report

agents:
  - id: validation_loop
    type: loop
    # Validates proposed path
    
  - id: conditional_executor
    type: local_llm
    # Checks if threshold_met
    # If yes, triggers execution
    # If no, blocks execution
```

**Flow:**
1. **Validation Phase:**
   - Loop validates path proposal
   - Iterates until quality threshold met
   - Returns approved/rejected decision

2. **Execution Phase:**
   - If approved: Execute validated agents
   - If rejected: Block execution, provide feedback

3. **Reporting Phase:**
   - Shows validation trace
   - Shows execution results (if executed)
   - Provides quality analysis

#### When to Use

- ✅ High-stakes decisions
- ✅ First-time patterns (validate) + known patterns (execute)
- ✅ Learning mode with gradual rollout
- ✅ Regulatory compliance + performance
- ✅ Plan caching with execution

#### Trade-offs

**Pros:**
- Safety of validation
- Efficiency of execution
- Conditional execution
- Full audit trail

**Cons:**
- Complex orchestration
- Higher latency for new patterns
- Requires meta-orchestration support
- More moving parts

#### Examples

- `graphscout_validate_then_execute.yml` - Full hybrid implementation

---

## Performance Comparison

| Mode | Latency | Cost | Quality | Use Case |
|------|---------|------|---------|----------|
| **Validation-Only** | High (30-60s) | 2-3x | Pre-guaranteed | Learning, Compliance |
| **Real-Time** | Low (10-20s) | 1x | Post-monitored | Production, Speed |
| **Hybrid** | Medium (20-40s) | 1.5-2x | Pre-guaranteed | High-stakes, Gradual |

## Decision Framework

### Choose Validation-Only if:
```
(execution_cost > $1) OR
(mistakes_are_unrecoverable) OR
(regulatory_approval_required) OR
(training_graphscout)
```

### Choose Real-Time if:
```
(latency_critical) AND
(graphscout_well_tuned) AND
(mistakes_recoverable) AND
(production_ready)
```

### Choose Hybrid if:
```
(high_stakes) AND
(need_audit_trail) AND
(can_tolerate_medium_latency) AND
(want_conditional_execution)
```

## Implementation Patterns

### Pattern 1: Validation-Only

```yaml
# GraphScout INSIDE loop - proposes but doesn't execute
- id: validation_loop
  type: loop
  internal_workflow:
    agents: [graphscout_router, plan_validator]

# Result: Validated plan (not executed)
```

### Pattern 2: Real-Time Execution

```yaml
# GraphScout in MAIN orchestrator - executes immediately
orchestrator:
  agents: 
    - graphscout_router  # Routes + orchestrator executes
    - quality_monitor    # Checks post-execution
```

### Pattern 3: Hybrid

```yaml
# Two-phase approach
orchestrator:
  agents:
    - validation_loop      # Validate plan
    - conditional_executor # Execute if approved
```

## Best Practices

### For Validation-Only:
1. Set appropriate `score_threshold` (0.80-0.90)
2. Use `strict` or `moderate` preset
3. Provide clear feedback in loop metadata
4. Cache validated plans for reuse
5. Consider time limits (max_loops: 3-5)

### For Real-Time:
1. Tune GraphScout thoroughly before production
2. Implement quality monitoring
3. Use fallback strategies
4. Monitor execution metrics
5. Have rollback procedures

### For Hybrid:
1. Validate new patterns, execute known patterns
2. Cache approved plans
3. Gradually move validated patterns to real-time
4. Monitor quality across both modes
5. Implement execution gates

## Migration Path

### Stage 1: Learning (Validation-Only)
- Use validation loop exclusively
- Build library of validated patterns
- Tune scoring thresholds
- Collect quality metrics

### Stage 2: Gradual Rollout (Hybrid)
- Validate new patterns
- Execute known-good patterns
- Cache successful validations
- Monitor quality closely

### Stage 3: Production (Real-Time)
- Execute trusted patterns immediately
- Post-execution quality checks
- Fallback to validation for edge cases
- Continuous monitoring

## Summary

| Aspect | Validation-Only | Real-Time | Hybrid |
|--------|----------------|-----------|--------|
| **GraphScout Location** | Inside loop | Main orchestrator | Both |
| **Execution** | Never | Always | Conditional |
| **Quality Gate** | Before | After | Before + After |
| **Latency** | High | Low | Medium |
| **Cost** | High | Low | Medium |
| **Safety** | Maximum | Moderate | High |
| **Complexity** | Medium | Low | High |
| **Best For** | Learning | Production | High-stakes |

## Conclusion

There's no one-size-fits-all approach. Choose based on:

- **Validation-Only**: When quality is paramount, cost is acceptable
- **Real-Time**: When speed is critical, GraphScout is trusted
- **Hybrid**: When you need both safety and performance

Most production systems will use a **combination**:
- Real-time for 80% of queries (known patterns)
- Validation for 15% of queries (new patterns)
- Hybrid for 5% of queries (high-stakes decisions)

The key is understanding the trade-offs and choosing the right mode for each scenario.

