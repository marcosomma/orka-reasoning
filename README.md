# OrKa-Reasoning

<div align="center">

<img src="https://orkacore.com/assets/ORKA_logo.png" alt="OrKa Logo" width="256" height="256"/>

[![Tests](https://github.com/marcosomma/orka-reasoning/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/marcosomma/orka-reasoning/actions/workflows/tests.yml)
[![codecov](https://codecov.io/github/marcosomma/orka-reasoning/graph/badge.svg?token=V91X4WGBBZ)](https://codecov.io/github/marcosomma/orka-reasoning)

[WEB](https://orkacore.com)
</div>

**Orchestrator Kit for Agentic Reasoning** - OrKa is a modular AI orchestration system that transforms Large Language Models (LLMs) into composable agents capable of reasoning, fact-checking, and constructing answers with transparent traceability.

## 🚀 Features

- **Modular Agent Orchestration**: Define and manage agents using intuitive YAML configurations.
- **Configurable Reasoning Paths**: Utilize Redis streams to set up dynamic reasoning workflows.
- **Comprehensive Logging**: Record and trace every step of the reasoning process for transparency.
- **Built-in Integrations**: Support for OpenAI agents, web search functionalities, routers, and validation mechanisms.
- **Command-Line Interface (CLI)**: Execute YAML-defined workflows with ease.

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

2. **Install Additional Dependencies**:
   ```bash
   pip install fastapi uvicorn
   ```

3. **Start the Services**:
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

### 2. Content Moderation Pipeline

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

### 3. Complex Decision Tree

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

##### DuckDuckGoAgent
- **Purpose**: Perform a real-time web search using DuckDuckGo.
- **Input**: Dict with "input" (the query string).
- **Output**: A list of search result strings.
- **Typical Use**: "Search for latest information about OrKa project."

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
- **Typical Use**: "Wait for parallel validations to finish before deciding next step.""

---

#### 📊 Summary Table

| Name | Type | Core Purpose |
|:---|:---|:---|
| BinaryAgent | Agent | True/False classification |
| ClassificationAgent | Agent | Category classification |
| OpenAIBinaryAgent | Agent | LLM-backed binary decision |
| OpenAIClassificationAgent | Agent | LLM-backed category decision |
| OpenAIAnswerBuilder | Agent | Compose detailed answer |
| DuckDuckGoAgent | Agent | Perform web search |
| RouterNode | Node | Dynamically route next steps |
| FailoverNode | Node | Resilient sequential fallback |
| FailingNode | Node | Simulate failure |
| WaitForNode | Node | Wait for multiple dependencies |
| ForkNode | Node	| Parallel execution split | 
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

📘 [View the Documentation](./docs/index.md)  
📝 [YAML Configuration Guide](./docs/yaml-configuration-guide.md) - Detailed examples for all agent types and nodes

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📜 License & Attribution

This project is licensed under the CC BY-NC 4.0 License. For more details, refer to the [LICENSE](./LICENSE) file.
