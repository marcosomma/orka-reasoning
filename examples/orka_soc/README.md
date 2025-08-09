## Cognitive Society Workflows (Local, Optimized)

This folder contains three optimized “Cognitive Society” workflows designed for local LLMs via Ollama. They coordinate multiple reasoning personas, iteratively refine positions, and converge to an agreement with memory support.

- cognitive_society_with_memory_local_optimal_deepseek-8b.yml
- cognitive_society_with_memory_local_optimal_deepseek-32b.yml
- cognitive_society_with_memory_local_optimal-gpt-oss-20b.yml

### Goals
- Multi-agent debate with distinct roles (progressive, conservative, realist, purist)
- Iterative refinement loop with scoring and early stopping
- Agreement finding + final synthesis
- RedisStack-based short-term memory for debate continuity

### Prerequisites
- RedisStack running (orka-start is recommended)
- Ollama running with pulled models referenced in the workflow (e.g., deepseek-r1:8b, deepseek-r1:32b, gpt-oss:20b)

Example (PowerShell):

```
ollama pull deepseek-r1:8b
ollama pull deepseek-r1:32b
ollama pull gpt-oss:20b
```

### Common Structure
- Orchestrator: sequential strategy with a top-level loop node and final synthesis
- Loop internal workflow:
  - shared_memory_reader → opening_positions (fork) → join
  - agreement_finder → collaborative_refinement (fork) → join
  - synthesis_attempt → agreement_moderator → shared_memory_writer
- Loop continues until the agreement score meets the threshold
- After the loop: meta_debate_reflection → final_synthesis_processor

### Memory
- Namespace: `society_memory`
- Short-term, vector-enabled storage for recent debate context
- Writer logs loop rounds, agreement summaries, and scores

### Key Differences Between Files
- 8b vs 32b vs 20b: same orchestration, different local models and temperature defaults for quality vs. speed trade-offs
- 8b is most cost-efficient, 32b produces richer language, 20b is a balanced GPT-OSS option

### How to Run

```
orka run examples/orka_soc/cognitive_society_with_memory_local_optimal_deepseek-8b.yml "How should cities balance green growth and housing affordability?"

# or
orka run examples/orka_soc/cognitive_society_with_memory_local_optimal_deepseek-32b.yml "What AI safety measures should be prioritized for open-source models?"

# or
orka run examples/orka_soc/cognitive_society_with_memory_local_optimal-gpt-oss-20b.yml "What is the role of nuclear energy in a decarbonized grid?"
```

### Tuning Tips
- Increase `score_threshold` for stricter convergence
- Adjust `max_loops` for longer/shorter deliberation
- Use `max_length_per_category` in `cognitive_extraction` to control token use
- Raise/Lower `similarity_threshold` in `shared_memory_reader` to change recall breadth

### Troubleshooting
- If no agreement is reached, lower `score_threshold` (e.g., from 0.90 to 0.75)
- Verify Ollama endpoint (`model_url`) and models exist (`ollama list`)
- Ensure RedisStack index is healthy (`orka memory watch`) and vector search is enabled


