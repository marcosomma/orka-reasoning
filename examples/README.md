# OrKa Examples Catalog

This folder contains curated workflow examples demonstrating OrKa's core patterns: fork/join, routing, validation, memory operations, external tools, loops, and local LLM orchestration.

## How to run
- Start backend: `orka-start`
- Run any example:
  - `orka run examples/<workflow>.yml`*`"your input"`*

Note: Private sets (folders prefixed with PRIVATE_) are excluded from this catalog.

---

## 🧭 GraphScout Agent Examples (NEW in v0.9.3)

### graph_scout_basic.yml
- **Purpose**: Demonstrate basic GraphScout intelligent routing with automatic path discovery
- **Pattern**: GraphScout → dynamic agent selection → execution
- **Highlights**: 
  - Automatic path discovery and evaluation
  - Budget and safety controls
  - Intelligent decision making (commit_next/shortlist/no_path)
  - Works with search_agent, analyzer, response_builder

### graph_scout_memory_aware.yml  
- **Purpose**: Advanced GraphScout with memory-aware routing and intelligent agent positioning
- **Pattern**: GraphScout → memory readers (first) → processors → memory writers (last) → response builder
- **Highlights**:
  - Memory-aware routing logic (readers first, writers last)
  - Multi-agent sequential execution
  - Semantic memory integration with knowledge base
  - Comprehensive analysis pipeline with memory persistence

**🚀 Try GraphScout:**
```bash
# Basic intelligent routing
orka run examples/graph_scout_basic.yml "What are the latest developments in quantum computing?"

# Memory-aware intelligent routing  
orka run examples/graph_scout_memory_aware.yml "Explain machine learning algorithms"
```

---

## temporal_change_search_synthesis.yml
- Purpose: detect a pivotal date, generate before/after queries, search both, and synthesize a timeline.
- Pattern: fork → search → join → synthesize.
- Highlights:
  - detect_change → date (DD/MM/YYYY)
  - generate_before_query / generate_after_query
  - search_before / search_after (DuckDuckGo)
  - synthesize_timeline_answer → final summary

## memory_validation_routing_and_write.yml
- Purpose: retrieval-first flow with validation-based routing, then write-back to memory.
- Pattern: memory read → validation (binary) → router → (answer-from-memory | search→answer) → memory write.
- Highlights: decay-aware memory read, sufficiency validator, short-term write with metadata.

## memory_read_fork_join_router.yml
- Purpose: read memories, process in parallel branches, merge, then route.
- Pattern: memory read → fork processors → join → router.
- Highlights: demonstrates multi-branch enrichment before decisions.

## person_routing_with_search.yml
- Purpose: detect if input relates to a person; on true, extract name and expand with search; else answer generically.
- Pattern: binary decision → true-path enrichment (name → search → narrative) | false-path answer.
- Highlights: openai-binary_6 + router_7 → openai-answer_10 → duckduckgo_8 → openai-answer_9.

## cognitive_society_minimal_loop.yml
- Purpose: minimal multi-agent society with role agents and agreement/quality loop.
- Pattern: loop → roles → agreement score → stop at threshold.
- Highlights: loop metadata, scoring strategies, convergence.

## failover_search_and_validate.yml
- Purpose: resilient answering using failover tree of agents.
- Pattern: failover node → alternative strategies → eventual success.
- Highlights: production-oriented fallback behavior.

## conditional_search_fork_join.yaml
- Purpose: run parallel search/enrichment branches and merge results.
- Pattern: fork (multiple branches) → join → next steps.
- Highlights: joined_results() helper for downstream templating.

## multi_model_local_llm_evaluation.yml
- Purpose: compare local LLMs/params for cost/latency/quality.
- Pattern: multiple local LLM calls → metrics capture → comparative synthesis.
- Highlights: local inference focus.

## cognitive_loop_scoring_example.yml
- Purpose: iterative refinement with loop scoring until threshold.
- Pattern: loop node → sub-workflow per iteration → scoring strategies.
- Highlights: regex/key/agent-based scoring and embedding fallback.

## orka_framework_qa.yml
- Purpose: simple end-to-end Q&A over prompts/docs.
- Pattern: prompt → answer (optionally write memory if configured).
- Use: quick smoke tests and demos.

## routed_binary_memory_writer.yml
- Purpose: use binary decisions to route to different memory writers.
- Pattern: predicate → router → writer(s).
- Highlights: structured metadata, TTL usage for categories.

## validation_structuring_memory_pipeline.yml
- Purpose: validate and structure outputs into a consistent schema before persisting.
- Pattern: answer → validation/structuring → memory write (schema-aware).
- Use: normalized artifacts for downstream consumption.

## memory_types_short_long_test.yml
- Purpose: observe TTL/decay across short- vs long-term entries.
- Pattern: write with different types/TTLs → observe expiry/retention.
- Use: validate decay configuration and cleanup.

---

## Template helper functions
- get_input(): safe access to user input.
- joined_results(): merged outputs from fork/join.
- get_agent_response('<agent_id>'): convenient access to prior responses.
- safe_get(obj, key, default=''): guard against missing keys.

## Tips
- Keep the intended final node as the last OpenAI/Local LLM agent in the sequence.
- Routers enqueue next agents; they do not produce user-facing output.
- Prefer helper functions in prompts to avoid unresolved variables.
- Ensure Redis/RedisStack backend and HNSW index are healthy for memory examples.