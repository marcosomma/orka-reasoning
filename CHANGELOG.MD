# OrKa-Reasoning – Un-official CHANGELOG  
*(derived from the public-repo commit history as of **2025-01-31**)*  

---
## [0.7.4] · 2025-01-31
### Fixed
* **🔧 Schema Management Dependencies Installation Issue**
  * **Critical Package Configuration Fix** - Fixed missing confluent-kafka dependencies preventing schema management features from working after pip installation
  * **Optional Dependencies Implementation** - Added `[schema]` optional dependencies group allowing users to install schema features with `pip install orka-reasoning[schema]`
  * **GitHub Actions Test Failures** - Resolved failing schema manager tests in CI/CD pipeline by installing required dependencies
  * **Installation Documentation** - Updated README.md, getting-started.md, and documentation to reflect new installation options
  * **Improved Error Messages** - Enhanced error messages in schema_manager.py to guide users to correct installation method
  * **Backward Compatibility** - Maintained full backward compatibility while adding optional schema management features

### Technical Details
* **Root Cause** - confluent-kafka dependencies were only in `orka/requirements.txt` but not in `setup.py` or `pyproject.toml`, causing installation failures
* **Solution Strategy** - Added schema management as optional dependencies that users can install when needed
* **Files Updated** - `setup.py`, `pyproject.toml`, `.github/workflows/test.yml`, documentation files, and schema_manager.py
* **Impact** - Users can now choose between basic installation (`pip install orka-reasoning`) and full schema support (`pip install orka-reasoning[schema]`)
* **Testing** - All 28 schema manager tests now pass, including the previously failing TestUtilityFunctions tests

---
## [0.7.3] · 2025-01-04
### Fixed
* **🔧 Memory Metadata Structure Preservation**
  * **Enhanced Memory Writer Node** - Fixed metadata structure handling to ensure YAML-defined metadata is properly preserved and rendered
  * **Improved Template Rendering** - Enhanced Jinja2 template rendering in metadata fields with better error handling and debugging
  * **Comprehensive Metadata Merging** - Fixed metadata merging from multiple sources (YAML config, context, guardian outputs, memory objects)
  * **Template Context Enhancement** - Improved template context with comprehensive data structure access and debugging capabilities
  * **Metadata Validation** - Added validation to ensure metadata structure is correctly saved and accessible for memory retrieval

### Technical Details
* **Root Cause** - Memory metadata structure was not being properly preserved when merging from different sources during memory writing
* **Solution Strategy** - Enhanced the `_merge_metadata()` and `_render_metadata_templates()` methods in MemoryWriterNode to properly handle YAML metadata structure
* **Impact** - Ensures that metadata defined in YAML configuration files is properly preserved and accessible for memory operations
* **Testing** - Enhanced debugging and logging to verify metadata structure preservation throughout the memory writing process

---
## [0.7.2] · 2025-01-31
### Fixed
* **🎨 TUI Package Distribution Issue**
  * **Missing CSS Files** - Fixed `textual_styles.tcss` file not being included in package distribution
  * **Package Configuration** - Updated `MANIFEST.in`, `setup.py`, and `pyproject.toml` to include TUI CSS files
  * **Files Updated** - Added `recursive-include orka *.tcss` to MANIFEST.in and `tui/*.tcss` to package_data
  * **Production Ready** - Resolves TUI styling issues when package is installed from distribution (pip install)

### Technical Details
* **Root Cause** - CSS file referenced in `textual_app.py` but not included in package distribution configuration
* **Solution Strategy** - Added tcss file inclusion to all package configuration files (MANIFEST.in, setup.py, pyproject.toml)
* **Impact** - Affects TUI visual styling and layout when running from installed package
* **Testing** - Package installation now includes all required TUI assets for proper styling

---
## [0.7.1] · 2025-01-31
### Fixed
* **🔧 Redis-py 5.x Compatibility Issue**
  * **Critical Import Fix** - Fixed `ModuleNotFoundError: No module named 'redis.commands.search.indexDefinition'` when using redis-py ≥5.0
  * **Forward Compatibility** - Added try/except import pattern to support both redis-py 4.x (camelCase) and 5.x (snake_case) import paths
  * **Files Updated** - Fixed imports in `orka/utils/bootstrap_memory_index.py` and `test/unit/test_bootstrap_memory_index_comprehensive.py`
  * **Zero Breaking Changes** - Solution maintains backward compatibility with redis-py 4.x while supporting the latest 5.x versions
  * **Production Ready** - Resolves bootstrap memory index initialization failures in environments using redis-py ≥5.0

