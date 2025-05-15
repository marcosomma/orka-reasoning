[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# YAML Configuration Guide for OrKa

This guide provides detailed examples and patterns for configuring different types of agents, nodes, and tools in your OrKa YAML configuration.

## Basic Structure

Every OrKa YAML file has the same basic structure:

```yaml
meta:
  version: "1.0"
  author: "Your Name"
  description: "Short description of what this flow does"

orchestrator:
  id: my_orchestrator
  strategy: sequential  # or "parallel" for fork/join flows
  queue: orka:main

agents:
  # List of agent configurations
  - id: agent1
    type: binary
    # agent-specific configuration
  - id: agent2
    type: classification
    # agent-specific configuration
```

## Core Agent Types

### Binary Agent

Returns `"true"` or `"false"` based on a question or statement.

```yaml
- id: is_relevant
  type: binary
  prompt: >
    Is the following statement relevant to cybersecurity? 
    Return TRUE if it is, or FALSE if it is not.
  queue: orka:relevance_check
  timeout: 15.0  # optional timeout in seconds
  max_concurrency: 5  # optional concurrency limit
```

### Classification Agent

Returns one option from a list of predefined options.

```yaml
- id: topic_classifier
  type: classification
  prompt: >
    Classify the following text into one of these categories.
    Respond with exactly one category.
  options: [technology, science, politics, entertainment, sports]
  queue: orka:classify
  timeout: 20.0
```

### Search Agent (DuckDuckGo)

Searches the web and returns snippets.

```yaml
- id: web_search
  type: duckduckgo
  prompt: Search for information about the following query
  queue: orka:search
  timeout: 60.0  # searches may take longer
  max_concurrency: 3  # limit concurrent searches
  params:
    max_results: 5  # optional: limit number of results
    region: "us-en"  # optional: search region
```

### Search Agent (Google)

```yaml
- id: google_search
  type: google-search
  prompt: Search for information about the following query
  queue: orka:google
  params:
    api_key: "${GOOGLE_API_KEY}"  # environment variable
    cse_id: "${GOOGLE_CSE_ID}"
    max_results: 5
```

## Flow Control Nodes

### Router Node

Dynamically routes execution based on previous outputs.

```yaml
- id: search_router
  type: router
  params:
    decision_key: requires_search  # key from previous output
    routing_map:
      "true": [web_search, fact_validator]  # if requires_search is "true"
      "false": [fact_validator]  # if requires_search is "false"
```

### Fork Node

Splits execution into parallel branches.

```yaml
- id: parallel_analysis
  type: fork
  targets:
    - [sentiment_analysis, sentiment_summarizer]  # Branch 1
    - [topic_analysis, topic_validator]  # Branch 2
    - [entity_extraction]  # Branch 3
```

### Join Node

Waits for parallel branches to complete before continuing.

```yaml
- id: join_analysis
  type: join
  group: parallel_analysis  # References the fork node ID
```

### Failover Node

Tries multiple agents in sequence until one succeeds.

```yaml
- id: search_with_fallback
  type: failover
  children:
    - id: primary_search
      type: duckduckgo
      prompt: Search for information about the input
      queue: orka:primary_search
    - id: backup_search
      type: google-search
      prompt: Search for information about the input
      queue: orka:backup_search
    - id: fallback_text
      type: static-response
      value: "No search results available."
      queue: orka:fallback
```

## Builder Agents

Compile final outputs using data from previous agents.

```yaml
- id: final_answer
  type: openai-answer
  prompt: |
    Build a comprehensive answer using the following information:
    - Topic classification: {{ previous_outputs.topic_classifier }}
    - Relevant facts: {{ previous_outputs.fact_validator }}
    - Research findings: {{ previous_outputs.web_search }}
  queue: orka:final_answer
  timeout: 45.0
```

## LLM Agent Configuration

```yaml
- id: expert_analysis
  type: openai-agent  # or anthropic-agent, or other LLM provider
  prompt: >
    You are an expert analyst. Analyze the following information
    and provide deep insights.
  queue: orka:analysis
  params:
    model: "gpt-4"  # or claude-3-opus, etc.
    temperature: 0.7
    max_tokens: 1000
```

## Templating in Prompts

OrKa supports Jinja2-style templating in prompts:

```yaml
- id: context_aware_classifier
  type: classification
  prompt: >
    Given the topic "{{ previous_outputs.topic }}", 
    classify the sentiment of the following text.
  options: [positive, neutral, negative]
  queue: orka:sentiment
```

## Advanced Configuration

### Environment Variable Substitution

```yaml
- id: api_agent
  type: api-call
  queue: orka:api
  params:
    api_key: "${API_KEY}"  # Will be replaced with environment variable
    endpoint: "https://api.example.com"
```

### Conditional Execution

```yaml
- id: conditional_agent
  type: conditional
  condition: "{{ previous_outputs.needs_detail == 'true' }}"
  if_true:
    id: detailed_analysis
    type: openai-agent
    prompt: Provide detailed analysis
    queue: orka:detail
  if_false:
    id: summary
    type: openai-agent
    prompt: Provide a brief summary
    queue: orka:summary
```

## OpenAI Agent Configuration

### OpenAI Answer Builder

```yaml
- id: research_question
  type: openai-answer
  prompt: |
    Generate a detailed answer to the following question:
    "{{ input }}"
    
    Include all relevant information and cite sources where appropriate.
  queue: orka:research_answers
  model: gpt-4
  temperature: 0.7
  
### OpenAI Binary Agent

```yaml
- id: is_medical_question
  type: openai-binary
  prompt: |
    Determine if the following is a medical question:
    "{{ input }}"
    
    Return ONLY true or false.
  queue: orka:binary_medical_filter
  model: gpt-3.5-turbo
  temperature: 0.2
```

### OpenAI Classification Agent

```yaml
- id: categorize_request
  type: openai-classification
  prompt: |
    Classify the following user request into exactly one of these categories:
    "{{ input }}"
  options:
    - technical_support
    - account_related
    - billing_question
    - feature_request
    - bug_report
    - general_inquiry
  queue: orka:request_categorizer
  model: gpt-3.5-turbo
  temperature: 0.3
```

### Configuration Parameters

| Parameter     | Description                                | Default        | Required |
|---------------|--------------------------------------------|--------------  |----------|
| model         | OpenAI model to use                        | gpt-3.5-turbo  | No       |
| temperature   | Randomness of output (0.0-1.0)             | 1.0            | No       |
| prompt        | Template for request to the model          | -              | Yes      |
| options       | List of choices (for classification only)  | -              | For classification |

## Complete Example

```yaml
meta:
  version: "1.0"
  description: "Research assistant flow"

orchestrator:
  id: research_orchestrator
  strategy: parallel
  queue: orka:research

agents:
  - id: query_analyzer
    type: classification
    prompt: >
      Classify this query into one of: [factual, opinion, advice].
      Return exactly one category.
    options: [factual, opinion, advice]
    queue: orka:classify
    timeout: 20.0

  - id: search_needed
    type: binary
    prompt: >
      Does this query require internet search to answer accurately?
      Return TRUE or FALSE.
    queue: orka:search_check
    timeout: 15.0

  - id: router_node
    type: router
    params:
      decision_key: search_needed
      routing_map:
        "true": [web_search, answer_builder]
        "false": [answer_builder]

  - id: web_search
    type: duckduckgo
    prompt: Search for information about this query
    queue: orka:search
    timeout: 60.0
    max_concurrency: 3

  - id: answer_builder
    type: openai-answer
    prompt: |
      Build a comprehensive answer for this query.
      Query type: {{ previous_outputs.query_analyzer }}
      {% if previous_outputs.search_needed == "true" %}
      Search results: {{ previous_outputs.web_search }}
      {% endif %}
    queue: orka:final_answer
    timeout: 45.0
    max_concurrency: 5
```

## Best Practices

1. **Use Descriptive IDs**: Choose clear, descriptive names for your agent IDs
2. **Set Appropriate Timeouts**: Longer for complex reasoning, shorter for simple tasks
3. **Limit Concurrency**: Especially for agents that access external resources
4. **Use Templating**: Reference previous outputs to build context
5. **Handle Failures**: Use failover nodes and fallbacks for critical paths
6. **Structure Prompts**: Use clear instructions and formatting in prompts

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md) 