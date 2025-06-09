# OrKa-Reasoning – Un-official CHANGELOG  
*(derived from the public-repo commit history as of **May 10 2025**)*  

---

## [0.6.3] · 2025-01-27
### Fixed
* **Critical Docker Integration Bug**
  * Fixed "docker-compose file not available" error when running `orka.orka_start` after pip installation
  * Enhanced package distribution configuration to properly include docker directory and all its contents
  * Updated `MANIFEST.in` to explicitly include `orka/docker/*` files in the package
  * Improved `setup.py` and `pyproject.toml` package data configuration with recursive docker file inclusion
  * Docker-compose.yml and related infrastructure files now properly bundled with pip installations
* **Package Distribution Improvements**
  * Enhanced setuptools configuration for better file inclusion in wheel distributions
  * Added comprehensive package data patterns to ensure all necessary docker files are included
  * Improved reliability of `get_docker_dir()` function for both development and production environments

## [0.6.2] · 2025-06-08
### Added
* **Real Local-Cost Model Implementation**
  * New `LocalCostCalculator` class replacing fantasy $0.00 costs with actual operational expenses
  * Three configurable cost policies: `calculate` (default), `null_fail` (strict), `zero_legacy` (deprecated)
  * Model-aware GPU utilization calculations with electricity consumption + hardware amortization
  * Regional electricity rate defaults and environment variable configuration support
  * Cost comparison analysis: Local models 4.5x cheaper than cloud even with real operational costs
* **Enhanced Blob Storage & Deduplication**
  * Improved blob deduplication system in memory logger with SHA-256 hashing
  * Enhanced blob reference resolution with configurable storage options
  * Better memory efficiency for large payload objects and file attachments
  * Versioned blob storage format with backward compatibility
* **Advanced Reporting & Metrics System**
  * Comprehensive meta report aggregation with real cost tracking and performance metrics
  * Enhanced execution time tracking, token counting, and latency analysis
  * Structured cost breakdowns showing electricity vs. hardware amortization components
  * Improved report formatting with detailed agent performance analytics
* **Memory Logger Versioning & Format Evolution**
  * Enhanced memory logger with versioned storage formats and migration support
  * Improved JSON sanitization with cycle detection to prevent infinite recursion
  * Better payload processing with deduplication-aware formatting
  * Enhanced file save/load operations with format validation
### Changed
* **Test Suite Architecture Overhaul**
  * All **295 tests** now passing with **70% coverage** (improved from previous versions)
  * Comprehensive Kafka memory test infrastructure with robust import mocking
  * Enhanced test isolation and mocking strategies across all modules
  * Fixed orchestrator tests to handle graceful error management instead of raw exceptions
  * Updated start script tests for new environment variable handling
* **Agent Response Structure Enhancement**
  * `LocalLLMAgent` now returns structured responses with cost metrics and performance data
  * Improved agent result formatting with consistent metadata across all agent types
  * Enhanced error handling and retry mechanisms with detailed failure reporting
  * Better integration between cost calculation and existing metrics systems
* **Infrastructure & Configuration Management**
  * Enhanced environment variable handling for deployment flexibility
  * Improved Docker and service startup configurations
  * Better error handling and graceful degradation across all components
  * Enhanced logging and debugging capabilities for production deployments
### Fixed
* **Critical Test Infrastructure Issues**
  * Resolved all Kafka memory logger test failures with comprehensive import mocking
  * Fixed orchestrator error handling tests to match new graceful error management patterns
  * Updated start script tests for new backend parameter requirements and environment handling
  * Enhanced mock environments to prevent dependency conflicts during testing
* **Memory Management & Performance**
  * Fixed memory logger recursion errors when sanitizing Mock objects with circular references
  * Improved JSON serialization handling for complex nested objects and blob references
  * Enhanced cleanup procedures for Redis and Kafka connections during shutdown
  * Better resource management and garbage collection for long-running processes
* **Production Readiness & Reliability**
  * Eliminated misleading $0.00 cost placeholders that provided incorrect economic signals
  * Added robust cost validation and null cost handling for production pipeline enforcement
  * Improved error messages and debugging information across all system components
  * Enhanced configurability for different deployment environments and use cases
### Documentation
* **Comprehensive Configuration Guides**
  * Environment variable documentation for cost calculation, blob storage, and metrics tuning
  * Examples of cost analysis workflows and optimization strategies
  * Guidelines for production deployment with strict cost enforcement policies
  * Regional configuration examples and deployment best practices

