# OrKa Documentation Index

> **Last Updated:** 29 November 2025  
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
| [TEMPLATE_FILTERS.md](TEMPLATE_FILTERS.md) | Custom Jinja2 filters & functions | 🟢 Current | 2025-11 |
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
- [x] Created this index.md documentation hub

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
← [None](..\README.md) | [📚 INDEX](index.md) | [Quickstart](quickstart.md) →