### Technical Details
* **Root Cause** - redis-py 5.0 renamed RediSearch helper modules from camelCase to snake_case (`indexDefinition` → `index_definition`)
* **Solution Strategy** - Implemented graceful import fallback pattern that tries camelCase first, then falls back to snake_case
* **Impact** - Affects RedisStack HNSW vector search initialization which requires IndexDefinition and IndexType imports
* **Testing** - All existing tests pass with both redis-py 4.x and 5.x versions

---
## [0.7.0] · 2025-01-31
### Added
* **🚀 RedisStack HNSW Vector Search Revolution - Production Ready**
  * **100x Faster Vector Searches** - RedisStack with HNSW (Hierarchical Navigable Small World) indexing now default across all components
  * **Sub-millisecond Search Latency** - O(log n) complexity replacing O(n) legacy FLAT indexing for massive datasets
  * **50,000+ Memories/Second** - Enterprise-grade write performance with sustained high-throughput operations
  * **Intelligent Vector Indexing** - Automatic HNSW index creation with optimized M=16, ef_construction=200 parameters
  * **Advanced Hybrid Search** - Combined vector similarity + metadata filtering with namespace, category, and importance scoring
  * **Enhanced Bootstrap Memory Index** - `ensure_enhanced_memory_index()` with comprehensive HNSW configuration and legacy fallback
  * **Production-Ready Performance Metrics** - Real-time HNSW search statistics, latency tracking, and index health monitoring

* **🏗️ Unified RedisStack Architecture - System-Wide Integration**
  * **RedisStack as Default Backend** - All components (orchestrator, memory logger factory, CLI, start scripts) now default to RedisStack
  * **Intelligent Graceful Fallback** - Automatic degradation to basic Redis when RedisStack modules unavailable
  * **Kafka Hybrid Enhancement** - Kafka backend now uses RedisStack for memory operations with full HNSW capabilities
  * **Memory Nodes Integration** - Memory reader/writer nodes fully integrated with memory logger system instead of direct Redis calls
  * **Consistent Field Naming** - Standardized `orka_*` prefixed fields across all backends with legacy compatibility maintained
  * **Enhanced Memory Logger Factory** - `create_memory_logger()` with RedisStack as primary option and comprehensive error handling

* **⚡ Advanced Memory Management & TTL System**
  * **Enhanced Index-Aware Cleanup** - Hybrid expiration detection combining TTL-based and field-based methods
  * **Batch Processing Operations** - 100-key batch deletion with automatic HNSW index maintenance and optimization
  * **Comprehensive Decay Metadata** - Enhanced memory entries with `orka_expire_time`, `orka_created_time`, `orka_importance_score`
  * **Automatic Index Optimization** - Intelligent index rebuilding triggered for significant cleanup operations (>10% threshold)
  * **Advanced Cleanup Metrics** - Detailed statistics including cleanup type, performance metrics, and error collection
  * **Field Standardization** - Dual field storage system supporting both `orka_*` standardized and legacy field names

* **🖥️ Professional CLI Dashboard & Monitoring**
  * **Enhanced Memory Watch** - Real-time RedisStack performance dashboard with HNSW metrics, search counts, and latency tracking
  * **Backend-Specific Metrics** - RedisStack performance indicators, hybrid search statistics, and index health status
  * **Advanced Configuration Testing** - Comprehensive RedisStack feature validation including HNSW index availability
  * **Professional UI Integration** - Rich terminal interface with live updates, performance visualization, and adaptive layouts
  * **Namespace Distribution Analysis** - Multi-tenant memory usage tracking and Redis server information display

* **🔧 Comprehensive Migration & Development Tools**
  * **Complete Migration Script** - `scripts/migrate_to_redisstack.py` with dry-run analysis, batch processing, and rollback capabilities
  * **Data Integrity Validation** - Migration verification with comprehensive statistics and integrity checking
  * **Development Mode Support** - `start_redis_only.py` with force basic Redis flag (`ORKA_FORCE_BASIC_REDIS=true`)
  * **Enhanced Error Handling** - Comprehensive error collection and reporting across all migration operations

