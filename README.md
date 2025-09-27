# OrKa - AI Agent Orchestration

<p align="center">

<img src="https://orkacore.com/assets/ORKA_logo.png" alt="OrKa Logo" style="border-radius: 25px; width: 400px; height:400px" />

[![GitHub Tag](https://img.shields.io/github/v/tag/marcosomma/orka-reasoning?color=blue)](https://github.com/marcosomma/orka-reasoning/tags)
[![PyPI - License](https://img.shields.io/pypi/l/orka-reasoning?color=blue)](https://pypi.org/project/orka-reasoning/)

[![codecov](https://img.shields.io/badge/codecov-76.97%25-yellow?&amp;logo=codecov)](https://codecov.io/gh/marcosomma/orka-reasoning)
[![orka-reasoning](https://snyk.io/advisor/python/orka-reasoning/badge.svg)](https://snyk.io/advisor/python/orka-reasoning)

[![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&amp;logo=pypi&amp;logoColor=1f73b7)](https://pypi.org/project/orka-reasoning/)[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&amp;logo=docker&amp;logoColor=white)](https://hub.docker.com/r/marcosomma/orka-ui)[![Documentation](https://img.shields.io/badge/Docs-blue?style=for-the-badge&amp;logo=googledocs&amp;logoColor=%23fff&amp;link=https%3A%2F%2Forkacore.com%2Fdocs%2Findex.html)](https://orkacore.com/docs/index.html)

[![orkacore](https://img.shields.io/badge/orkacore-.com-green?labelColor=blue&amp;style=for-the-badge&amp;link=https://orkacore.com/)](https://orkacore.com/)


[![Pepy Total Downloads](https://img.shields.io/pepy/dt/orka-reasoning?style=for-the-badge&amp;label=Downloads%20from%20April%202025&amp;color=blue&amp;link=https%3A%2F%2Fpiptrends.com%2Fpackage%2Forka-reasoning)](https://clickpy.clickhouse.com/dashboard/orka-reasoning)
</p>

## What OrKa Does

OrKa lets you define AI workflows in YAML files instead of writing complex Python code. You describe what you want - like "search memory, then ask an AI, then save the result" - and OrKa handles the execution.

Think of it as a streamlined, open-source alternative to CrewAI or LangChain, but with a focus on:
- **YAML configuration** instead of code
- **Built-in memory** that remembers and forgets intelligently  
- **Local LLM support** for privacy
- **Simple setup** with Docker

## Basic Example

Instead of writing Python code like this:
```python
# Complex Python orchestration code
memory_results = search_memory(query)
if not memory_results:
    web_results = search_web(query)
    answer = llm.generate(web_results + query)
else:
    answer = llm.generate(memory_results + query)
save_to_memory(query, answer)
```

You write a YAML file like this:
```yaml
orchestrator:
  id: simple-qa
  agents: [memory_search, web_search, answer, memory_store]

agents:
  - id: memory_search
    type: memory
    operation: read
    prompt: "Find: {{ input }}"
    
  - id: web_search  
    type: search
    prompt: "Search: {{ input }}"
    
  - id: answer
    type: local_llm
    model: llama3.2
    prompt: "Answer based on: {{ previous_outputs }}"
    
  - id: memory_store
    type: memory
    operation: write
    prompt: "Store: {{ input }} -> {{ previous_outputs.answer }}"
```

## Installation

```bash
# Install OrKa
pip install orka-reasoning

# Start Redis (for memory)
orka-start

# Memory TUI
orka memory watch

# Run a workflow
orka run my-workflow.yml "What is machine learning?"
```

## How It Works

### 1. Agent Types
OrKa provides several agent types you can use in your workflows:

- **`memory`** - Read from or write to persistent memory
- **`local_llm`** - Use local models (Ollama, LM Studio)
- **`openai-*`** - Use OpenAI models  
- **`search`** - Web search
- **`router`** - Conditional branching
- **`fork/join`** - Parallel processing
- **`loop`** - Iterative workflows
- **`GraphScout`** - [BETA] Find best path for workflow execution

### 2. Memory System
OrKa includes a memory system that:
- Stores conversations and facts
- Searches semantically (finds related content, not just exact matches)
- Automatically forgets old, unimportant information
- Uses Redis for fast retrieval

### 3. Workflow Execution
When you run `orka run workflow.yml "input"`, OrKa:
1. Reads your YAML configuration
2. Creates the agents you defined
3. Runs them in the order you specified
4. Passes outputs between agents
5. Returns the final result

### 4. Local LLM Support
OrKa works with local models through:
- **Ollama** - `ollama pull llama3.2` then use `provider: ollama`
- **LM Studio** - Point to your local API endpoint
- **Any LLM-compatible API**

## Common Patterns

### Memory-First Q&A
```yaml
# Check memory first, search web if nothing found
agents:
  - id: check_memory
    type: memory
    operation: read

  - id: binary_agent
    type: local_llm
    prompt: |
      Given those memory {{get_agent_response('check_memory')}} and this input {{ input }}
      Is an search on internet required?
      Only answer with 'true' or 'false' 
    
  - id: route_decision
    type: router
    decision_key: 'binary_agent'
    routing_map:
      "true": [answer_from_memory]
      "false": [web_search, answer_from_web]
```

### Parallel Processing
```yaml
# Analyze sentiment and toxicity simultaneously
agents:
  - id: parallel_analysis
    type: fork
    targets:
      - [sentiment_analyzer]
      - [toxicity_checker]
      
  - id: combine_results
    group: parallel_analysis
    type: join
```

### Iterative Improvement
```yaml
# Keep improving until quality threshold met
agents:
  - id: improvement_loop
    type: loop
    max_loops: 5
    score_threshold: 0.85
    internal_workflow:
      agents: [analyzer, scorer]
```

## Comparison to Alternatives

| Feature | OrKa | LangChain | CrewAI |
|---------|------|-----------|---------|
| Configuration | YAML files | Python code | Python code |
| Memory | Built-in with decay | External/manual | External/manual |
| Local LLMs | First-class support | Via adapters | Limited |
| Parallel execution | Native fork/join | Manual threading | Agent-based |
| Learning | Automatic memory management | Manual | Manual |

## Quick Start Examples

### 1. Simple Q&A with Memory
```bash
# Copy example
cp examples/simple_memory_preset_demo.yml my-qa.yml

# Run it
orka run my-qa.yml "What is artificial intelligence?"
```

### 2. Web Search + Memory
```bash
# Copy example  
cp examples/person_routing_with_search.yml web-qa.yml

# Run it
orka run web-qa.yml "Latest news about quantum computing"
```

### 3. Local LLM Chat
```bash
# Start Ollama
ollama pull llama3.2

# Copy example
cp examples/multi_model_local_llm_evaluation.yml local-chat.yml

# Run it
orka run local-chat.yml "Explain machine learning simply"
```

## Documentation

- [Getting Started Guide](docs/getting-started.md) - Detailed setup and first workflows
- [Agent Types](docs/agents.md) - All available agent types and configurations  
- [Memory System](docs/MEMORY_SYSTEM_GUIDE.md) - How memory works and configuration
- [YAML Configuration](docs/yaml-configuration-guide.md) - Complete YAML reference
- [Examples](examples/README.md) - 15+ ready-to-use workflow templates

## Getting Help

- [GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues) - Bug reports and feature requests
- [Documentation](https://orkacore.com/docs) - Full documentation
- [Examples](examples/) - Working examples you can copy and modify

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 License - see [LICENSE](LICENSE) for details.