## [0.6.1] · 2025-06-07
### Fixed
* **Critical Search Tool Bug**
  * Fixed DuckDuckGo search tool receiving raw template strings instead of formatted prompts
  * Search queries now properly resolve template variables (e.g., `{{ previous_outputs['agent_id'] }}`)
  * Orchestrator now renders prompts **before** agent execution instead of after
  * Search results now correctly match the intended search queries
* **Orchestrator Execution Flow**
  * Fixed incomplete `if` statement in parallel agent execution causing syntax errors
  * Added formatted prompts to payload data across all execution paths (RouterNode, ForkNode, JoinNode, normal agents)
  * Fixed `previous_outputs` update timing in parallel execution - agents now see only results from previously completed agents
  * Improved error handling for prompt template rendering with graceful fallbacks
* **Code Quality Improvements**
  * Refactored duplicated prompt handling code into reusable helper methods (`_render_agent_prompt`, `_add_prompt_to_payload`)
  * Fixed timezone-aware datetime usage for UTC timestamps (replaced deprecated `datetime.utcnow()`)
  * Enhanced payload data consistency across sequential and parallel execution paths
### Changed
* **Prompt Processing Architecture**
  * Template rendering now occurs before agent execution for immediate availability
  * Search tools prioritize `formatted_prompt` from orchestrator over raw prompt templates
  * Improved separation of concerns between execution-time and logging-time prompt handling

## [0.6.0] · 2025-06-07
### Added
* **Kafka Memory Backend Support**
  * Comprehensive `KafkaMemoryLogger` implementation with full feature parity to Redis backend
  * Support for hash operations, set operations, key-value storage, and event logging via Kafka
  * Factory function `create_memory_logger()` for dynamic backend selection via environment variables
  * Docker configuration and documentation for Kafka setup and integration
  * 21 comprehensive test cases covering initialization, logging, data operations, and error handling
* **Enhanced Resource Registry System**  
  * Complete test coverage (0% → 98%) for `ResourceRegistry` with 20 new test cases
  * Support for Redis, OpenAI, SentenceTransformer, and custom resource types
  * Comprehensive error handling and resource lifecycle management testing
  * Dynamic resource initialization with proper cleanup and connection management
* **Robust Test Infrastructure**
  * **295 total tests** passing with **73% overall coverage** (improved from 71%)
  * Fork Group Manager coverage improved from 51% → 99% with 32 comprehensive tests
  * Fixed critical recursion errors in memory logger JSON sanitization
  * Enhanced mock strategies for Kafka integration without requiring actual Kafka installation
  * Improved test isolation and reliability across different environments
### Changed
* **Dependency Management**
  * Made DuckDuckGo search import optional to resolve PyO3 compatibility issues
  * Enhanced error handling for missing optional dependencies (sentence-transformers, huggingface-hub)
  * Coverage calculation now excludes start scripts (start_kafka.py, start_redis.py) for cleaner metrics
* **Memory Logger Architecture**
  * Improved JSON sanitization with cycle detection to prevent infinite recursion
  * Enhanced logging error handling during system shutdown to prevent I/O operation errors
  * Better error messages and graceful degradation for missing dependencies
### Fixed
* **Test Suite Stability**
  * Resolved JoinNode test failures with proper mock `hget`/`hset` method implementations  
  * Fixed memory logger recursion errors when sanitizing Mock objects with circular references
  * Improved start script testing without problematic import dependencies
  * Enhanced fork/join node functionality with proper retry count handling
* **Logging and Error Handling**
  * Fixed logging system shutdown errors in RedisMemoryLogger and KafkaMemoryLogger
  * Improved error handling for resource cleanup during application termination
  * Better exception handling and error reporting across memory backend operations

---

## [0.5.9] · 2025-06-01
### Added
* **LocalLLMAgent** - New agent type for local LLM integration
  * Support for multiple local LLM providers: Ollama, LM Studio, OpenAI-compatible APIs
  * Dedicated `local_llm_agents.py` module for better separation from cloud agents
  * Template-based prompt handling with `{{ input }}` substitution
  * Configurable model endpoints, temperature, and provider selection
  * Full integration with OrKa agent registry and orchestrator
