# Testing Improvements Roadmap

## Overview

This document outlines improvements needed to enhance the OrKa test suite, specifically focusing on reducing mocking and adding more E2E tests. These improvements were identified as part of the GraphScout V1.0 Production Fixes plan.

---

## Current State

### Existing Test Coverage
- **Unit Tests**: 64 test files in `tests/unit/`
- **Integration Tests**: 6 test files in `tests/integration/`
- **Performance Tests**: 2 test files in `tests/performance/`

### Current Testing Approach
- Heavy use of mocking (AsyncMock, MagicMock)
- Component isolation for fast execution
- Limited E2E workflow validation
- Some integration tests use real components

### New Tests Added (V1.0)
- `tests/integration/test_graphscout_deterministic.py` - Deterministic evaluator tests
- `tests/integration/test_path_executor_integration.py` - PathExecutor integration tests
- `tests/integration/test_complete_workflows.py` - E2E workflow stubs

---

## Reducing Mocking in Existing Tests

### Philosophy

Mocking should be used strategically:
- **Mock external services** (Kafka, Redis, OpenAI) to avoid dependencies
- **Use real components** for internal logic (scoring, validation, routing)
- **Test integration points** with minimal mocking at boundaries

### High-Impact Refactoring Opportunities

#### 1. GraphScout Component Tests
**File**: `tests/unit/test_graph_scout_components.py`

**Current**: Heavy mocking of PathScorer, GraphIntrospector, SafetyController

**Improvement**:
```python
# Instead of:
mock_scorer = AsyncMock()
mock_scorer.score_candidates.return_value = [...]

# Use real scorer:
from orka.orchestrator.path_scoring import PathScorer
from orka.nodes.graph_scout_agent import GraphScoutConfig

config = GraphScoutConfig()
real_scorer = PathScorer(config)
results = await real_scorer.score_candidates(candidates, question, context)
```

**Benefits**:
- Tests real scoring logic
- Catches configuration issues
- Validates threshold behavior

#### 2. Orchestrator Tests
**File**: `tests/unit/test_orchestrator_composition.py`

**Current**: Mocks agent execution completely

**Improvement**:
- Use real agent instances for simple agents
- Mock only external I/O (network, file system)
- Test actual execution flow

**Example**:
```python
# Instead of mocking all agents
class SimpleTestAgent(BaseNode):
    async def _run_impl(self, context):
        return {"result": "test"}

# Use in orchestrator tests
orchestrator.agents = {
    "test_agent": SimpleTestAgent(node_id="test_agent")
}
```

#### 3. PathScorer Tests
**File**: `tests/unit/test_path_scoring.py` (if exists)

**Current**: May mock config and components

**Improvement**:
- Use real GraphScoutConfig with test values
- Test actual scoring calculations
- Validate configurable thresholds

#### 4. DryRunEngine Tests  
**File**: `tests/unit/test_dry_run_engine.py` (if exists)

**Current**: Likely mocks LLM completely

**Improvement**:
```python
# Test deterministic fallback with real components
evaluator = SmartPathEvaluator(config)
# Disable LLM, use real deterministic evaluator
config.llm_evaluation_enabled = False

results = await evaluator.simulate_candidates(...)
# Validate real heuristic logic
```

---

## E2E Test Expansion

### Infrastructure Requirements

#### Docker Compose for Services
Create `docker-compose.test.yml`:
```yaml
version: '3.8'
services:
  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
  
  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
    ports:
      - "9092:9092"
```

#### Test Configuration
- Separate test configs for CI
- Mock external LLM services
- Use local Redis/Kafka for state

### Proposed E2E Tests

#### 1. Complete Validated Execution Workflow
**File**: `tests/integration/test_validated_execution_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_graphscout_validator_executor_workflow():
    """
    Test complete workflow:
    1. Load graph_scout_validated_loop.yml
    2. Run orchestrator
    3. Validate GraphScout proposes path
    4. Validate PlanValidator scores path
    5. Validate PathExecutor executes approved path
    6. Check metrics collected at each stage
    """
    config = load_yaml_config("examples/graph_scout_validated_loop.yml")
    orchestrator = await OrkaOrchestrator.from_config(config)
    
    result = await orchestrator.run({"input": "Test query"})
    
    # Validate workflow stages
    assert "path_discovery_loop" in result["trace"]
    assert "path_executor" in result["trace"]
    assert "final_execution" in result["trace"]
    
    # Validate metrics
    assert result["metrics"]["graphscout"]["candidates_discovered"] > 0
    assert result["metrics"]["path_executor"]["successful_agents"] > 0
```