### Changed
* **🔄 Architecture Transformation - RedisStack First**
  * **Default Backend Migration** - System-wide change from `"redis"` to `"redisstack"` as default across all entry points
  * **Orchestrator Enhancement** - `orka/orchestrator/base.py` updated with RedisStack defaults and HNSW configuration
  * **Start Script Modernization** - `orka/orka_start.py` and all entry points now use RedisStack with intelligent fallback
  * **Memory Node Refactoring** - Eliminated direct Redis operations in favor of unified memory logger system architecture
  * **Enhanced Kafka Integration** - Kafka backend now leverages RedisStack for memory operations instead of basic Redis streams

* **📈 Performance Architecture Optimization**
  * **Vector Search Complexity** - Reduced from O(n) to O(log n) through HNSW indexing implementation
  * **Memory Utilization** - 60% reduction in memory overhead through optimized indexing and field standardization
  * **Concurrent Operations** - Support for 1000+ concurrent search operations with RedisStack clustering ready
  * **Cleanup Efficiency** - 60% reduction in cleanup operation time through batch processing and index awareness

* **🛠️ Enhanced Developer Experience**
  * **Unified API Interface** - Consistent behavior across all memory operations regardless of backend
  * **Improved Error Messages** - Enhanced error handling with comprehensive logging and graceful degradation
  * **Simplified Configuration** - Automatic RedisStack configuration with sensible defaults and environment variable support
  * **Enhanced Documentation** - Comprehensive migration guides and production deployment recommendations

### Fixed
* **🔧 Critical Architecture Consistency Issues**
  * **Backend Fragmentation** - Resolved inconsistent backend usage across components (CLI used RedisStack while core used basic Redis)
  * **Memory Node Integration** - Fixed memory writer/reader nodes bypassing memory logger system with direct Redis operations
  * **Field Naming Inconsistencies** - Standardized field naming conventions across all backends while maintaining legacy compatibility
  * **Kafka Backend Limitations** - Enhanced Kafka backend to use RedisStack for memory operations instead of basic Redis streams

* **⚡ Performance & Reliability Improvements**
  * **Vector Search Performance** - Eliminated 100x performance gap between development and production through HNSW adoption
  * **Index Maintenance** - Fixed index corruption issues during cleanup operations with proper HNSW maintenance
  * **Memory Leak Prevention** - Enhanced TTL and cleanup systems preventing memory accumulation in long-running processes
  * **Graceful Degradation** - Improved fallback handling when RedisStack dependencies unavailable

* **🖥️ CLI & User Experience Enhancements**
  * **Memory Watch Accuracy** - Fixed RedisStack-specific metrics display and real-time performance monitoring
  * **Configuration Validation** - Enhanced backend feature detection and validation with clear error messaging
  * **Cross-Platform Compatibility** - Improved Windows, macOS, and Linux support with fallback modes for terminal limitations

### Technical Details
* **HNSW Implementation** - Advanced vector indexing with configurable parameters (M=16 connectivity, ef_construction=200 build accuracy)
* **Hybrid Backend Architecture** - Event streaming via Kafka, memory operations via RedisStack HNSW for optimal performance
* **Zero-Breaking Migration** - Complete backward compatibility maintained while providing enterprise-grade performance upgrades
* **Production Readiness** - High availability through RedisStack clustering, comprehensive monitoring, and performance tracking
* **Benchmarking Results** - 100x search latency improvement (50-200ms → 0.5-5ms), 50x write throughput increase (1,000/sec → 50,000/sec)
* **Migration Path** - Seamless upgrade path with dry-run analysis, validation tools, and rollback capabilities for existing deployments

### Migration Notes
* **For Existing Users** - No action required; system automatically attempts RedisStack with graceful fallback to Redis
* **For Production Deployments** - Install RedisStack for optimal performance; existing Redis configurations continue to work
* **Environment Configuration** - Optional `ORKA_MEMORY_BACKEND=redisstack` and `ORKA_FORCE_BASIC_REDIS=true` for explicit control
* **Performance Benefits** - Immediate 100x search performance improvement upon RedisStack adoption with zero code changes

