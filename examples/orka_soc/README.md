## Cognitive Society Workflow (Local, Optimized)

This folder contains an optimized "Cognitive Society" workflow for local LLMs. It
coordinates multiple reasoning personas, iteratively refines positions, and converges
to an agreement with memory support.

- `cognitive_society_with_memory_local_optimal-gpt-oss-20b.yml`

> Note: earlier `deepseek-8b` / `deepseek-32b` variants were removed; this folder now
> ships the single LM Studio + `openai/gpt-oss-20b` configuration.

### Goals
- Multi-agent debate with distinct roles (progressive, conservative, realist, purist)
- Iterative refinement loop with scoring and early stopping
- Agreement finding + final synthesis
- RedisStack-based short-term memory for debate continuity

### Prerequisites
- RedisStack running (`orka-start` is recommended)
- An OpenAI-compatible local LLM endpoint serving `openai/gpt-oss-20b`
  (the workflow uses `provider: lm_studio`, `model_url: http://localhost:1234`)

### Common Structure
- Orchestrator: sequential strategy with a top-level loop node and final synthesis
- Loop internal workflow:
  - shared_memory_reader → opening_positions (fork) → join
  - agreement_finder → collaborative_refinement (fork) → join
  - synthesis_attempt → agreement_moderator → shared_memory_writer
- Loop continues until the agreement score meets the threshold
- After the loop: meta_debate_reflection → final_synthesis_processor

### Scoring
- Primary: boolean `loop_convergence` scoring via the `loop_validator` + the
  `agreement_moderator` high-priority agent.
- Fallback: embedding-agreement across the perspective agents, enabled explicitly via
  `score_extraction_config.agreement_fallback: true` (the previous agent-name
  auto-detection has been removed).

### Memory
- Namespace: `society_memory`
- Short-term, vector-enabled storage for recent debate context
- Writer logs loop rounds, agreement summaries, and scores

### How to Run

```
ORKA_TIMEOUT_SECONDS=600 orka run \
  examples/orka_soc/cognitive_society_with_memory_local_optimal-gpt-oss-20b.yml \
  "What is the role of nuclear energy in a decarbonized grid?"
```

### Tuning Tips
- Increase `score_threshold` for stricter convergence
- Adjust `max_loops` for longer/shorter deliberation
- Use `max_length_per_category` in `cognitive_extraction` to control token use
- Raise/Lower `similarity_threshold` in `shared_memory_reader` to change recall breadth

### Troubleshooting
- If no agreement is reached, lower `score_threshold`
- Verify the LLM endpoint (`model_url`) is serving the model
- Ensure RedisStack index is healthy (`orka memory watch`) and vector search is enabled
- gpt-oss-20b is large; if agents time out, raise `ORKA_TIMEOUT_SECONDS`