#### 2. Deterministic Fallback E2E
**File**: `tests/integration/test_fallback_e2e.py`

Test that simulates LLM failure and validates fallback behavior in complete workflow.

#### 3. Schema Validation E2E
**File**: `tests/integration/test_schema_validation_e2e.py`

Test that injects malformed LLM responses and validates error handling.

#### 4. Observability E2E
**File**: `tests/integration/test_observability_e2e.py`

Test that runs workflow and validates all metrics and structured logs are emitted correctly.

---

## Prioritized Refactoring Plan

### Phase 1: Low-Hanging Fruit (1-2 days)
1. Update PathScorer tests to use real config
2. Update DeterministicPathEvaluator tests (already using real components)
3. Add real component tests for schema validation

### Phase 2: Component Integration (3-5 days)
1. Refactor GraphScout component tests
2. Add real GraphIntrospector tests
3. Update SafetyController tests

### Phase 3: E2E Infrastructure (5-7 days)
1. Set up docker-compose for tests
2. Create E2E test fixtures
3. Implement 2-3 core E2E workflows

### Phase 4: Comprehensive E2E (Ongoing)
1. Add E2E test for each example YAML
2. Performance benchmarking
3. Chaos testing (fault injection)

---

## Testing Best Practices

### When to Mock
✅ **Do Mock**:
- External API calls (OpenAI, other LLMs)
- External services (Kafka producers/consumers initially)
- File system operations (unless testing file operations)
- Time-dependent operations (use `freezegun`)

❌ **Don't Mock**:
- Internal business logic (scoring, validation)
- Configuration objects
- Data structures (candidates, results)
- Synchronous utility functions

### Test Organization

```
tests/
├── unit/                      # Component tests, some mocking
│   ├── orchestrator/         # Orchestrator logic tests
│   ├── nodes/                # Node implementation tests
│   └── tools/                # Tool tests
├── integration/              # Multi-component tests, minimal mocking
│   ├── test_graphscout_*.py # GraphScout workflows
│   └── test_orchestrator_*.py # Orchestrator workflows
├── e2e/                      # Full workflow tests (new)
│   ├── test_examples_*.py   # Test each example YAML
│   └── test_scenarios_*.py  # Test common scenarios
└── performance/              # Performance benchmarks
    └── test_graphscout_perf.py
```

---

## Measuring Progress

### Metrics to Track
1. **Mock Reduction**: % of tests using real components
2. **E2E Coverage**: % of example YAMLs with E2E tests
3. **Integration Coverage**: Lines covered by integration tests
4. **Test Speed**: Average test execution time

### Success Criteria
- [ ] 50% reduction in mocking for core components
- [ ] E2E tests for top 5 example workflows
- [ ] All new code includes integration tests
- [ ] CI runs full E2E suite (with external services)

---

## Implementation Notes

### Current V1.0 Implementation Status

#### ✅ Completed
- Created `test_graphscout_deterministic.py` (uses real DeterministicPathEvaluator)
- Created `test_path_executor_integration.py` (minimal mocking, real PathExecutor)
- Created E2E test stubs in `test_complete_workflows.py`

#### 📋 Deferred to Post-V1.0
- Refactoring existing unit tests to reduce mocking
- Full E2E test implementation with external services
- Docker-compose test infrastructure
- CI integration with service dependencies

**Rationale**: Core production fixes are complete and tested. Test improvements are valuable but not blocking for V1.0 release. Can be implemented incrementally.

---

## Resources

### Tools
- `pytest-asyncio` - Already in use
- `pytest-docker` - For docker-compose integration
- `pytest-benchmark` - For performance tests
- `freezegun` - For time-dependent tests

### Documentation
- [Testing Best Practices](TESTING.md)
- [Integration Examples](INTEGRATION_EXAMPLES.md)
- [Debugging Guide](DEBUGGING.md)

---

## Conclusion

The test suite improvements outlined here will:
1. Increase confidence in component interactions
2. Catch integration issues earlier
3. Validate real-world workflows
4. Reduce brittleness from over-mocking

**Current State (V1.0)**: Foundation laid with integration tests for new components. Production-ready with existing test coverage plus new integration tests.

**Future State**: Comprehensive E2E coverage with minimal mocking, full workflow validation, and performance benchmarking.

Implementation should be incremental and prioritized based on:
- Risk (critical paths tested first)
- Value (high-impact workflows)
- Effort (low-hanging fruit first)