---
## [0.6.6] · 2025-01-30
### Added
* **Kafka Hybrid Backend Implementation**
  * **Streamlined Architecture** - Kafka now automatically uses Redis for memory operations while handling event streaming
  * **Hybrid Memory Logger** - New KafkaMemoryLogger that intelligently routes memory operations to Redis while streaming events to Kafka
  * **Simplified Command Interface** - `start_kafka` command now automatically configures both Kafka and Redis backends without manual dual setup
  * **Enhanced Docker Integration** - Updated docker-compose.yml and startup scripts for seamless hybrid backend deployment
  * **Comprehensive Test Coverage** - New test files for hybrid backend validation and comprehensive component testing:
    * `test_kafka_hybrid_backend.py` - Complete hybrid backend functionality testing
    * `test_failover_node_comprehensive.py` - Enhanced failover node testing
    * `test_orka_cli_comprehensive.py` - Extended CLI functionality testing  
    * `test_redis_logger_comprehensive.py` - Comprehensive Redis logger testing
### Changed
* **Memory Backend Architecture**
  * **Unified Backend Strategy** - Eliminated confusion between dual backend and hybrid backend approaches
  * **Automatic Backend Selection** - Kafka startup now automatically enables hybrid mode without additional configuration
  * **Enhanced Memory Logger Factory** - Improved backend selection logic with better error handling and validation
  * **Docker Configuration Updates** - Modified startup scripts (start-kafka.bat, start-kafka.sh) for hybrid backend support
* **Test Infrastructure Improvements**
  * **Enhanced FakeRedisClient** - Improved mock Redis client with better method compatibility and error handling
  * **Fixed Test Suite Compatibility** - Resolved all failing tests after hybrid backend implementation
  * **Improved Test Isolation** - Better test separation and cleanup procedures for hybrid backend scenarios
  * **Enhanced Coverage Reporting** - Updated coverage configuration and reporting for new test files
### Fixed
* **Critical Backend Integration Issues**
  * **Kafka Memory Logger Compatibility** - Fixed missing methods and improper method calls in KafkaMemoryLogger
  * **Redis Integration** - Resolved byte/string encoding issues in FakeRedisClient for test compatibility
  * **Test Suite Stability** - Fixed 12 failing tests related to hybrid backend changes, ensuring 100% test pass rate
  * **Import Path Resolution** - Corrected import paths and method references across test files
* **Infrastructure and Configuration**
  * **Docker Startup Issues** - Fixed startup script compatibility across Windows and Unix platforms
  * **Memory Logger Factory** - Resolved backend selection logic and error handling edge cases
  * **Failover Node Stability** - Enhanced failover node error handling and recovery mechanisms
  * **CLI Command Integration** - Fixed OrKa CLI compatibility with hybrid backend architecture
### Technical Details
* **Hybrid Backend Implementation** - Seamless integration of Kafka event streaming with Redis memory operations
* **Zero-Impact Migration** - Existing workflows continue to function without modification while gaining Kafka streaming capabilities
* **Enhanced Error Handling** - Improved error reporting and recovery mechanisms across all backend operations
* **Performance Optimization** - Optimized memory operations routing and event streaming for better throughput
* **Cross-Platform Support** - Enhanced Windows and Unix compatibility for Docker and startup scripts
* **Comprehensive Testing** - Extended test coverage to 639+ tests with focus on hybrid backend scenarios

## [0.6.5] · 2025-01-29
### Added
* **Memory Decay System - Intelligent Memory Management**
  * **Automatic Memory Classification** - Smart classification of memory entries as short-term or long-term based on importance and event type
  * **Agent-Level Decay Configuration** - Per-agent decay settings that override global configuration for fine-grained control
  * **Configurable Retention Policies** - Separate retention periods for short-term and long-term memories with hour-based precision
  * **Importance Scoring Algorithm** - Dynamic importance calculation based on event types, agent types, and payload content
  * **Background Cleanup Scheduler** - Automatic cleanup of expired memories with configurable check intervals
  * **Memory Type Rules Engine** - Configurable rules for classifying events as long-term or short-term based on event types
  * **Decay Metadata Tracking** - Comprehensive metadata including importance scores, memory types, creation time, and expiration time
