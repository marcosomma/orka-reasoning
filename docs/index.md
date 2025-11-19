# OrKa Documentation Index

> **Last Updated:** 16 November 2025  
> **Version:** 0.9.6  
> **Status:** 🟢 Current

Welcome to the OrKa documentation hub. This index provides a comprehensive map of all documentation resources, their current status, and recommended reading paths.

---

## 📚 Table of Contents

- [Quick Links by Use Case](#-quick-links-by-use-case)
- [Documentation Sitemap](#-documentation-sitemap)
  - [Getting Started](#getting-started)
  - [Core Concepts](#core-concepts)
  - [Configuration](#configuration)
  - [Memory System](#memory-system)
  - [Agent Development](#agent-development)
  - [Advanced Topics](#advanced-topics)
  - [Testing & Quality](#testing--quality)
  - [Development & Operations](#development--operations)
  - [Project Status & History](#project-status--history)
  - [Tutorials & Examples](#tutorials--examples)
- [Documentation Consolidation](#-documentation-consolidation)
- [Documentation Roadmap](#-documentation-roadmap)
- [Documentation Conventions](#-documentation-conventions)

---

## 🎯 Quick Links by Use Case

**I want to...**
- **Get started quickly** → [quickstart.md](quickstart.md) → [getting-started.md](getting-started.md)
- **Use the visual editor** → [orka-ui.md](orka-ui.md) → [OrKa_UI_Getting_Started_With_Images.md](OrKa_UI_Getting_Started_With_Images.md)
- **Understand the architecture** → [architecture.md](architecture.md) → [COMPONENTS.md](COMPONENTS.md) → [VISUAL_ARCHITECTURE_GUIDE.md](VISUAL_ARCHITECTURE_GUIDE.md)
- **Configure a workflow** → [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md) → [yaml-configuration-guide.md](yaml-configuration-guide.md)
- **Use memory/RAG** → [MEMORY_SYSTEM_GUIDE.md](MEMORY_SYSTEM_GUIDE.md) → [memory-agents-guide.md](memory-agents-guide.md)
- **Build custom agents** → [agents.md](agents.md) → [extending-agents.md](extending-agents.md) → [agents-advanced.md](agents-advanced.md)
- **Use GraphScout routing** → [GRAPH_SCOUT_AGENT.md](GRAPH_SCOUT_AGENT.md) → [GRAPHSCOUT_EXECUTION_MODES.md](GRAPHSCOUT_EXECUTION_MODES.md)
- **Debug problems** → [DEBUGGING.md](DEBUGGING.md) → [troubleshooting.md](troubleshooting.md) → [faq.md](faq.md)
- **Run tests** → [TESTING.md](TESTING.md) → [TEST_COVERAGE_ENHANCEMENT_STRATEGY.md](TEST_COVERAGE_ENHANCEMENT_STRATEGY.md)
- **Deploy to production** → [runtime-modes.md](runtime-modes.md) → [observability.md](observability.md) → [security.md](security.md)

---

## 🗺️ Documentation Sitemap

### Getting Started
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [README.md](../README.md) | Project overview, installation, quick example | 🟢 Current | 2025-11 |
| [quickstart.md](quickstart.md) | 5-minute getting started guide | 🟢 Current | 2025-11 |
| [getting-started.md](getting-started.md) | Comprehensive introduction | 🟢 Current | 2025-11 |
| [orka-ui.md](orka-ui.md) | **Visual workflow builder guide** | 🆕 New | 2025-11-19 |
| [OrKa_UI_Getting_Started_With_Images.md](OrKa_UI_Getting_Started_With_Images.md) | Visual tutorial with screenshots | 🟢 Current | 2025-11 |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | CLI commands cheat sheet | 🟢 Current | 2025-11 |

### Core Concepts
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [architecture.md](architecture.md) | System architecture overview | 🟢 Current | 2025-11 |
| [COMPONENTS.md](COMPONENTS.md) | Detailed component breakdown | 🟢 Current | 2025-11 |
| [ONTOLOGY.md](ONTOLOGY.md) | Terminology and concepts | 🟢 Current | 2025-11 |
| [VISUAL_ARCHITECTURE_GUIDE.md](VISUAL_ARCHITECTURE_GUIDE.md) | Visual design system & iconography | 🆕 New | 2025-11-16 |
| [SCORING_ARCHITECTURE.md](SCORING_ARCHITECTURE.md) | Deterministic scoring system | 🟢 Current | 2025-11 |
| [BOOLEAN_SCORING_DESIGN.md](BOOLEAN_SCORING_DESIGN.md) | Boolean scoring implementation | 🟢 Current | 2025-11 |
| [BOOLEAN_SCORING_GUIDE.md](BOOLEAN_SCORING_GUIDE.md) | Boolean scoring usage guide | 🟢 Current | 2025-11 |

### Configuration
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md) | **Primary YAML guide** | 🟢 Primary | 2025-11 |
| [yaml-configuration-guide.md](yaml-configuration-guide.md) | Tutorial-style YAML guide | 🟡 Consolidate | 2025-11 |
| [orka.yaml-schema.md](orka.yaml-schema.md) | YAML schema reference | 🟡 Consolidate | 2025-11 |
| [CONFIGURATION.md](CONFIGURATION.md) | General configuration | 🟡 Consolidate | 2025-11 |
| [runtime-modes.md](runtime-modes.md) | Execution modes (sequential/parallel) | 🟢 Current | 2025-11 |

### Memory System
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [MEMORY_SYSTEM_GUIDE.md](MEMORY_SYSTEM_GUIDE.md) | Comprehensive memory system guide | 🟢 Current | 2025-11 |
| [memory-agents-guide.md](memory-agents-guide.md) | Memory agent usage | 🟢 Current | 2025-11 |
| [memory-presets.md](memory-presets.md) | Pre-configured memory patterns | 🟢 Current | 2025-11 |
| [MEMORY_BACKENDS.md](MEMORY_BACKENDS.md) | Redis/RAG backend details | 🟢 Current | 2025-11 |
| [README_BACKENDS.md](README_BACKENDS.md) | Backend configuration | 🟡 Consolidate | 2025-11 |

### Agent Development
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [agents.md](agents.md) | Agent fundamentals | 🟢 Current | 2025-11 |
| [agents-advanced.md](agents-advanced.md) | Advanced agent patterns | 🟢 Current | 2025-11 |
| [extending-agents.md](extending-agents.md) | Creating custom agents | 🟢 Current | 2025-11 |
| [AGENT_NODE_TOOL_INDEX.md](AGENT_NODE_TOOL_INDEX.md) | Agent/node/tool reference | 🟢 Current | 2025-11 |
| [AGENT_SCOPING.md](AGENT_SCOPING.md) | Agent isolation/scoping | 🟢 Current | 2025-11 |
| [GRAPH_SCOUT_AGENT.md](GRAPH_SCOUT_AGENT.md) | GraphScout intelligent routing | 🟢 Current | 2025-11 |
| [GRAPHSCOUT_EXECUTION_MODES.md](GRAPHSCOUT_EXECUTION_MODES.md) | GraphScout modes (fast/balanced/thorough) | 🟢 Current | 2025-11 |
| [LOCAL_LLM_COST_CALCULATION.md](LOCAL_LLM_COST_CALCULATION.md) | Cost estimation for local LLMs | 🟢 Current | 2025-11 |

### Advanced Topics
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [best-practices.md](best-practices.md) | Design patterns & recommendations | 🟢 Current | 2025-11 |
| [api-reference.md](api-reference.md) | Python API documentation | 🟢 Current | 2025-11 |
| [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) | Integration patterns | 🟢 Current | 2025-11 |
| [DEVELOPER_GUIDE_INTELLIGENT_QA_FLOW.md](DEVELOPER_GUIDE_INTELLIGENT_QA_FLOW.md) | QA workflow patterns | 🟢 Current | 2025-11 |
| [TEMPLATE_RENDERING_FIX.md](TEMPLATE_RENDERING_FIX.md) | Jinja2 template troubleshooting | 🟡 Archive | 2025-11 |

### Testing & Quality
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [TESTING.md](TESTING.md) | Testing strategy & guidelines | 🟢 Current | 2025-11 |
| [TEST_COVERAGE_ENHANCEMENT_STRATEGY.md](TEST_COVERAGE_ENHANCEMENT_STRATEGY.md) | Coverage improvement plan | 🟢 Current | 2025-11 |
| [TESTING_IMPROVEMENTS_ROADMAP.md](TESTING_IMPROVEMENTS_ROADMAP.md) | Testing roadmap | 🟢 Current | 2025-11 |
| [TEST_EXECUTION_LOG.md](TEST_EXECUTION_LOG.md) | Test run logs | 🟡 Operational | 2025-11 |

### Development & Operations
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [DEBUGGING.md](DEBUGGING.md) | Debugging techniques & tools | 🟢 Current | 2025-11 |
| [troubleshooting.md](troubleshooting.md) | Common issues & solutions | 🟢 Current | 2025-11 |
| [faq.md](faq.md) | Frequently asked questions | 🟢 Current | 2025-11 |
| [observability.md](observability.md) | Monitoring & logging | 🟢 Current | 2025-11 |
| [security.md](security.md) | Security considerations | 🟢 Current | 2025-11 |

### Project Status & History
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [CHANGELOG.MD](../CHANGELOG.MD) | Version history & release notes | 🟢 Current | 2025-11-16 |
| [GIT_TIMELINE_PROJECT_EVOLUTION.md](GIT_TIMELINE_PROJECT_EVOLUTION.md) | Project evolution timeline | 🟢 Current | 2025-11 |
| [PROJECT_EXCELLENCE_REVIEW.md](PROJECT_EXCELLENCE_REVIEW.md) | Quality assessment | 🟢 Current | 2025-11 |
| [ARCHIVE_2025_01_31.md](ARCHIVE_2025_01_31.md) | Historical archive | 📦 Archive | 2025-01 |

### Tutorials & Examples
| Document | Description | Status | Last Updated |
|----------|-------------|--------|--------------|
| [orka_rosetta_stone_article.md](orka_rosetta_stone_article.md) | OrKa vs other frameworks | 🟢 Current | 2025-11 |
| [OrKa_UI_Getting_Started_With_Images.md](OrKa_UI_Getting_Started_With_Images.md) | Visual UI walkthrough | 🟢 Current | 2025-11 |
| [../examples/](../examples/) | 50+ YAML workflow examples | 🟢 Current | 2025-11 |

---

## 📋 Documentation Consolidation

### High Priority: YAML Configuration Guides

**Problem:** 4 overlapping YAML configuration documents cause confusion.

**Recommendation:**
1. **Keep as primary:** `YAML_CONFIGURATION.md` (comprehensive, well-structured)
2. **Merge into primary:** 
   - `yaml-configuration-guide.md` → Extract tutorial sections, merge examples
   - `orka.yaml-schema.md` → Extract schema reference, add as appendix
3. **Deprecate/Archive:** `CONFIGURATION.md` (too generic, covered elsewhere)

**Action Plan:**
```yaml
Phase 1 (v0.9.7):
  - Add deprecation notices to yaml-configuration-guide.md and orka.yaml-schema.md
  - Enhance YAML_CONFIGURATION.md with merged content
  - Update all cross-references to point to YAML_CONFIGURATION.md

Phase 2 (v1.0):
  - Move deprecated files to docs/archive/
  - Add redirects in README
```

### Medium Priority: Backend Documentation

**Problem:** `MEMORY_BACKENDS.md` and `README_BACKENDS.md` overlap.

**Recommendation:**
- Merge `README_BACKENDS.md` content into `MEMORY_BACKENDS.md`
- Move Redis/backend setup to "Backend Configuration" section
- Archive `README_BACKENDS.md`

### Low Priority: Template Fixes

**Recommendation:**
- Move `TEMPLATE_RENDERING_FIX.md` to `docs/archive/troubleshooting/`
- Keep as historical reference, add "RESOLVED in v0.9.x" notice

---

## 🛣️ Documentation Roadmap

### ✅ Completed (v0.9.6)
- [x] Created VISUAL_ARCHITECTURE_GUIDE.md with comprehensive iconography
- [x] Updated CHANGELOG.MD with markdown formatting consistency
- [x] Enhanced GRAPH_SCOUT_AGENT.md with execution modes
- [x] Improved BOOLEAN_SCORING_GUIDE.md with examples
- [x] Created this INDEX.md documentation hub

### 🔄 In Progress (v0.9.7)
- [ ] Add "Last Updated" metadata to all documentation files
- [ ] Add cross-navigation links between related docs
- [ ] Consolidate 4 YAML configuration guides into single primary
- [ ] Create automated documentation status checker script
- [ ] Add MkDocs configuration for website generation

### 📋 Planned (v0.10.0)
- [ ] Interactive API documentation with examples
- [ ] Video tutorial series (YouTube/docs embedding)
- [ ] Architecture decision records (ADR) directory
- [ ] Performance benchmarking documentation
- [ ] Migration guides for version upgrades

### 🎯 Future (v1.0+)
- [ ] Multi-language documentation (i18n)
- [ ] Auto-generated API docs from docstrings (Sphinx)
- [ ] Versioned documentation (docs.orka.ai/v0.9, /v1.0, etc.)
- [ ] Contribution guide with doc writing standards
- [ ] Documentation analytics (most viewed, search queries)

---

## 📖 Documentation Conventions

### Status Indicators
- 🟢 **Current** - Up-to-date, actively maintained
- 🆕 **New** - Recently added (< 1 month)
- 🟡 **Needs Update** - Outdated content, scheduled for revision
- 🔴 **Deprecated** - No longer recommended, kept for reference
- 📦 **Archive** - Historical, no longer relevant to current version
- 🟣 **Experimental** - Unstable features, may change

### Document Structure Template
All major documentation files should follow:

```markdown
# Document Title

> **Last Updated:** YYYY-MM-DD  
> **Status:** 🟢/🟡/🔴/🆕  
> **Related:** [Link1](link1.md) | [Link2](link2.md)

## Overview
Brief description (2-3 sentences)

## Table of Contents
- [Section 1](#section-1)
- [Section 2](#section-2)

## Content Sections
...

---
← [Previous Doc](prev.md) | [Index](INDEX.md) | [Next Doc](next.md) →
```

### Cross-Reference Format
- **Internal links:** Use relative paths `[text](../path/to/doc.md)`
- **Section links:** Use anchors `[text](#section-heading)`
- **Code references:** Use backticks `` `code` ``
- **External links:** Use full URLs with context

### Maintenance Schedule
- **Weekly:** Update TEST_EXECUTION_LOG.md with test runs
- **Monthly:** Review "Last Updated" dates, update stale docs
- **Quarterly:** Full documentation audit (INDEX.md status column)
- **Per Release:** Update CHANGELOG.MD, version references, deprecations

---

## 🤝 Contributing to Documentation

### Quick Checklist
- [ ] Add metadata header (Last Updated, Status, Related)
- [ ] Follow markdown linting rules (markdownlint)
- [ ] Add cross-references to related docs
- [ ] Update INDEX.md if adding new doc
- [ ] Test all code examples
- [ ] Add entry to CHANGELOG.MD if significant

### Documentation Types
1. **Getting Started** - Assumes no prior knowledge, step-by-step
2. **Guides** - Task-oriented, practical examples
3. **Reference** - Comprehensive technical details
4. **Explanations** - Conceptual understanding, architecture

### Writing Style
- Use active voice ("Run the command" not "The command should be run")
- Code examples should be copy-pasteable
- Include expected output for commands
- Use warnings/notes callouts for important info:
  ```markdown
  > ⚠️ **Warning:** Critical information
  > 💡 **Tip:** Helpful suggestion
  > 📌 **Note:** Additional context
  ```

---

## 📞 Documentation Support

**Questions or Issues?**
- Open issue: [GitHub Issues](https://github.com/marcosomma/orka-core/issues)
- Discussion: [GitHub Discussions](https://github.com/marcosomma/orka-core/discussions)
- Email: [project contact]

**Found a Documentation Bug?**
Label issue with `documentation` tag and include:
- File path (e.g., `docs/agents.md`)
- Section/line number
- Description of issue (outdated, incorrect, unclear)

---

**Index Version:** 1.0.0  
**Generated:** 16 November 2025  
**Maintainer:** OrKa Documentation Team  

← [Back to README](../README.md)

Extending OrKa

- Add new agents under `orka/agents/` and register them in the agent registry.
- Write unit tests under `tests/unit/` and mock external dependencies (LLMs, Redis) for deterministic tests.

Observability and debugging

OrKa logs execution events and, where configured, persists traces to the memory backend. Use debug logging and the CLI monitoring commands to investigate runs. For production deployments, configure structured logging and monitor the memory backend health.

Performance notes

Benchmarks in `docs/benchmark/` show example measurements for specific environments. These are illustrative; if you care about latency or throughput, run benchmarks with your data, index configuration and hardware.

Where to read next

Start with [Getting Started](./getting-started.md) and the examples in the `examples/` folder. For details about agent types, memory configuration and advanced topics see the other pages in this `docs/` folder.
[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🧭 GraphScout Agent](./GRAPH_SCOUT_AGENT.md) | [🔍 Architecture](./architecture.md) | [🧩 Ontology](./ONTOLOGY.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa Documentation

Welcome to OrKa - the **Orchestrator Kit for Agentic Reasoning**. OrKa is a YAML-based framework for orchestrating LLM workflows with persistent memory storage and retrieval.

## 🚀 What's New in V0.9.3 - GraphScout Agent

- **🧭 GraphScout Agent** - Workflow graph traversal with multi-agent path execution based on LLM evaluation
- **🎯 Dynamic Path Discovery** - Runtime workflow analysis as alternative to static routing configuration
- **🧠 Memory Agent Ordering** - Positions memory readers before other agents and writers after
- **⚡ Multi-Agent Execution** - Execute ALL agents in shortlist sequentially, not just the first one
- **🔍 LLM-Based Evaluation** - Path selection using LLM-based confidence scoring

## 🚀 Previous Major Features - V0.9.2 Memory Presets

- **🧠 Memory Presets System** - Simplified memory configuration using preset templates based on memory duration patterns
- **🎯 Operation-Aware Configuration** - Different default parameters for read vs write operations
- **🔧 Unified Memory Agents** - Single `type: memory` replacing separate reader/writer types
- **🤖 Local LLM Integration** - Full Ollama support for running models locally
- **📚 Documentation Updates** - Reorganized examples with simplified preset-based configurations

## 🚀 Previous Major Features

### V0.7.5 - Loop Control
- **🔄 Loop Node** - Iterative workflow execution with configurable exit conditions
- **🧠 Multi-Agent Workflows** - Multiple agents collaborating on tasks with shared memory
- **🎯 Threshold-Based Execution** - Loop termination based on score thresholds

### V0.7.0 - RedisStack Integration
- **🚀 HNSW Vector Search** - RedisStack HNSW indexing for faster similarity search (benchmarked 100x faster than basic Redis)
- **⚡ Improved Search Latency** - Sub-millisecond search performance on indexed data
- **🏗️ Unified Backend** - All components now use RedisStack with fallback to basic Redis

## 🧠 Key Features

### Memory System with Presets
OrKa includes a Redis-based memory system with configurable retention policies:

- **🧠 Memory Presets**: 6 preset configurations with different retention durations (sensory, working, episodic, semantic, procedural, meta)
- **🎯 Simplified Configuration**: Single `memory_preset` parameter provides preconfigured defaults
- **⚡ Operation-Based Defaults**: Different default parameters for read vs write operations
- **🚀 HNSW Vector Indexing**: RedisStack HNSW provides faster vector similarity search (benchmarked 100x faster than basic Redis)
- **🔄 Configurable Expiration**: Time-based memory expiration with importance factor multipliers
- **📊 Preset Templates**: Preconfigured retention periods and importance rules per preset type
- **🔍 Semantic Search**: Vector embeddings for similarity-based retrieval
- **🖥️ CLI Monitoring**: Command-line tools for viewing memory state and metrics

### YAML-Based Configuration
Define workflows in YAML files instead of code:
- **📝 Declarative Format**: Specify agents and their connections in YAML
- **🔧 Modular Agents**: Composable agent types for different tasks
- **🌊 Conditional Routing**: Router agents for branching logic based on outputs
- **🔄 Fork/Join Patterns**: Parallel execution paths with result aggregation

### Execution Tracking
Workflows provide execution logs and metrics:
- **📋 Execution History**: Redis-based logging of agent interactions
- **🎭 Monitoring UI**: Optional web interface for workflow monitoring
- **📊 Metadata Storage**: Agent outputs and execution context stored in Redis

## 🚀 Quick Start

### 1. Install OrKa with Dependencies
```bash
# Install OrKa with all required dependencies
pip install orka-reasoning fastapi uvicorn

# Optional: Install extra features
pip install orka-reasoning[extra]
```

### 2. Start OrKa (Automatic RedisStack Setup)
**Prerequisites:** RedisStack via one of these methods:
- Docker (easiest - will be auto-configured)
- Native RedisStack installation (brew/apt/download)

```bash
# Set your OpenAI key (if using OpenAI models)
export OPENAI_API_KEY=your-key-here

# Start OrKa with automatic RedisStack detection
# Tries native first, then Docker, then shows install instructions
orka-start

# Alternative: Use Python module directly
python -m orka.orka_start
```

**What `orka-start` does:**
1. Checks for native RedisStack installation
2. Falls back to Docker if native not found
3. Provides installation instructions if neither available

### 3. Create Your First Workflow with Memory
```yaml
orchestrator:
  id: smart-assistant
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168
      importance_rules:
        user_correction: 3.0
        successful_answer: 2.0

agents:
  - id: memory_search
    type: memory-reader
    namespace: conversations
    params:
      enable_context_search: true
      context_weight: 0.4
      temporal_weight: 0.3
      similarity_threshold: 0.8
    prompt: "Find relevant conversation history for: {{ input }}"

  - id: response_generation
    type: openai-answer
    prompt: |
      History: {{ previous_outputs.memory_search }}
      Current: {{ input }}
      Generate a response using the conversation history.

  - id: memory_store
    type: memory-writer
    namespace: conversations
    params:
      vector: true
    prompt: "User: {{ input }} | Assistant: {{ previous_outputs.response_generation }}"
```

### 4. Run and Monitor Workflows
```bash
# Run your workflow
python -m orka.orka_cli smart-assistant.yml "Hello! Tell me about OrKa's memory system."

# Monitor memory state
python -m orka.orka_cli memory watch

# View statistics
python -m orka.orka_cli memory stats

# Optional: Run OrKa UI for web-based monitoring
docker pull marcosomma/orka-ui:latest
docker run -it -p 80:80 --name orka-ui marcosomma/orka-ui:latest
# Then open http://localhost in your browser
```

## 📚 Documentation Guide

### 🎯 Getting Started
- **[📘 Getting Started](./getting-started.md)** - Complete setup guide
- **[📝 YAML Configuration Guide](./yaml-configuration-guide.md)** - Agent configuration reference
- **[🧠 Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)** - Memory configuration and usage

### 🔧 Core Concepts
- **[🤖 Agent Types](./agents.md)** - All available agent types and their capabilities
- **[🔍 Architecture](./architecture.md)** - System design and architectural principles
- **[🧩 Ontology](./ONTOLOGY.md)** - Entities, identifiers, and relationships across OrKa
- **[⚙ Runtime Modes](./runtime-modes.md)** - Different execution strategies

### 🛠️ Advanced Topics
- **[🧪 Extending Agents](./extending-agents.md)** - Build custom agents and tools
- **[📊 Observability](./observability.md)** - Monitoring and debugging workflows
- **[🔐 Security](./security.md)** - Security considerations and best practices

### 📖 Reference
- **[📜 YAML Schema](./orka.yaml-schema.md)** - Complete YAML configuration schema
- **[❓ FAQ](./faq.md)** - Frequently asked questions and troubleshooting

## 🎯 Common Use Cases

### 1. Conversational Interface with Memory
Chatbots that retrieve and store conversation history:
```yaml
# Retrieves conversation history using vector search,
# classifies interaction type, generates responses based on context,
# and stores interactions with configurable expiration rules
```

### 2. Knowledge Base with Updates
Systems that search existing knowledge and add new information:
```yaml
# Searches existing knowledge with HNSW indexing, checks if content is recent,
# fetches new information via web search, validates facts using LLM,
# and updates knowledge base with new entries
```

### 3. Multi-Agent Workflows
Multiple agents working on related tasks with shared memory:
```yaml
# Research agents gather information, analysis agents process findings,
# synthesis agents create reports - all using shared Redis memory
```

### 4. Iterative Refinement
Workflows that repeat until output meets criteria:
```yaml
# Uses LoopNode to iteratively refine responses until quality threshold is met,
# extracts metrics from each iteration,
# stores iteration history in memory for tracking progress
```

### 5. Multi-Agent Deliberation
Multiple agents providing different perspectives on a topic:
```yaml
# Multiple agents (logical, empathetic, skeptical, creative) generate responses,
# moderator evaluates similarity between responses, process repeats until threshold reached,
# produces aggregated output combining different viewpoints
```

### 6. Workflow Validation
Systems that retry on failure with memory of past attempts:
```yaml
# Attempts task execution, validates results using validation agent,
# stores failures in memory, retries with adjustments based on past failures
```

## 🧠 Memory System Configuration

### Configurable Expiration Rules
```yaml
memory_config:
  decay:
    enabled: true
    importance_rules:
      critical_info: 3.0      # Multiply retention time by 3x
      user_feedback: 2.5      # Multiply retention time by 2.5x
      routine_query: 0.8      # Multiply retention time by 0.8x
```

### Context-Aware Search with HNSW
```yaml
memory_reader:
  params:
    enable_context_search: true    # Include conversation history in search
    context_weight: 0.4           # 40% weight for context matching
    temporal_weight: 0.3          # 30% weight for recency
    similarity_threshold: 0.8     # Minimum relevance score (HNSW-indexed)
```

### Monitoring Tools
```bash
# Command-line memory dashboard
python -m orka.orka_cli memory watch

# View memory statistics
python -m orka.orka_cli memory stats

# Clean up expired entries
python -m orka.orka_cli memory cleanup
```

## 🌟 Comparison to Alternatives

| Feature | OrKa V0.7.0 | LangChain | CrewAI | LlamaIndex |
|---------|-------------|-----------|--------|-------------|
| **Memory System** | ✅ RedisStack HNSW (benchmarked 100x faster) | ❌ Basic storage | ❌ Simple memory | ⚠️ RAG-focused |
| **Vector Search** | ✅ Sub-millisecond HNSW | ❌ Basic similarity | ❌ No vector search | ⚠️ Limited indexing |
| **Configuration** | ✅ YAML-based | ❌ Python code | ❌ Python code | ❌ Python code |
| **Execution Logging** | ✅ Redis-based logs | ⚠️ Limited | ⚠️ Basic | ⚠️ Limited |
| **Learning Curve** | ✅ Low (YAML) | ⚠️ Medium (Python) | ⚠️ Medium (Python) | ⚠️ Medium (Python) |
| **Memory Expiration** | ✅ Time-based with rules | ❌ Manual cleanup | ❌ No expiration | ❌ Manual cleanup |
| **Context Inclusion** | ✅ Multi-factor scoring | ❌ Basic retrieval | ❌ Simple memory | ⚠️ Vector-only |
| **Performance** | ✅ HNSW indexing | ⚠️ Varies by backend | ⚠️ Basic | ⚠️ Index-dependent |

## 📊 Performance Benchmarks

Performance measurements comparing basic Redis to RedisStack HNSW on a test dataset:

| Metric | Basic Redis | **RedisStack HNSW** | Measured Difference |
|--------|-------------|---------------------|-------------|
| **Vector Search** | 50-200ms | **0.5-5ms** | **~100x faster** |
| **Memory Usage** | 100% baseline | **40%** | **60% reduction** |
| **Throughput** | 1,000/sec | **50,000/sec** | **50x higher** |
| **Concurrent Searches** | 10-50 | **1,000+** | **20x more** |

*Note: Performance depends on dataset size, query complexity, and hardware. Your results may vary.*

## 🔧 Architecture Overview

OrKa uses a Redis-based architecture for workflow execution and memory:

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   YAML      │     │  Orchestrator   │     │   Agents    │
│ Definition  ├────►│  (Control Flow) ├────►│  (Execution)│
└─────────────┘     └────────┬────────┘     └──────┬──────┘
                             │                     │
                     ┌───────▼─────────────────────▼───────┐
                     │     RedisStack HNSW Memory          │
                     │  (Vector search with HNSW index)    │
                     └───────────────────────────────────┬─┘
                                                         │
                                                 ┌───────▼────────┐
                                                 │   OrKa UI      │
                                                 │  (Monitoring)  │
                                                 └────────────────┘
```

**Ready to get started?** See our [📘 Getting Started](./getting-started.md) guide!

---


---
← [None](..\README.md) | [📚 index](index.md) | [Quickstart](quickstart.md) →
