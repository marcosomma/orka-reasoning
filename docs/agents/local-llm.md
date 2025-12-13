# Local LLM Agent

**Type:** `local_llm`  
**Category:** LLM Agent  
**Version:** v0.9.4+

## Overview

The Local LLM Agent integrates with locally running large language models, providing privacy-preserving AI processing without sending data to external APIs. Supports Ollama, LM Studio, and any OpenAI-compatible endpoint.

## Basic Configuration

```yaml
- id: local_processor
  type: local_llm
  provider: lm_studio
  model: llama3.2:latest
  model_url: http://localhost:1234
  temperature: 0.7
  prompt: "{{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier |
| `type` | string | Must be `local_llm` |
| `provider` | string | `ollama`, `lm_studio`, or `openai_compatible` |
| `model` | string | Model name (provider-specific) |
| `model_url` | string | API endpoint URL |
| `prompt` | string | Template for the prompt |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `temperature` | float | `0.7` | Creativity (0.0-2.0) |
| `max_tokens` | int | `1000` | Maximum response length |
| `top_p` | float | `1.0` | Nucleus sampling |
| `top_k` | int | `40` | Token selection (Ollama) |
| `repeat_penalty` | float | `1.1` | Repetition control (Ollama) |
| `timeout` | float | `120.0` | Longer for local models |
| `stream` | bool | `false` | Stream response |
| `system_prompt` | string | - | System context |

## Supported Providers

### Ollama

```yaml
- id: ollama_agent
  type: local_llm
  provider: lm_studio
  model: "llama3.2:latest"
  model_url: "http://localhost:1234"
  temperature: 0.7
  prompt: "{{ input }}"
```

**Popular Ollama Models:**
- `llama3.2:latest` - Meta's Llama 3.2 (3B, 8B, 70B)
- `llama3:8b` - Llama 3 8B
- `mistral:latest` - Mistral 7B
- `codellama:latest` - Code-specialized
- `deepseek-coder:latest` - DeepSeek Coder
- `qwen2.5:latest` - Qwen 2.5
- `phi3:latest` - Microsoft Phi-3

### LM Studio

```yaml
- id: lm_studio_agent
  type: local_llm
  provider: lm_studio
  model: "mistral-7b-instruct"
  model_url: "http://localhost:1234/v1/chat/completions"
  temperature: 0.5
  prompt: "{{ input }}"
```

### Generic OpenAI-Compatible

```yaml
- id: custom_local
  type: local_llm
  provider: openai_compatible
  model: "custom-model-name"
  model_url: "http://localhost:8080/v1/chat/completions"
  temperature: 0.7
  prompt: "{{ input }}"
```

## Usage Examples

### Example 1: Privacy-Sensitive Processing

```yaml
- id: private_analyzer
  type: local_llm
  provider: lm_studio
  model: "llama3:8b"
  model_url: "http://localhost:1234"
  temperature: 0.3
  prompt: |
    Analyze this confidential data (stays on local machine):
    {{ input }}
    
    Provide insights without sending to external services.
```

### Example 2: Code Generation

```yaml
- id: code_helper
  type: local_llm
  provider: lm_studio
  model: "codellama:13b"
  model_url: "http://localhost:1234"
  temperature: 0.2
  system_prompt: "You are an expert programmer."
  prompt: |
    Generate {{ previous_outputs.language }} code for:
    {{ input }}
    
    Include comments and error handling.
```

### Example 3: Multi-Model Evaluation

```yaml
- id: llama_answer
  type: local_llm
  provider: lm_studio
  model: "llama3:8b"
  model_url: "http://localhost:1234"
  prompt: "{{ input }}"

- id: mistral_answer
  type: local_llm
  provider: lm_studio
  model: "mistral:7b"
  model_url: "http://localhost:1234"
  prompt: "{{ input }}"

- id: compare_results
  type: openai-answer
  prompt: |
    Compare these answers and synthesize the best response:
    
    Llama: {{ previous_outputs.llama_answer }}
    Mistral: {{ previous_outputs.mistral_answer }}
```

### Example 4: Local-First with Cloud Fallback

```yaml
- id: local_or_cloud
  type: failover
  children:
    - id: try_local
      type: local_llm
      provider: lm_studio
      model: "llama3:8b"
      model_url: "http://localhost:1234"
      timeout: 30.0
      prompt: "{{ input }}"
    
    - id: fallback_cloud
      type: openai-answer
      model: gpt-3.5-turbo
      prompt: "{{ input }}"