* **Enhanced Memory Reader System - Advanced Context-Aware Search**
  * **Context-Enhanced Search** - Memory reader now uses conversation history and previous outputs for more relevant memory retrieval
  * **Hybrid Scoring Algorithm** - Combines semantic similarity, keyword matching, context overlap, and temporal decay for optimal relevance ranking
  * **Enhanced Query Variations** - Intelligent generation of query variations using entity extraction and context keywords for broader search coverage
  * **Temporal Ranking** - Time-based scoring that prioritizes recent memories while maintaining relevance to older important memories
  * **Advanced Filtering** - Multi-criteria filtering with configurable thresholds for semantic similarity, keyword matching, and context relevance
  * **Deterministic Search Results** - Consistent and reproducible search results with proper handling of edge cases and timestamp variations
  * **Backward Compatibility** - Enhanced features are opt-in with full compatibility for existing memory reader configurations
* **Enhanced CLI Memory Management Interface**
  * **Real-time Memory Monitoring** - `orka memory watch` command with professional dashboard using Rich library
  * **Memory Statistics** - `orka memory stats` command showing detailed memory usage and decay configuration
  * **Manual Cleanup** - `orka memory cleanup` command for on-demand expired memory removal
  * **Configuration Display** - `orka memory configure` command showing current decay settings and environment variables
  * **Adaptive Layout** - Compact mode and dynamic sizing for different workflow complexities
  * **Color-coded Memory Types** - Visual distinction between short-term (🔥), long-term (💾), and unknown (❓) memories
* **Advanced Memory Configuration Options**
  * **Global Decay Configuration** - Orchestrator-level settings for default retention periods and importance rules
  * **Agent-Specific Overrides** - Individual agent decay settings that merge with global configuration
  * **Environment Variable Support** - Full configuration via environment variables for deployment flexibility
  * **Memory Type Forcing** - `default_long_term` setting to force agent memories into specific retention categories
  * **Flexible Time Configuration** - Support for fractional hours (e.g., 0.025 hours = 1.5 minutes) for testing and fine-tuning
### Changed
* **Memory Logger Architecture Enhancement**
  * **Decay-Aware Logging** - All memory loggers now support decay metadata and agent-specific configuration
  * **Deep Configuration Merging** - Intelligent merging of global and agent-level decay settings
  * **Enabled by Default** - Memory decay now enabled by default for better memory management
  * **Backward Compatibility** - Existing configurations continue to work without modification
* **Memory Reader Node Improvements**
  * **Enhanced Search Capabilities** - Memory reader now supports context-aware search with conversation history integration
  * **Improved Relevance Scoring** - Advanced hybrid scoring combining multiple relevance factors for better memory retrieval
  * **Configurable Search Parameters** - New configuration options for context weight, temporal weight, and search thresholds
  * **Performance Optimization** - More efficient memory scanning and relevance calculation for faster search results
* **Agent Factory Integration**
  * **Automatic Decay Injection** - Agent factory automatically extracts and injects decay configuration into memory nodes
  * **Memory Logger Passing** - Memory writer nodes now receive memory logger instances for decay-aware storage
  * **Configuration Validation** - Enhanced validation of decay configuration parameters
### Fixed
* **Memory Writer Node Integration**
  * **Proper Decay Application** - Memory writer nodes now use memory logger for decay-aware storage instead of direct Redis writes
  * **Agent-Level Configuration Support** - Fixed agent-specific decay settings not being applied to memory entries
  * **Memory Type Classification** - Corrected memory type classification to respect agent-level `default_long_term` settings
* **Memory Reader Search Accuracy**
  * **Query Variation Generation** - Fixed entity extraction and punctuation handling for more accurate query variations
  * **Namespace Consistency** - Resolved namespace mismatch issues between memory storage and retrieval
  * **Temporal Scoring Precision** - Fixed timestamp conversion thresholds for accurate temporal decay calculations
  * **Context Integration** - Improved context keyword extraction and deterministic ordering for consistent search results
* **Statistics Accuracy**
  * **Active Entry Counting** - Memory statistics now correctly count only active (non-expired) entries
  * **Expired Entry Tracking** - Separate tracking of expired entries without inflating active counts
  * **Memory Type Distribution** - Accurate distribution counts for short-term, long-term, and unknown memory types
