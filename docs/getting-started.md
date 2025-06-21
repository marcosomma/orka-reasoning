[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Getting Started with OrKa

Welcome to OrKa! This guide will help you get up and running with the Orchestrator Kit for Agentic Reasoning in just a few minutes.

## 🚀 Quick Start (5 Minutes)

### 1. Installation

```bash
# Install OrKa
pip install orka-reasoning

# Install additional dependencies for web interface
pip install fastapi uvicorn
```

### 2. Set Environment Variables

```bash
# Required for OpenAI agents
export OPENAI_API_KEY=your-openai-api-key-here

# Optional: For local LLM support
export OLLAMA_HOST=http://localhost:11434
```

### 3. Create Your First Workflow

Create a file called `my-first-workflow.yml`:

```yaml
meta:
  version: "1.0"
  author: "Getting Started"
  description: "My first OrKa workflow"

orchestrator:
  id: hello-orka
  strategy: sequential
  queue: orka:hello

agents:
  - id: classifier
    type: openai-classification
    prompt: "Classify this as a [question, statement, request]"
    options: [question, statement, request]
    queue: orka:classify

  - id: responder
    type: openai-answer
    prompt: |
      Type: {{ previous_outputs.classifier }}
      Input: {{ input }}
      
      Provide an appropriate response based on the type.
    queue: orka:respond
```

### 4. Run Your Workflow

```bash
# Start OrKa services (Redis + FastAPI server)
python -m orka.orka_start

# In another terminal, run your workflow
python -m orka.orka_cli ./my-first-workflow.yml "What is artificial intelligence?"
```

## 🎯 Core Concepts

### Agents
**Agents** are processing units that perform specific tasks:
- **Classification**: Categorize input
- **Answer Building**: Generate responses
- **Memory Operations**: Store and retrieve information
- **Search**: Find external information

### Orchestrator
The **Orchestrator** manages the flow between agents:
- **Sequential**: Agents run one after another
- **Parallel**: Multiple agents run simultaneously
- **Decision Trees**: Dynamic routing based on results

### Memory System
OrKa includes intelligent memory management:
- **Context-Aware Search**: Find relevant past information
- **Automatic Decay**: Smart memory lifecycle management
- **Vector Embeddings**: Semantic similarity matching

## 📚 Examples by Use Case

### 1. Question Answering System

```yaml
orchestrator:
  id: qa-system
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168

agents:
  - id: question_analyzer
    type: openai-classification
    prompt: "What type of question is this?"
    options: [factual, opinion, how_to, troubleshooting]
    
  - id: search_needed
    type: openai-binary
    prompt: "Does this question require recent information? True/False"
    
  - id: router
    type: router
    params:
      decision_key: search_needed
      routing_map:
        "true": [web_search, answer_with_sources]
        "false": [answer_from_knowledge]
        
  - id: web_search
    type: duckduckgo
    prompt: "Search for: {{ input }}"
    
  - id: answer_with_sources
    type: openai-answer
    prompt: |
      Question: {{ input }}
      Type: {{ previous_outputs.question_analyzer }}
      Search Results: {{ previous_outputs.web_search }}
      
      Provide a comprehensive answer with source citations.
      
  - id: answer_from_knowledge
    type: openai-answer
    prompt: |
      Question: {{ input }}
      Type: {{ previous_outputs.question_analyzer }}
      
      Answer based on your training knowledge.
```

### 2. Memory-Enhanced Chat System

```yaml
orchestrator:
  id: chat-system
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 1
      default_long_term_hours: 72

agents:
  - id: memory_retrieval
    type: memory
    namespace: chat_history
    config:
      operation: read
      limit: 5
      enable_context_search: true
      temporal_weight: 0.3
    prompt: "Find relevant conversation history for: {{ input }}"
    
  - id: response_generator
    type: openai-answer
    prompt: |
      Current message: {{ input }}
      Conversation history: {{ previous_outputs.memory_retrieval }}
      
      Generate a contextually aware response.
      
  - id: memory_storage
    type: memory
    namespace: chat_history
    config:
      operation: write
      memory_type: auto
      vector: true
    prompt: |
      User: {{ input }}
      Assistant: {{ previous_outputs.response_generator }}
```

### 3. Local LLM Processing

```yaml
orchestrator:
  id: local-processing
  strategy: sequential

agents:
  - id: privacy_classifier
    type: local_llm
    model: "llama3.2:latest"
    model_url: "http://localhost:11434/api/generate"
    provider: "ollama"
    prompt: |
      Classify this content as [public, internal, confidential]:
      {{ input }}
      
  - id: local_processor
    type: local_llm
    model: "mistral:latest"
    model_url: "http://localhost:11434/api/generate"
    provider: "ollama"
    temperature: 0.7
    prompt: |
      Content classification: {{ previous_outputs.privacy_classifier }}
      
      Process this content appropriately: {{ input }}
```

## 🛠️ Development Workflow

### 1. Plan Your Agents
- Identify the tasks your workflow needs
- Choose appropriate agent types
- Plan the data flow between agents

### 2. Start Simple
- Begin with 2-3 agents
- Test each agent individually
- Gradually add complexity

### 3. Test and Debug
```bash
# Run with detailed logging
python -m orka.orka_cli ./workflow.yml "test input" --log-to-file --verbose

# Check Redis logs for debugging
redis-cli xrevrange orka:your_agent_id + - COUNT 5
```

### 4. Monitor and Optimize
```bash
# Real-time memory monitoring
orka memory watch

# View memory statistics
orka memory stats

# Manual memory cleanup
orka memory cleanup
```

## 🔧 Configuration Tips

### Environment Setup
```bash
# Create a .env file for your project
cat > .env << EOF
OPENAI_API_KEY=your-key-here
REDIS_URL=redis://localhost:6379
OLLAMA_HOST=http://localhost:11434
EOF
```

### YAML Best Practices
- Use descriptive agent IDs
- Include helpful comments
- Set appropriate timeouts
- Plan for error handling with failover agents

### Memory Management
- Use appropriate memory types (short_term vs long_term)
- Configure decay rules for your use case
- Enable vector search for semantic matching
- Monitor memory usage regularly

## 🎮 Interactive Development

### OrKa UI
Access the web interface at `http://localhost:8080` to:
- Visualize workflow execution
- Monitor agent performance
- Debug failed executions
- Manage memory contents

### CLI Commands
```bash
# Run a workflow
orka run ./workflow.yml "your input"

# Memory management
orka memory stats
orka memory watch
orka memory cleanup

# Service management
orka start  # Start all services
orka stop   # Stop all services
```

## 🚀 Next Steps

1. **Explore Examples**: Check the `/examples` directory
2. **Read Agent Documentation**: See [Agent Types](./agents.md)
3. **Advanced Configuration**: Review [YAML Configuration Guide](./yaml-configuration-guide.md)
4. **Architecture Deep Dive**: Understand the [Architecture](./architecture.md)
5. **Extend OrKa**: Learn about [Extending Agents](./extending-agents.md)

## 🆘 Getting Help

- **Documentation**: Browse all guides in the `/docs` directory
- **Examples**: Check practical examples in `/examples`
- **Issues**: Report bugs on GitHub
- **Community**: Join discussions on our community channels

Happy orchestrating! 🎭