```

### Example 5: Specialized Tasks

```yaml
# Translation
- id: translator
  type: local_llm
  provider: lm_studio
  model: "aya:8b"  # Multilingual model
  model_url: "http://localhost:1234"
  temperature: 0.3
  prompt: |
    Translate to {{ target_language }}:
    {{ input }}

# Summarization
- id: summarizer
  type: local_llm
  provider: lm_studio
  model: "mistral:7b"
  model_url: "http://localhost:1234"
  temperature: 0.5
  prompt: |
    Summarize in 3 bullet points:
    {{ input }}

# SQL Generation
- id: sql_generator
  type: local_llm
  provider: lm_studio
  model: "sqlcoder:7b"
  model_url: "http://localhost:1234"
  temperature: 0.1
  prompt: |
    Generate SQL query for:
    {{ input }}
    
    Schema: {{ database_schema }}
```

## Installation & Setup

### Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2
ollama pull mistral
ollama pull codellama

# Verify running
ollama list

# Start server (if not auto-started)
ollama serve
```

### LM Studio Setup

1. Download LM Studio from https://lmstudio.ai
2. Load a model (e.g., Mistral 7B)
3. Start local server (default port 1234)
4. Use the provided endpoint in configuration

## Model Selection Guide

| Model | Size | Use Case | Speed | Quality |
|-------|------|----------|-------|---------|
| llama3.2:3b | 3B | Fast, simple tasks | Very Fast | Good |
| llama3:8b | 8B | General purpose | Fast | Very Good |
| llama3:70b | 70B | Complex reasoning | Slow | Excellent |
| mistral:7b | 7B | Balanced performance | Fast | Very Good |
| codellama:13b | 13B | Code generation | Medium | Excellent |
| deepseek-coder:6.7b | 6.7B | Coding | Fast | Very Good |
| qwen2.5:7b | 7B | Multilingual | Fast | Very Good |

## Performance Optimization

### 1. Model Size vs Speed

```yaml
# Fast responses (3-7B models)
- id: quick_response
  type: local_llm
  provider: lm_studio
  model: "llama3.2:3b"  # Smallest, fastest
  temperature: 0.7
  prompt: "{{ input }}"

# Quality responses (13B+ models)
- id: quality_response
  type: local_llm
  provider: lm_studio
  model: "llama3:70b"  # Largest, best quality
  temperature: 0.7
  prompt: "{{ input }}"
  timeout: 300.0  # Longer timeout needed
```

### 2. GPU Acceleration

```bash
# Check GPU is being used
ollama run llama3:8b
# Should show GPU memory usage

# Configure GPU layers (in Ollama)
export OLLAMA_NUM_GPU=1
export OLLAMA_GPU_OVERHEAD=0
```

### 3. Caching Strategies

```yaml
# Check memory cache first
- id: memory_check
  type: memory-reader
  namespace: llm_responses
  params:
    similarity_threshold: 0.9
  prompt: "{{ input }}"

- id: route_to_llm
  type: router
  params:
    decision_key: memory_check
    routing_map:
      "found": [return_cached]
      "not_found": [compute_llm, cache_response]

- id: compute_llm
  type: local_llm
  provider: lm_studio
  model: "llama3:8b"
  model_url: "http://localhost:1234"
  prompt: "{{ input }}"

- id: cache_response
  type: memory-writer
  namespace: llm_responses
  params:
    vector: true
  decay_config:
    enabled: true
    default_long_term_hours: 168
  prompt: "Q: {{ input }} A: {{ previous_outputs.compute_llm }}"
```

### 4. Parallel Processing

```yaml
# Process multiple items in parallel
- id: fork_processing
  type: fork
  targets:
    - [process_item_1]
    - [process_item_2]
    - [process_item_3]

- id: process_item_1
  type: local_llm
  provider: lm_studio
  model: "llama3:8b"
  model_url: "http://localhost:1234"
  prompt: "Process: {{ item_1 }}"
```

## Cost Comparison

| Model Type | Provider | Cost per 1M tokens | Privacy | Speed |
|------------|----------|-------------------|---------|-------|
| Local LLM (llama3:8b) | Ollama | $0 (hardware cost) | ✅ Full | Medium |
| Local LLM (llama3:70b) | Ollama | $0 (hardware cost) | ✅ Full | Slow |
| gpt-4o | OpenAI | ~$5 | ❌ Cloud | Fast |
| gpt-3.5-turbo | OpenAI | ~$0.50 | ❌ Cloud | Very Fast |