### Technical Details
* **Decay Algorithm Implementation** - Sophisticated importance scoring with configurable boost factors for different event and agent types
* **Enhanced Memory Search Algorithm** - Multi-factor relevance scoring with semantic, keyword, context, and temporal components
* **Thread-Safe Background Processing** - Daemon thread scheduler for automatic cleanup with proper shutdown handling
* **Rich UI Integration** - Professional terminal interface with live updates, progress bars, and adaptive layouts
* **Cross-Platform Compatibility** - Full Windows, macOS, and Linux support with fallback modes for terminal limitations
* **Comprehensive Testing** - Extensive test coverage for decay functionality, enhanced memory reader, CLI commands, and edge cases
* **Performance Optimization** - Efficient memory scanning and cleanup with minimal impact on orchestration performance

## [0.6.4] · 2025-01-28
### Changed
* **Major Architectural Refactoring - Monolithic File Decomposition**
  * **Memory Logger Modularization** - Split `memory_logger.py` from 1,813 lines into focused components:
    * `base_logger.py` (273 lines) - BaseMemoryLogger abstract class with core interface
    * `serialization.py` (160 lines) - JSON sanitization and memory processing utilities
    * `file_operations.py` (180 lines) - Save/load functionality with file I/O operations
    * `redis_logger.py` (420 lines) - Complete RedisMemoryLogger implementation
    * `__init__.py` (35 lines) - Package initialization with proper component imports
    * Updated `memory_logger.py` (218 lines) - Factory function and backward compatibility layer
    * **88% code reduction** (1,813 → 218 lines) while maintaining 100% API compatibility
  * **Orchestrator Modularization** - Split `orchestrator.py` from 1,345 lines into specialized components:
    * `base.py` (90 lines) - OrchestratorBase class with initialization and configuration
    * `agent_factory.py` (180 lines) - AgentFactory with AGENT_TYPES registry and agent initialization
    * `prompt_rendering.py` (70 lines) - PromptRenderer with Jinja2 template processing
    * `error_handling.py` (180 lines) - ErrorHandler with comprehensive error tracking and reporting
    * `metrics.py` (220 lines) - MetricsCollector with LLM metrics and runtime environment detection
    * `execution_engine.py` (120 lines) - ExecutionEngine with main execution loop and agent coordination
    * `__init__.py` - Package initialization with component imports
    * New `Orchestrator` class using multiple inheritance composition pattern
    * **96% code reduction** (1,345 → 60 lines) while preserving identical public API
* **Architecture Improvements**
  * **Mixin Pattern Implementation** - Used multiple inheritance to compose functionality from specialized components
  * **Zero-Impact Refactoring** - All extracted code moved exactly as-is with no behavioral changes
  * **Enhanced Maintainability** - Created 12 focused, single-responsibility modules from 2 monolithic files
  * **Method Resolution Order Preservation** - Maintained identical method resolution to ensure unchanged behavior
### Added
* **Modular Package Structure**
  * New `orka/memory_logger/` package with 6 specialized modules
  * New `orka/orchestrator/` package with 7 specialized modules  
  * Comprehensive `__init__.py` files ensuring proper component exposure
  * Factory functions and composition classes for seamless integration
### Fixed
* **Code Organization & Technical Debt**
  * **Massive Code Reduction** - Eliminated 2,740 lines of monolithic code (92% overall reduction)
  * **Import Compatibility** - All existing imports continue to work without modification
  * **API Preservation** - Every public method remains accessible in identical locations
  * **Test Compatibility** - All existing tests pass without changes
  * **Backward Compatibility** - 100% compatibility maintained for all existing code using these components
### Technical Details
* **Phase 1: Memory Logger** - Successfully decomposed complex logging system into maintainable components
* **Phase 2: Orchestrator** - Transformed complex orchestration logic into specialized, testable modules
* **Composition Strategy** - Used multiple inheritance composition to maintain API while improving internal structure
* **Zero Regression Policy** - Rigorous testing ensured no functionality changes during refactoring process
* **Future-Proof Architecture** - New modular structure enables easier maintenance, testing, and feature development

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
  * Coverage calculation now excludes start scripts (start_kafka.py, start_redis_only.py) for cleaner metrics
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

