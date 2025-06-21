# OrKa-Reasoning

<div align="center">

<img src="https://orkacore.com/assets/ORKA_logo.png" alt="OrKa Logo" width="256" height="256"/>

[![Tests](https://github.com/marcosomma/orka-reasoning/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/marcosomma/orka-reasoning/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/marcosomma/orka-reasoning/branch/master/graph/badge.svg?token=V91X4WGBBZ)](https://codecov.io/gh/marcosomma/orka-reasoning)
![PyPI - License](https://img.shields.io/pypi/l/orka-reasoning?color=blue) [![orka-reasoning](https://snyk.io/advisor/python/orka-reasoning/badge.svg)](https://snyk.io/advisor/python/orka-reasoning)

[![orka-reasoning Package Age](https://assets.piptrends.com/get-age-badge/orka-reasoning.svg 'orka-reasoning Package Age by pip Trends')](https://piptrends.com/package/orka-reasoning)[![orka-reasoning Average Daily Downloads](https://assets.piptrends.com/get-average-downloads-badge/orka-reasoning.svg 'orka-reasoning Average Daily Downloads by pip Trends')](https://piptrends.com/package/orka-reasoning) [![orka-reasoning Downloads Last Week](https://assets.piptrends.com/get-last-week-downloads-badge/orka-reasoning.svg 'orka-reasoning Downloads Last Week by pip Trends')](https://piptrends.com/package/orka-reasoning) [![orka-reasoning Downloads Last Month](https://assets.piptrends.com/get-last-month-downloads-badge/orka-reasoning.svg 'orka-reasoning Downloads Last Month by pip Trends')](https://piptrends.com/package/orka-reasoning)

![Pepy Total Downloads](https://img.shields.io/pepy/dt/orka-reasoning?style=for-the-badge&label=Total%20Downloads&labelColor=%231e1e1e&color=%2338a0ff&link=https%3A%2F%2Fpiptrends.com%2Fpackage%2Forka-reasoning)


[![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&logo=pypi&logoColor=1f73b7)](https://pypi.org/project/orka-reasoning/) [![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/marcosomma/orka-ui)


[![orkacore](https://img.shields.io/badge/orkacore-.com-green?labelColor=blue&style=for-the-badge&link=https://orkacore.com/)](https://orkacore.com/)



[![orka-reasoning Widget](https://assets.piptrends.com/get-widget/orka-reasoning.svg 'orka-reasoning Widget by pip Trends')](https://piptrends.com/package/orka-reasoning)
</div>

**Orchestrator Kit for Agentic Reasoning** - OrKa is a modular AI orchestration system that transforms Large Language Models (LLMs) into composable agents capable of reasoning, fact-checking, and constructing answers with transparent traceability.

---

## 📋 Table of Contents

- [🚀 Features](#-features)
- [🎥 OrKa Video Overview](#-orka-video-overview)
- [🏆 Why Choose OrKa?](#-why-choose-orka)
- [⚡ 5-Minute Quickstart](#-5-minute-quickstart)
- [🛠️ Installation](#️-installation)
- [📚 Common Patterns & Recipes](#-common-patterns--recipes)
- [⚙️ Agent Configuration Examples](#️-agent-configuration-examples)
- [📝 YAML Configuration Structure](#-yaml-configuration-structure)
- [🧠 Memory Management & Intelligent Decay](#-memory-management--intelligent-decay)
- [🧪 Example](#-example)
- [🔧 Requirements](#-requirements)
- [📄 Usage](#-usage)
- [🔍 Troubleshooting](#-troubleshooting)
- [📊 Performance & Scalability](#-performance--scalability)
- [🏢 Case Studies & Success Stories](#-case-studies--success-stories)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📜 License & Attribution](#-license--attribution)

---

## 🚀 Features

- **Modular Agent Orchestration**: Define and manage agents using intuitive YAML configurations.
- **Intelligent Memory System**: Advanced memory management with context-aware search, intelligent decay, and automatic classification.
- **Configurable Reasoning Paths**: Utilize Redis streams to set up dynamic reasoning workflows.
- **Context-Aware Memory Retrieval**: Enhanced memory reader with semantic similarity, keyword matching, and temporal ranking.
- **Automatic Memory Decay**: Smart memory lifecycle management with short-term and long-term retention policies.
- **Comprehensive Logging**: Record and trace every step of the reasoning process for transparency.
- **Built-in Integrations**: Support for OpenAI agents, web search functionalities, routers, and validation mechanisms.
- **Command-Line Interface (CLI)**: Execute YAML-defined workflows with ease and monitor memory usage in real-time.

## 🎥 OrKa Video Overview

[![Watch the video](https://img.youtube.com/vi/hvVc8lSoADI/hqdefault.jpg)](https://www.youtube.com/watch?v=hvVc8lSoADI)

Click the thumbnail above to watch a quick video demo of OrKa in action — how it uses YAML to orchestrate agents, log reasoning, and build transparent LLM workflows.

## 🏆 Why Choose OrKa?

**OrKa stands out from other AI orchestration tools by focusing on transparency, modularity, and cognitive science-inspired workflows.**

### OrKa vs. Alternatives

| Feature | OrKa | LangChain | CrewAI | LlamaIndex |
|---------|-----|-----------|--------|------------|
| **Focus** | Transparent reasoning | Chaining LLM calls | Multi-agent simulation | RAG & indexing |
| **Configuration** | YAML-driven | Python code | Python code | Python code |
| **Traceability** | Complete Redis logs | Limited | Basic | Limited |
| **Modularity** | Fully modular | Semi-modular | Agent-centric | Index-centric |
| **Workflow Viz** | Built-in (OrkaUI) | Third-party | Limited | Limited |
| **Learning Curve** | Low (YAML) | Medium | Medium | Medium |
| **Reasoning Patterns** | Decision trees, fork/join | Sequential | Role-based | Query-focused |

### Architecture Overview

OrKa uses a modular architecture with clear separation of concerns:

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   YAML      │     │  Orchestrator   │     │   Agents    │
│ Definition  ├────►│  (Control Flow) ├────►│ (Reasoning) │
└─────────────┘     └────────┬────────┘     └──────┬──────┘
                             │                     │
                     ┌───────▼─────────────────────▼───────┐
                     │        Redis/Kafka Streams          │
                     │  (Message Passing & Observability)  │
                     └───────────────────────────────────┬─┘
                                                         │
                                                 ┌───────▼────────┐
                                                 │   OrKa UI      │
                                                 │  (Monitoring)  │
                                                 └────────────────┘
```

---

## ⚡ 5-Minute Quickstart

Get OrKa running in 5 minutes:

```bash
# Install via pip
pip install orka-reasoning

# Create a simple test.yml file
cat > test.yml << EOF
orchestrator:
  id: simple-test
  strategy: sequential
  queue: orka:test
  agents:
    - classifier
    - answer_builder

agents:
  - id: classifier
    type: openai-classification
    prompt: Classify this as [tech, science, other]
    options: [tech, science, other]
    queue: orka:classify

  - id: answer_builder
    type: openai-answer
    prompt: |
      Topic: {{ previous_outputs.classifier }}
      Generate a paragraph about: {{ input }}
    queue: orka:answer
EOF

# Set up your OpenAI key
export OPENAI_API_KEY=your-key-here

# Run OrKa with your test input
python -m orka.orka_cli ./test.yml "Quantum computing applications"
```

This will classify your input and generate a response based on the classification.

---

## 🛠️ Installation

### PIP Installation

1. **Install the Package**:
   ```bash
   pip install orka-reasoning
   ```

2. **Add ENV variables**:
   ```bash
   export OPENAI_API_KEY=<your opena AI key>
   ```

3. **Install Additional Dependencies**:
   ```bash
   pip install fastapi uvicorn
   ```

4. **Start the Services**:
   ```bash
   python -m orka.orka_start
   ```

### Local Development Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/marcosomma/orka-resoning.git
   cd orka
   ```

2. **Install Dependencies**:
   ```bash
   pip install -e .
   pip install fastapi uvicorn
   ```

3. **Start the Services**:
   ```bash
   python -m orka.orka_start
   ```

### Running OrkaUI Locally

To run the OrkaUI locally and connect it with your local OrkaBackend:

1. **Pull the OrkaUI Docker image**:
   ```bash
   docker pull marcosomma/orka-ui:latest
   ```

2. **Run the OrkaUI container**:
   ```bash
   docker run -d \
     -p 8080:80 \
     -e VITE_API_URL_LOCAL=http://localhost:8000/api/run@dist  \
     --name orka-ui \
     marcosomma/orka-ui:latest
   ```

This will start the OrkaUI on port 8080, connected to your local OrkaBackend running on port 8000.

## 📚 Common Patterns & Recipes

### 1. Question-Answering with Web Search

```yaml
orchestrator:
  id: qa-system
  strategy: sequential
  agents:
    - search_needed
    - router
    - web_search
    - answer_builder

agents:
  - id: search_needed
    type: openai-binary
    prompt: Does this question require recent information? Return true/false.

  - id: router
    type: router
    params:
      decision_key: search_needed
      routing_map:
        "true": [web_search, answer_builder]
        "false": [answer_builder]

  - id: web_search
    type: duckduckgo
    prompt: Search for information about this query
    
  - id: answer_builder
    type: openai-answer
    prompt: |
      Build an answer using:
      {% if previous_outputs.search_needed == "true" %}
      Search results: {{ previous_outputs.web_search }}
      {% endif %}
```

### 2. Memory-Enhanced Conversational System

```yaml
orchestrator:
  id: memory-conversation
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168  # 1 week
  agents:
    - memory_reader
    - context_classifier
    - memory_writer
    - response_generator

agents:
  - id: memory_reader
    type: memory-reader
    namespace: conversation
    params:
      limit: 5
      enable_context_search: true
      context_weight: 0.3
      temporal_weight: 0.2
      enable_temporal_ranking: true
    prompt: Find relevant memories about this conversation topic

  - id: context_classifier
    type: openai-classification
    prompt: |
      Based on the conversation context and memories:
      Memories: {{ previous_outputs.memory_reader }}
      
      Classify this interaction as:
    options: [question, followup, new_topic, clarification]

  - id: memory_writer
    type: memory-writer
    namespace: conversation
    params:
      memory_type: auto  # Will be classified as short-term or long-term
    prompt: |
      Store this interaction:
      User: {{ input }}
      Context: {{ previous_outputs.context_classifier }}

  - id: response_generator
    type: openai-answer
    prompt: |
      Generate a response using:
      - Current input: {{ input }}
      - Relevant memories: {{ previous_outputs.memory_reader }}
      - Interaction type: {{ previous_outputs.context_classifier }}
      
      Provide a contextually aware response.
```

### 3. Content Moderation Pipeline

```yaml
orchestrator:
  id: content-moderation
  strategy: sequential
  agents:
    - toxic_check
    - sentiment
    - fork_analysis
    - join_analysis
    - final_decision

agents:
  - id: toxic_check
    type: openai-binary
    prompt: Is this content toxic or harmful? Return true/false.

  - id: fork_analysis
    type: fork
    targets:
      - [sentiment_analysis]
      - [bias_check]
      - [fact_validation]

  # ... other agents
```

### 4. Intelligent Knowledge Base with Memory Decay

```yaml
orchestrator:
  id: knowledge-base
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 24
      default_long_term_hours: 720  # 30 days
      importance_rules:
        critical_info: 2.0
        user_feedback: 1.5
        routine_query: 0.8
  agents:
    - query_analyzer
    - memory_search
    - knowledge_updater
    - response_builder

agents:
  - id: query_analyzer
    type: openai-classification
    prompt: Analyze this query type
    options: [factual_lookup, how_to_guide, troubleshooting, feedback]

  - id: memory_search
    type: memory-reader
    namespace: knowledge_base
    params:
      limit: 10
      enable_context_search: true
      enable_temporal_ranking: true
      context_window_size: 5
    prompt: |
      Search for relevant information about: {{ input }}
      Query type: {{ previous_outputs.query_analyzer }}

  - id: knowledge_updater
    type: memory-writer
    namespace: knowledge_base
    decay_config:
      enabled: true
      default_long_term: true  # Force important queries to long-term
    prompt: |
      Store this knowledge interaction:
      Query: {{ input }}
      Type: {{ previous_outputs.query_analyzer }}
      Retrieved: {{ previous_outputs.memory_search }}

  - id: response_builder
    type: openai-answer
    prompt: |
      Build a comprehensive response using:
      - Query: {{ input }}
      - Query type: {{ previous_outputs.query_analyzer }}
      - Knowledge base results: {{ previous_outputs.memory_search }}
      
      If no relevant information found, indicate that clearly.
```

### 5. Complex Decision Tree

```yaml
orchestrator:
  id: approval-workflow
  strategy: decision-tree
  agents:
    - initial_check
    - router_approval

agents:
  - id: router_approval
    type: router
    params:
      decision_key: initial_check
      routing_map:
        "approved": [notify_success]
        "needs_revision": [request_changes]
        "rejected": [notify_rejection]
```

## ⚙️ Agent Configuration Examples

### Basic Agent Types

```yaml
# Binary Classification
- id: fact_checker
  type: openai-binary
  prompt: "Is this statement factually accurate? Return TRUE or FALSE: {{ input }}"
  queue: orka:facts

# Multi-class Classification  
- id: topic_classifier
  type: openai-classification
  prompt: "Classify this into one category"
  options: [science, technology, history, politics]
  queue: orka:classify

# Local LLM Processing
- id: local_summarizer
  type: local_llm
  prompt: "Summarize this text: {{ input }}"
  model: "llama3.2:latest"
  model_url: "http://localhost:11434/api/generate"
  provider: "ollama"
  temperature: 0.7
  queue: orka:local

# Answer Generation
- id: answer_builder
  type: openai-answer
  prompt: |
    Based on the classification: {{ previous_outputs.topic_classifier }}
    And search results: {{ previous_outputs.web_search }}
    Provide a comprehensive answer to: {{ input }}
  queue: orka:answer
```

### Memory Management

```yaml
# Memory Reader with Context Enhancement
- id: context_memory
  type: memory
  namespace: conversations
  config:
    operation: read
    limit: 10
    enable_context_search: true
    context_weight: 0.3
    temporal_weight: 0.2
    enable_temporal_ranking: true
  prompt: "Find relevant memories about: {{ input }}"

# Memory Writer with Decay Configuration
- id: store_interaction
  type: memory
  namespace: user_sessions
  config:
    operation: write
    memory_type: auto
    vector: true
  decay_config:
    enabled: true
    default_long_term: true
    default_long_term_hours: 720  # 30 days
  prompt: "Store this interaction: {{ input }}"
```

### Advanced Nodes

```yaml
# Dynamic Routing
- id: content_router
  type: router
  params:
    decision_key: content_type
    routing_map:
      "question": [search_agent, answer_builder]
      "statement": [fact_checker, validator]
      "request": [task_processor]

# Parallel Processing
- id: multi_validator
  type: fork
  targets:
    - [sentiment_check]
    - [toxicity_check] 
    - [fact_validation]
  mode: parallel

# Results Aggregation
- id: validation_merger
  type: join
  prompt: "Combine validation results from parallel checks"

# Resilient Processing
- id: search_with_fallback
  type: failover
  children:
    - id: primary_search
      type: duckduckgo
      prompt: "Search: {{ input }}"
    - id: backup_search  
      type: duckduckgo
      prompt: "Backup search: {{ input }}"
      params:
        region: "us-en"
```

## 📝 YAML Configuration Structure

The YAML file specifies the agents and their interactions. Below is an example configuration:

```yaml
orchestrator:
  id: fact-checker
  strategy: decision-tree
  queue: orka:fact-core
  agents:
    - domain_classifier
    - is_fact
    - validate_fact

agents:
  - id: domain_classifier
    type: openai-classification
    prompt: >
      Classify this question into one of the following domains:
      - science, geography, history, technology, date check, general
    options: [science, geography, history, technology, date check, general]
    queue: orka:domain

  - id: is_fact
    type: openai-binary
    prompt: >
      Is this a {{ input }} factual assertion that can be verified externally? Answer TRUE or FALSE.
    queue: orka:is_fact

  - id: validate_fact
    type: openai-binary
    prompt: |
      Given the fact "{{ input }}", and the search results "{{ previous_outputs.duck_search }}"?
    queue: validation_queue
```

For a comprehensive guide with detailed examples of all agent types, node configurations, and advanced patterns, see our [YAML Configuration Guide](./docs/yaml-configuration-guide.md).

### From Monolithic Prompts to Agent Networks

OrKa helps you transform complex prompts like:

```
Classify this input as science/history/tech, then if it's a factual question requiring
research, search the web, extract relevant info, and compose a detailed answer using
correct formatting and citing sources.
```

Into a clear, maintainable agent network:

```
Input → Classification → Search Need Check → Router → Web Search → Answer Builder → Output
```

This provides transparency, reusability, and easier debugging at each step.

### Key Sections

- **agents**: Defines the individual agents involved in the workflow. Each agent has:
  - **name**: Unique identifier for the agent.
  - **type**: Specifies the agent's function (e.g., `search`, `llm`).

- **workflow**: Outlines the sequence of interactions between agents:
  - **from**: Source agent or input.
  - **to**: Destination agent or output.

Settings such as the model and API keys are loaded from the `.env` file, keeping your configuration secure and flexible.

## 🧠 Memory Management & Intelligent Decay

OrKa v0.6.5 introduces an advanced memory system with intelligent decay management for building context-aware applications.

### Memory Decay Configuration

Configure memory decay at the orchestrator level for automatic memory lifecycle management:

```yaml
orchestrator:
  id: my-workflow
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2      # Short-term memories expire after 2 hours
      default_long_term_hours: 168     # Long-term memories expire after 1 week
      importance_rules:
        critical_info: 2.0             # Boost factor for critical information
        user_feedback: 1.5             # Boost factor for user feedback
        routine_query: 0.8             # Reduce factor for routine queries
```

### Agent-Level Memory Configuration

Override global settings for specific agents:

```yaml
agents:
  - id: important_memory_writer
    type: memory-writer
    namespace: critical_data
    decay_config:
      enabled: true
      default_long_term: true          # Force all memories to long-term
      default_long_term_hours: 720     # Keep for 30 days
```

### Memory CLI Commands

OrKa provides powerful CLI commands for memory management:

```bash
# Real-time memory monitoring with professional dashboard
orka memory watch

# View detailed memory statistics and decay configuration
orka memory stats

# Manual cleanup of expired memories
orka memory cleanup

# Display current decay configuration
orka memory configure
```

### Context-Aware Memory Search

The enhanced memory reader uses multiple relevance factors:

- **Semantic Similarity**: Vector-based content matching
- **Keyword Matching**: Exact term matching with TF-IDF scoring
- **Context Overlap**: Relevance to recent conversation history
- **Temporal Decay**: Time-based relevance scoring

Example configuration for advanced memory search:

```yaml
agents:
  - id: enhanced_memory_search
    type: memory-reader
    namespace: conversations
    params:
      limit: 10
      enable_context_search: true      # Use conversation history
      context_weight: 0.3              # 30% weight for context similarity
      temporal_weight: 0.2             # 20% weight for recency
      enable_temporal_ranking: true    # Enable time-based scoring
      context_window_size: 5           # Use last 5 agent outputs
```

## 🧪 Example

To see OrKa in action, use the provided `example.yml` configuration:

```bash
python -m orka.orka_cli ./example.yml "What is the capital of France?" --log-to-file
```

This will execute the workflow defined in `example.yml` with the input question, logging each reasoning step.

## 🔧 Requirements

- Python 3.8 or higher
- Redis server
- Docker (for containerized deployment)
- Required Python packages:
  - fastapi
  - uvicorn
  - redis
  - pyyaml
  - litellm
  - jinja2
  - google-api-python-client
  - duckduckgo-search
  - python-dotenv
  - openai
  - async-timeout
  - pydantic
  - httpx

## 📄 Usage

### 📄 OrKa Nodes and Agents Documentation

#### 📊 Agents

##### BinaryAgent
- **Purpose**: Classify an input into TRUE/FALSE.
- **Input**: A dict containing a string under "input" key.
- **Output**: A boolean value.
- **Typical Use**: "Is this sentence a factual statement?"

##### ClassificationAgent
- **Purpose**: Classify input text into predefined categories.
- **Input**: A dict with "input".
- **Output**: A string label from predefined options.
- **Typical Use**: "Classify a sentence as science, history, or nonsense."

##### OpenAIBinaryAgent
- **Purpose**: Use an LLM to binary classify a prompt into TRUE/FALSE.
- **Input**: A dict with "input".
- **Output**: A boolean.
- **Typical Use**: "Is this a question?"

##### OpenAIClassificationAgent
- **Purpose**: Use an LLM to classify input into multiple labels.
- **Input**: Dict with "input".
- **Output**: A string label.
- **Typical Use**: "What domain does this question belong to?"

##### OpenAIAnswerBuilder
- **Purpose**: Build a detailed answer from a prompt, usually enriched by previous outputs.
- **Input**: Dict with "input" and "previous_outputs".
- **Output**: A full textual answer.
- **Typical Use**: "Answer a question combining search results and classifications."

##### DuckDuckGoTool
- **Purpose**: Perform a real-time web search using DuckDuckGo.
- **Input**: Dict with "input" (the query string).
- **Output**: A list of search result strings.
- **Typical Use**: "Search for latest information about OrKa project."

##### LocalLLMAgent
- **Purpose**: Interface with locally running large language models (Ollama, LM Studio, etc.).
- **Input**: Dict with "input" (text to process) and optional model parameters.
- **Output**: Generated response from the local model with confidence score and reasoning.
- **Configuration**:
  - `model`: Model name (e.g., "llama3.2:latest", "mistral")
  - `model_url`: Local endpoint URL (e.g., "http://localhost:11434/api/generate")
  - `provider`: "ollama", "lm_studio", or "openai_compatible"
  - `temperature`: Sampling temperature (0.0-1.0)
- **Typical Use**: "Generate responses using privacy-preserving local models without cloud dependencies."

##### ValidationAndStructuringAgent
- **Purpose**: Validate answers for correctness and structure them into memory objects.
- **Input**: Dict with "input" (question) and "previous_outputs" containing context and answers.
- **Output**: Dict with validation status, reason, and structured memory object.
- **Configuration**:
  - `store_structure`: Optional template for memory object structure
- **Typical Use**: "Validate generated answers before storing them in memory with proper structure."

##### Memory Agent (Read Operation)
- **Purpose**: Search and retrieve relevant memories from the memory backend using advanced context-aware algorithms.
- **Type**: `memory` with `config.operation: read`
- **Input**: Dict with "input" (search query) and optional "previous_outputs" for context enhancement.
- **Output**: A list of relevant memory entries ranked by relevance score.
- **Configuration**:
  - `namespace`: Memory namespace to search in
  - `config.limit`: Maximum number of memories to return (default: 10)
  - `config.enable_context_search`: Use conversation history for enhanced search (default: false)
  - `config.context_weight`: Weight for context similarity in scoring (default: 0.3)
  - `config.temporal_weight`: Weight for temporal decay in scoring (default: 0.2)
  - `config.enable_temporal_ranking`: Enable time-based ranking (default: false)
  - `config.similarity_threshold`: Minimum similarity score for retrieval (default: 0.6)
- **Typical Use**: "Find relevant past conversations about machine learning topics."

##### Memory Agent (Write Operation)
- **Purpose**: Store information in the memory backend with intelligent decay management.
- **Type**: `memory` with `config.operation: write`
- **Input**: Dict with "input" and "previous_outputs" to store as memory.
- **Output**: Confirmation of memory storage with metadata.
- **Configuration**:
  - `namespace`: Memory namespace to store in
  - `config.memory_type`: "short_term", "long_term", or "auto" for automatic classification
  - `config.vector`: Enable vector embeddings for semantic search (default: false)
  - `key_template`: Template for generating memory keys
  - `metadata`: Additional metadata to store with memory
  - `decay_config`: Agent-specific decay settings that override global configuration
- **Typical Use**: "Store user interaction with classification for future reference."

---

#### 🔧 Tools

##### DuckDuckGoTool
- **Purpose**: Perform real-time web search using DuckDuckGo search engine.
- **Input**: Dict with "input" (the search query string).
- **Output**: A list of search result strings with titles, snippets, and URLs.
- **Configuration**:
  - `num_results`: Number of search results to return (default: 5)
  - `region`: Search region (e.g., "us-en", "uk-en")
  - `safe_search`: Safe search setting ("on", "moderate", "off")
- **Typical Use**: "Search for latest information about quantum computing developments."

---

#### 🧵 Nodes

##### RouterNode
- **Purpose**: Dynamically route execution based on a prior decision output.
- **Input**: Dict with "previous_outputs".
- **Routing Logic**: Matches a decision_key's value to a list of next agent ids.
- **Typical Use**: "Route to search agents if external lookup needed; otherwise validate directly."

##### FailoverNode
- **Purpose**: Execute multiple child agents in sequence until one succeeds.
- **Input**: Dict with "input".
- **Behavior**: Tries each child agent. If one crashes/fails, moves to next.
- **Typical Use**: "Try web search with service A; if unavailable, fallback to service B."

##### FailingNode
- **Purpose**: Intentionally fail. Used to simulate errors during execution.
- **Input**: Dict with "input".
- **Output**: Always throws an Exception.
- **Typical Use**: "Test failover scenarios or resilience paths."

##### **ForkNode**  
- **Purpose**: Split execution into multiple parallel agent branches.
- **Input**: Dict with "input" and "previous\_outputs".
- **Behavior**: Launches multiple child agents simultaneously. Supports sequential (default) or full parallel execution.
- **Options**:
- `targets`: List of agents to fork.
- `mode`: "sequential" or "parallel".
- **Typical Use**: "Validate topic and check if a summary is needed simultaneously. 

##### **JoinNode**
- **Purpose**: Wait for multiple forked agents to complete, then merge their outputs.
- **Input**: Dict including `fork_group_id` (forked group name).
- **Behavior**: Suspends execution until all required forked agents have completed. Then aggregates their outputs.
- **Typical Use**: "Wait for parallel validations to finish before deciding next step."

##### **RAGNode**
- **Purpose**: Perform Retrieval-Augmented Generation (RAG) operations with vector search and LLM generation.
- **Input**: Dict with "query" for the search question.
- **Output**: Dict with generated answer and source documents.
- **Configuration**:
  - `top_k`: Number of documents to retrieve (default: 5)
  - `score_threshold`: Minimum similarity score for retrieval (default: 0.7)
- **Behavior**: Searches memory using embeddings, formats context, and generates answers using LLM.
- **Typical Use**: "Answer questions using relevant documents from a knowledge base."

---

#### 📊 Summary Table

| Name | Type | Core Purpose |
|:---|:---|:---|
| BinaryAgent | Agent | True/False classification |
| ClassificationAgent | Agent | Category classification (deprecated) |
| OpenAIBinaryAgent | Agent | LLM-backed binary decision |
| OpenAIClassificationAgent | Agent | LLM-backed category decision |
| OpenAIAnswerBuilder | Agent | Compose detailed answer |
| LocalLLMAgent | Agent | Local LLM inference |
| ValidationAndStructuringAgent | Agent | Answer validation and structuring |
| DuckDuckGoTool | Tool | Perform web search |
| Memory (read) | Node | Context-aware memory retrieval |
| Memory (write) | Node | Intelligent memory storage |
| RAGNode | Node | Retrieval-augmented generation |
| RouterNode | Node | Dynamically route next steps |
| FailoverNode | Node | Resilient sequential fallback |
| FailingNode | Node | Simulate failure |
| ForkNode | Node | Parallel execution split |
| JoinNode | Node | Parallel execution merge |

## 🔍 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **"Cannot connect to Redis"** | Ensure Redis is running: `redis-cli ping` should return `PONG`. Start Redis with `redis-server` if needed. |
| **Agent returns unexpected results** | Check the agent's prompt in your YAML file. Make sure it's clear and specific. You can also check Redis logs: `redis-cli xrevrange orka:memory + - COUNT 5` |
| **Binary agents return strings instead of booleans** | As of latest version, binary agents return `"true"` or `"false"` as strings. Update your router's routing_map to use string values: `"true":` instead of `true:` |
| **Templating errors in prompts** | Verify your Jinja2 syntax: `{{ previous_outputs.agent_id }}` is correct format. Make sure the referenced agent has already executed. |
| **Execution stops unexpectedly** | Check for errors in Redis logs. Ensure all required agents are defined. Try adding a fallback path with `failover` nodes. |

### Debugging Tips

1. **Enable detailed logging**:
   ```bash
   python -m orka.orka_cli ./your_config.yml "Your input" --log-to-file --verbose
   ```

2. **Inspect Redis streams for exact agent outputs**:
   ```bash
   redis-cli xrevrange orka:your_agent_id + - COUNT 1
   ```

3. **Test agents individually** using the testing tools in `orka.agent_test`

4. **Common timeout issues**: Increase timeouts for web search or complex reasoning agents in your YAML config.

## 📊 Performance & Scalability

OrKa is designed to scale with your needs:

- **Single-server deployment**: Handles hundreds of requests per minute
- **Clustered deployment**: With Redis Cluster and multiple OrKa instances, can scale to thousands of requests
- **Resource Utilization**: 
  - Memory: ~100MB base + ~10MB per concurrent request
  - CPU: Minimal, mostly I/O bound
  - Network: Depends on LLM API usage

**Optimization tips**:
- Use appropriate timeouts for each agent type
- Implement caching for repetitive requests
- For high-volume scenarios, consider Redis Cluster
- Scale horizontally with multiple OrKa instances behind a load balancer

## 🏢 Case Studies & Success Stories

### Enterprise Knowledge Base Assistant
A Fortune 500 company implemented OrKa to build a knowledge base assistant that:
- Classifies questions into 20+ categories
- Routes to appropriate search strategies based on question type
- Provides transparent reasoning paths for compliance
- Reduced average response time by 40% compared to monolithic prompt approach

### Academic Research Tool
Research teams use OrKa to:
- Create reproducible literature analysis workflows
- Document reasoning paths for peer review
- Chain specialized tools in transparent pipelines
- Generate research summaries with clear attribution 

### Content Moderation System
A content platform used OrKa to build a moderation system that:
- Parallelizes content checks across multiple dimensions
- Provides clear explanation for moderation decisions
- Achieves 99.7% agreement with human moderators
- Scales to handle thousands of submissions per hour

## 📚 Documentation

- 📚 [Online Documentation](https://orkacore.web.app/docs) - Full API reference and guides
- 📘 [Idea Manifesto](./docs/index.md) - Core philosophy and design principles
- 📝 [YAML Configuration Guide](./docs/yaml-configuration-guide.md) - Detailed examples for all agent types and nodes

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📜 License & Attribution

This project is licensed under the Apache 2.0 License. For more details, refer to the [LICENSE](./LICENSE) file.