* **Comprehensive example workflows**
  * `comprehensive_research_analysis.yml` - Demonstrates all agent types and nodes
  * Research paper analysis workflow using hybrid local + cloud processing
  * Shows parallel processing, conditional routing, memory operations, and failover
* **Enhanced agent modularity**
  * Separated local LLM agents from OpenAI agents for cleaner architecture
  * Updated agent registry and orchestrator to support new agent type
  * Comprehensive test suite for LocalLLMAgent with multiple provider scenarios
### Changed
* Agent imports reorganized for better modularity and separation of concerns
* Example configurations updated to showcase hybrid local + cloud workflows
* Documentation expanded with local LLM integration patterns
### Fixed
* Improved error handling for local model connection failures
* Better template substitution and input validation for local agents

---

## [0.5.8] · 2025-05-25
### Added
* New `ValidationAndStructuringAgent` for validating and structuring answers into memory format
  * Supports custom memory object templates
  * Provides validation status and reasoning
  * Integrates with existing memory system
### Changed
* Enhanced LLM agent parameters:
  * Added support for model-specific parameters in YAML config
  * Improved temperature and model selection handling
  * Better error handling for model responses
### Fixed
* Documentation now properly hosted at orkacore.web.app/docs
* Fixed Sphinx documentation generation for new agent
* Improved test coverage for validation agent

---

## [0.5.7] · 2025-05-18
### Changed
* Consolidated test suite into domain-specific files for better organization and maintenance.
* Updated CI workflow to run domain-based tests for improved clarity and efficiency.
* Added deprecation markers to legacy test files while preserving test coverage.

---

## [0.5.6] · 2025-05-17
### Fixed
* LLM agent test suite now uses unified mocking ensuring reliability across local runs and GitHub Actions.
* CI workflow updated to set `PYTEST_RUNNING` early and avoid skipping coverage.
* Documentation and import paths adjusted for `LegacyBaseAgent`.

---

## [0.5.5] · 2025-05-10
### Changed
* Bumped version to **0.5.5** in *pyproject.toml* / *setup.py*.  
* Polished README (new badges, wording) and expanded docs.  
* Refactored CI scripts & Codecov wiring; test-badge now green. :contentReference[oaicite:0]{index=0}  

---

## [0.5.2] · 2025-05-10
### Added
* Initial **Codecov** integration & coverage upload workflow.  
* Extra unit-tests ⇒ higher overall coverage.  
### Changed
* Project metadata set to **0.5.2**. :contentReference[oaicite:1]{index=1}  

---

## [0.5.0] · 2025-05-10  
*(tag implied by version bump in later commits)*  
### Added
* **Service-node / Memory subsystem**  
  * `MemoryReaderNode`, `MemoryWriterNode`, `memory_logger.py`  
  * JSON-sanitising logger + Redis backing.  
  * Embedding utility (`utils/embedder.py`) for future RAG hooks.  
* >2 kLoC of tests covering the new nodes and logger.  
### Changed
* Orchestrator patched to wire per-node embeddings & scoped memory. :contentReference[oaicite:2]{index=2}  

---

## [0.3.7] · 2025-05-03
### Added
* Docker artefacts (`orka/docker/*`, root `docker-compose.yml`).  
* `orka_start.py` — one-shot CLI launcher for Redis + backend.  
### Changed
* README completely reorganised; clearer "PIP Installation" and YAML sample. :contentReference[oaicite:3]{index=3}  

---

## [0.3.64] · 2025-05-03
### Added
* Repo-wide branding refresh (new logo URL, website link).  
* Additional Codecov / Test badges.  
### Changed
* README tweaks, Dockerfile re-location, misc path fixes. :contentReference[oaicite:4]{index=4}  

---

## [0.3.6] · 2025-05-03
### Added
* **CLI `orka-start`** docs & helper text.  
* Bulk test suite (`test_orka_*`, fake-Redis) + coverage scripts.  
### Changed
* README: quick-start for full stack via Docker Compose. :contentReference[oaicite:5]{index=5}  

---

## [0.3.5] · 2025-05-02
### Added
* First **fork/join** logic polish – big diff in `join_node.py`.  
* Example YAML (`example.yml`) with agent definitions.  
### Changed
* `ORKA` LLM agent temperature default raised to 1.0. :contentReference[oaicite:6]{index=6}  

---

> **Note:** versions earlier than 0.3.5 are not tagged in the public repo; private `orca-core` work (0.4.x) is outside this history.

