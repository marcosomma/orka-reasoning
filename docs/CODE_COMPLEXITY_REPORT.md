# Orka Codebase Complexity Report

**Generated:** December 20, 2025

This report identifies the top 20 largest and most complex files in the `orka/` folder.

---

## Top 20 Largest and Most Complex Files

| Rank | File | Lines | Size (KB) | Classes | Functions | Async Funcs | Complexity |
|------|------|-------|-----------|---------|-----------|-------------|------------|
| **1** | `memory/redisstack_logger.py` | ~~1,954~~ **365** | ~~95.6~~ 18.2 | 1 | 48→9 | 0 | ✅ Done |
| **2** | `orchestrator/dry_run_engine.py` | ~~1,287~~ **312** | ~~65.2~~ 15.4 | 4→1 | 25→12 | 11→5 | ✅ Done |
| **3** | `nodes/memory_reader_node.py` | **1,154** | 53.0 | 1 | 15 | 9 | 🟠 High |
| **4** | `orchestrator/simplified_prompt_rendering.py` | **953** | 50.0 | 1 | 12 | 0 | 🟠 High |
| **5** | `memory/base_logger.py` | **949** | 45.0 | 1 | 38 | 0 | 🟠 High |
| **6** | `tui/components.py` | **902** | 42.7 | 1 | 21 | 0 | 🟠 High |
| **7** | `memory/redis_logger.py` | **742** | 33.8 | 1 | 19 | 0 | 🟡 Medium |
| **8** | `nodes/memory_writer_node.py` | **740** | 39.9 | 1 | 11 | 1 | 🟡 Medium |
| **9** | `orchestrator/graph_introspection.py` | **739** | 36.7 | 1 | 15 | 4 | 🟡 Medium |
| **10** | `agents/llm_agents.py` | **732** | 33.5 | 3 | 9 | 3 | 🟡 Medium |
| **11** | `nodes/path_executor_node.py` | **669** | 29.1 | 1 | 11 | 2 | 🟡 Medium |
| **12** | `tui/textual_widgets.py` | **606** | 28.8 | 5 | 29 | 0 | 🟡 Medium |
| **13** | `memory/presets.py` | **571** | 24.1 | 0 | 6 | 0 | 🟢 Low |
| **14** | `utils/bootstrap_memory_index.py` | **570** | 26.5 | 0 | 5 | 2 | 🟢 Low |
| **15** | `utils/json_parser.py` | **554** | 22.9 | 2 | 17 | 0 | 🟡 Medium |
| **16** | `agents/local_llm_agents.py` | **541** | 25.8 | 1 | 2 | 4 | 🟡 Medium |
| **17** | `tui/data_manager.py` | **527** | 24.9 | 3 | 33 | 0 | 🟡 Medium |
| **18** | `scoring/presets.py` | **504** | 19.4 | 0 | 4 | 0 | 🟢 Low |
| **19** | `nodes/loop/score_extractor.py` | **501** | 25.7 | 1 | 3 | 2 | 🟡 Medium |
| **20** | `orchestrator/boolean_scoring.py` | **491** | 22.9 | 2 | 5 | 6 | 🟡 Medium |

---

## Complexity Legend

| Symbol | Level | Description |
|--------|-------|-------------|
| 🔴 | Critical | >1,000 lines, high method count, refactoring recommended |
| 🟠 | High | 900-1,000 lines, significant complexity |
| 🟡 | Medium | 500-900 lines, moderate complexity |
| 🟢 | Low | <600 lines, manageable complexity |

---

## Key Observations

### 🔴 Critical Complexity (Top 3)

#### 1. `memory/redisstack_logger.py` ~~(1,954 lines)~~ → **365 lines ✅ REFACTORED**
- ~~**Most complex file** in the entire codebase~~ → Now modular with 9 mixins
- ~~Single class with **48 methods**~~ → Main class with 9 core methods, rest in mixins
- ~~Handles HNSW vector indexing, Redis operations, memory decay, and serialization~~
- **Completed refactoring** (Dec 20, 2025):
  - ✅ `VectorIndexManager` - HNSW operations
  - ✅ `ConnectionManager` - Connection pooling & thread safety  
  - ✅ `MemoryDecayMixin` - Decay algorithms
  - ✅ `MemorySearchMixin` - Vector & text search
  - ✅ `MemoryCRUDMixin` - CRUD operations
  - ✅ `MetricsMixin` - Stats & performance
  - ✅ `EmbeddingMixin` - Embedding generation
  - ✅ 108 new unit tests added

#### 2. `orchestrator/dry_run_engine.py` ~~(1,287 lines)~~ → **312 lines ✅ REFACTORED**
- ~~Heavy simulation engine with **4 classes** and **11 async methods**~~ → Now modular with 7 mixins
- ~~Complex state management for dry-run workflows~~
- **Completed refactoring** (Dec 20, 2025):
  - ✅ `DeterministicPathEvaluator` - Heuristic fallback
  - ✅ `LLMProviderMixin` - Ollama/LM Studio integration
  - ✅ `PromptBuilderMixin` - Prompt construction
  - ✅ `ResponseParserMixin` - JSON parsing
  - ✅ `AgentAnalyzerMixin` - Agent analysis
  - ✅ `PathEvaluatorMixin` - Path evaluation
  - ✅ 64 new unit tests added