## Best Practices

### 1. Temperature Settings

```yaml
# Factual/Code tasks
temperature: 0.1-0.3

# General conversation
temperature: 0.5-0.7

# Creative writing
temperature: 0.8-1.2
```

### 2. Timeout Management

```yaml
# Larger models need more time
- id: large_model
  type: local_llm
  provider: lm_studio
  model: "llama3:70b"
  timeout: 300.0  # 5 minutes
  prompt: "{{ input }}"

# Smaller models are faster
- id: small_model
  type: local_llm
  provider: lm_studio
  model: "llama3.2:3b"
  timeout: 30.0  # 30 seconds
  prompt: "{{ input }}"
```

### 3. System Prompts

```yaml
- id: specialized_agent
  type: local_llm
  provider: lm_studio
  model: "llama3:8b"
  model_url: "http://localhost:1234"
  system_prompt: |
    You are an expert {{ domain }} consultant with 20 years of experience.
    You provide practical, actionable advice with real-world examples.
    You are concise but thorough.
  prompt: "{{ input }}"
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Ollama not running | `ollama serve` |
| Model not found | Model not pulled | `ollama pull model_name` |
| Very slow responses | CPU-only processing | Enable GPU acceleration |
| Out of memory | Model too large for GPU | Use smaller model or increase RAM |
| Timeout errors | Model too slow | Increase `timeout`, use smaller model |
| Poor quality | Wrong model for task | Use specialized model (e.g., codellama for code) |

## Hardware Requirements

| Model Size | Min RAM | Recommended RAM | GPU | Speed |
|------------|---------|-----------------|-----|-------|
| 3B | 4GB | 8GB | Optional | Fast |
| 7-8B | 8GB | 16GB | 4GB VRAM | Medium |
| 13B | 16GB | 32GB | 8GB VRAM | Medium-Slow |
| 70B | 64GB | 128GB | 24GB VRAM | Slow |

## Advanced Example: Multi-Stage Local Processing

```yaml
orchestrator:
  id: local-processing-pipeline
  strategy: sequential
  agents: [initial_analysis, refinement, quality_check, final_output]

agents:
  # Stage 1: Fast initial analysis
  - id: initial_analysis
    type: local_llm
    provider: lm_studio
    model: "llama3.2:3b"  # Fast, lightweight
    model_url: "http://localhost:1234"
    temperature: 0.7
    prompt: |
      Quick analysis of: {{ input }}
      Provide initial thoughts and key points.

  # Stage 2: Detailed refinement
  - id: refinement
    type: local_llm
    provider: lm_studio
    model: "llama3:8b"  # More capable
    model_url: "http://localhost:1234"
    temperature: 0.5
    prompt: |
      Refine this analysis: {{ previous_outputs.initial_analysis }}
      Original input: {{ input }}
      
      Provide detailed, accurate response.

  # Stage 3: Quality check
  - id: quality_check
    type: local_llm
    provider: lm_studio
    model: "mistral:7b"  # Different perspective
    model_url: "http://localhost:1234"
    temperature: 0.2
    prompt: |
      Verify quality of this analysis:
      {{ previous_outputs.refinement }}
      
      Check for:
      - Accuracy
      - Completeness
      - Clarity
      - Logical flow
      
      Rate 0.0-1.0: SCORE: X.XX

  # Stage 4: Final output
  - id: final_output
    type: local_llm
    provider: lm_studio
    model: "llama3:8b"
    model_url: "http://localhost:1234"
    temperature: 0.3
    prompt: |
      Create final polished response:
      
      Refined analysis: {{ previous_outputs.refinement }}
      Quality score: {{ previous_outputs.quality_check }}
      
      Produce publication-ready output.
```

## Environment Variables

```bash
# Ollama configuration
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_MODELS=/path/to/models
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=2

# OrKa configuration
export LOCAL_LLM_TIMEOUT=120
```

## Related Documentation

- [OpenAI Answer Agent](./openai-answer.md)
- [Memory Integration](../memory-integration-guide.md)
- [Failover Node](../nodes/failover.md)
- [Performance Optimization](../performance-guide.md)

## Version History

- **v0.9.4**: Current stable version with multi-provider support
- **v0.8.0**: Added LM Studio support
- **v0.7.0**: Initial Ollama integration