#### 3. `nodes/memory_reader_node.py` (1,154 lines)
- Large node with **9 async methods**
- Handles memory retrieval, filtering, and processing
- **Recommendation:** Extract filtering logic into a separate `MemoryFilter` class

---

### 🟠 High Complexity (Ranks 4-6)

| File | Issue | Recommendation |
|------|-------|----------------|
| `simplified_prompt_rendering.py` | Template rendering with Jinja2, complex string manipulation | Extract template helpers |
| `base_logger.py` | Base class with 38 methods, inheritance complexity | Consider composition over inheritance |
| `tui/components.py` | UI state management, 21 methods | Split into smaller component files |

---

## Complexity Hotspots by Module

| Module | Files in Top 20 | Total Lines | Notes |
|--------|-----------------|-------------|-------|
| `memory/` | 4 | ~~4,216~~ 2,627 | Refactored - 1,589 lines moved to mixins |
| `orchestrator/` | 4 | ~~3,470~~ 2,495 | Refactored - 975 lines moved to mixins |
| `nodes/` | 4 | 3,064 | Node implementations |
| `tui/` | 3 | 2,035 | UI components |
| `agents/` | 2 | 1,273 | LLM integration |
| `utils/` | 2 | 1,124 | Utility functions |
| `scoring/` | 1 | 504 | Scoring logic |

---

## Recommendations

### Immediate Actions
1. **Refactor `redisstack_logger.py`** - Split into 4-5 smaller classes
2. **Add unit tests** for complex methods in top 5 files
3. **Document** complex algorithms in `dry_run_engine.py`

### Long-term Improvements
1. Apply **Single Responsibility Principle** to files >800 lines
2. Consider **dependency injection** for memory backends
3. Extract **common patterns** into shared utilities

---

## Metrics Summary

- **Total files analyzed:** 20
- **Combined lines of code:** ~~14,682~~ 12,118 (after refactoring)
- **Average file size:** ~~734~~ 606 lines
- **Files exceeding 1,000 lines:** ~~3~~ 1
- **Files with >30 functions:** ~~3~~ 2 (`base_logger`, `data_manager`) - `redisstack_logger` & `dry_run_engine` refactored

---

## ✅ Refactoring Checklist

Track progress on addressing complexity issues in each file.

### 🔴 Critical Priority (Must Fix)

- [x] **`memory/redisstack_logger.py`** ~~(1,954 lines, 48 methods)~~ → **365 lines (81.3% reduction) ✅**
  - [x] Extract `VectorIndexManager` class for HNSW operations
  - [x] Extract `ConnectionManager` class for connection pooling
  - [x] Extract `MemoryDecayMixin` for decay algorithms
  - [x] Extract `MemorySearchMixin` for search operations
  - [x] Extract `MemoryCRUDMixin` for CRUD operations
  - [x] Extract `MetricsMixin` for stats and metrics
  - [x] Extract `OrchestrationLoggingMixin` for event logging
  - [x] Extract `RedisInterfaceMixin` for Redis interface methods
  - [x] Extract `EmbeddingMixin` for embedding generation
  - [x] Add comprehensive unit tests (108 new tests)
  - [x] Add inline documentation for complex methods
  
  **New module structure:** `orka/memory/redisstack/`
  - `connection_manager.py` - Connection pooling & thread safety
  - `vector_index_manager.py` - HNSW index management
  - `decay_mixin.py` - Memory decay & TTL
  - `search_mixin.py` - Vector & text search
  - `crud_mixin.py` - CRUD operations
  - `metrics_mixin.py` - Stats & performance metrics
  - `logging_mixin.py` - Orchestration event logging
  - `redis_interface_mixin.py` - Direct Redis interface
  - `embedding_mixin.py` - Embedding generation

- [x] **`orchestrator/dry_run_engine.py`** ~~(1,287 lines, 4 classes)~~ → **312 lines (75.8% reduction) ✅**
  - [x] Extract `PathEvaluation` and `ValidationResult` data classes
  - [x] Extract `DeterministicPathEvaluator` class
  - [x] Extract `LLMProviderMixin` for Ollama/LM Studio integration
  - [x] Extract `PromptBuilderMixin` for prompt generation
  - [x] Extract `ResponseParserMixin` for parsing LLM responses
  - [x] Extract `AgentAnalyzerMixin` for agent information extraction
  - [x] Extract `PathEvaluatorMixin` for path evaluation logic
  - [x] Add comprehensive unit tests (64 new tests)
  
  **New module structure:** `orka/orchestrator/dry_run/`
  - `data_classes.py` - PathEvaluation, ValidationResult
  - `deterministic_evaluator.py` - Heuristic fallback evaluator
  - `llm_providers.py` - Ollama & LM Studio async clients
  - `prompt_builder.py` - LLM prompt construction
  - `response_parser.py` - JSON response parsing
  - `agent_analyzer.py` - Agent capability inference
  - `path_evaluator.py` - Path scoring & outcome generation

- [ ] **`nodes/memory_reader_node.py`** (1,154 lines, 9 async methods)
  - [ ] Extract `MemoryFilter` class for filtering logic
  - [ ] Simplify async method chains
  - [ ] Add unit tests for retrieval logic
  - [ ] Document memory processing pipeline

### 🟠 High Priority (Should Fix)

- [ ] **`orchestrator/simplified_prompt_rendering.py`** (953 lines)
  - [ ] Extract template helper functions
  - [ ] Reduce Jinja2 complexity
  - [ ] Add template validation tests

- [ ] **`memory/base_logger.py`** (949 lines, 38 methods)
  - [ ] Consider composition over inheritance
  - [ ] Split into focused abstract classes
  - [ ] Document inheritance chain

- [ ] **`tui/components.py`** (902 lines, 21 methods)
  - [ ] Split into smaller component files
  - [ ] Separate state management from rendering
  - [ ] Add component documentation

### 🟡 Medium Priority (Consider Fixing)

- [ ] **`memory/redis_logger.py`** (742 lines, 19 methods)
  - [ ] Review for code duplication with redisstack_logger
  - [ ] Extract common patterns
  - [ ] Add missing unit tests

- [ ] **`nodes/memory_writer_node.py`** (740 lines, 11 methods)
  - [ ] Review serialization logic
  - [ ] Add error handling tests
  - [ ] Document write patterns

- [ ] **`orchestrator/graph_introspection.py`** (739 lines, 15 methods)
  - [ ] Document graph analysis algorithms
  - [ ] Add visualization helpers
  - [ ] Improve test coverage

- [ ] **`agents/llm_agents.py`** (732 lines, 3 classes)
  - [ ] Document agent lifecycle
  - [ ] Add integration tests
  - [ ] Review error handling

- [ ] **`nodes/path_executor_node.py`** (669 lines, 11 methods)
  - [ ] Document execution flow
  - [ ] Add edge case tests
  - [ ] Review async patterns

- [ ] **`tui/textual_widgets.py`** (606 lines, 5 classes)
  - [ ] Split into individual widget files
  - [ ] Add widget documentation
  - [ ] Review accessibility

- [ ] **`utils/json_parser.py`** (554 lines, 17 functions)
  - [ ] Add more error recovery tests
  - [ ] Document parsing strategies
  - [ ] Review edge cases

- [ ] **`agents/local_llm_agents.py`** (541 lines, 4 async methods)
  - [ ] Document provider integration
  - [ ] Add timeout handling tests
  - [ ] Review connection pooling

- [ ] **`tui/data_manager.py`** (527 lines, 33 methods)
  - [ ] Reduce method count
  - [ ] Extract data utilities
  - [ ] Add caching documentation

- [ ] **`nodes/loop/score_extractor.py`** (501 lines, 3 async methods)
  - [ ] Document scoring algorithms
  - [ ] Add extraction tests
  - [ ] Review regex patterns

- [ ] **`orchestrator/boolean_scoring.py`** (491 lines, 6 async methods)
  - [ ] Document scoring logic
  - [ ] Add boundary tests
  - [ ] Review async patterns

### 🟢 Low Priority (Optional)

- [ ] **`memory/presets.py`** (571 lines)
  - [ ] Review preset configurations
  - [ ] Add preset validation
  - [ ] Document preset usage

- [ ] **`utils/bootstrap_memory_index.py`** (570 lines)
  - [ ] Review initialization logic
  - [ ] Add startup tests
  - [ ] Document bootstrap process

- [ ] **`scoring/presets.py`** (504 lines)
  - [ ] Review scoring configurations
  - [ ] Add preset validation
  - [ ] Document scoring presets

---

## 📋 Progress Summary

| Priority | Total Files | Completed | Remaining |
|----------|-------------|-----------|-----------|
| 🔴 Critical | 3 | 2 | 1 |
| 🟠 High | 3 | 0 | 3 |
| 🟡 Medium | 11 | 0 | 11 |
| 🟢 Low | 3 | 0 | 3 |
| **Total** | **20** | **2** | **18** |

---

## 📝 Notes

_Use this section to track decisions, blockers, and additional context._

- [x] **Completed:** `redisstack_logger.py` refactored (Dec 20, 2025) - 81.3% size reduction, 108 new unit tests
- [x] **Completed:** `dry_run_engine.py` refactored (Dec 20, 2025) - 75.8% size reduction, 64 new unit tests
- [ ] **Blocker:** _None identified_
- [ ] **Decision:** _Pending team review for remaining files_
- [ ] **Context:** _Report generated December 20, 2025_

---

*Report generated by codebase analysis tool*

