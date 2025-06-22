[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Getting Started with OrKa

Welcome to OrKa! This guide will help you get up and running with OrKa's powerful agent orchestration system in just a few minutes.

## 🚀 Quick Setup

### Prerequisites

- Python 3.8 or higher
- Redis server (for memory backend)
- OpenAI API key

### Installation

```bash
# Install OrKa
pip install orka-reasoning

# Install Redis (choose your platform)
# macOS
brew install redis

# Ubuntu/Debian
sudo apt install redis-server

# Windows (using Docker)
docker run -d -p 6379:6379 redis:alpine

# Start Redis
redis-server
```

### Environment Configuration

```bash
# Create a .env file
cat > .env << EOF
# Required: OpenAI API key
OPENAI_API_KEY=your-openai-api-key-here

# Memory backend configuration
ORKA_MEMORY_BACKEND=redis
REDIS_URL=redis://localhost:6379/0

# Memory decay settings (optional)
ORKA_MEMORY_DECAY_ENABLED=true
ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
EOF

# Load environment variables
source .env  # Linux/macOS
# or set them manually on Windows
```

## 🎯 Your First OrKa Workflow

Let's create a simple but powerful workflow that demonstrates OrKa's memory capabilities:

### Create your first workflow file: `smart-assistant.yml`

```yaml
meta:
  version: "1.0"
  author: "Your Name"
  description: "Smart assistant with memory and learning capabilities"

orchestrator:
  id: smart-assistant
  strategy: sequential
  queue: orka:smart-assistant
  
  # 🧠 Memory configuration - this is what makes OrKa special!
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2      # Conversations fade after 2 hours
      default_long_term_hours: 168     # Important info lasts 1 week
      check_interval_minutes: 30       # Clean up every 30 minutes
      
      # Importance rules - OrKa learns what matters
      importance_rules:
        user_correction: 3.0           # User corrections are very important
        positive_feedback: 2.0         # Learn from positive feedback
        successful_answer: 1.5         # Remember successful interactions
        routine_query: 0.8             # Routine questions decay faster

  agents:
    - conversation_memory
    - context_classifier
    - smart_responder
    - memory_storage

agents:
  # 1. Retrieve relevant conversation history
  - id: conversation_memory
    type: memory-reader
    namespace: conversations
    params:
      limit: 5                         # Get up to 5 relevant memories
      enable_context_search: true      # Use conversation context
      context_weight: 0.4              # Context is 40% of relevance score
      temporal_weight: 0.3             # Recent memories get 30% boost
      similarity_threshold: 0.6        # Minimum relevance threshold
      enable_temporal_ranking: true    # Boost recent interactions
    prompt: |
      Find relevant conversation history for: {{ input }}
      
      Look for:
      - Similar topics we've discussed
      - Previous questions from this user
      - Related context that might be helpful

  # 2. Classify the type of interaction
  - id: context_classifier
    type: openai-classification
    prompt: |
      Based on the conversation history: {{ previous_outputs.conversation_memory }}
      Current user input: {{ input }}
      
      Classify this interaction type:
    options: [new_question, followup, clarification, correction, feedback, greeting, casual_chat]

  # 3. Generate intelligent response using memory
  - id: smart_responder
    type: openai-answer
    prompt: |
      You are a helpful AI assistant with memory of past conversations.
      
      **Conversation History:**
      {{ previous_outputs.conversation_memory }}
      
      **Interaction Type:** {{ previous_outputs.context_classifier }}
      **Current Input:** {{ input }}
      
      Generate a response that:
      1. Acknowledges relevant conversation history when appropriate
      2. Directly addresses the current input
      3. Shows understanding of context and continuity
      4. Is helpful, accurate, and engaging
      
      {% if previous_outputs.context_classifier == "correction" %}
      Pay special attention - the user is correcting something. Learn from this!
      {% elif previous_outputs.context_classifier == "followup" %}
      This is a follow-up question. Build on the previous context.
      {% elif previous_outputs.context_classifier == "feedback" %}
      The user is providing feedback. Acknowledge and learn from it.
      {% endif %}

  # 4. Store the interaction for future reference
  - id: memory_storage
    type: memory-writer
    namespace: conversations
    params:
              # memory_type automatically classified as short-term or long-term
      vector: true                     # Enable semantic search
      metadata:
        interaction_type: "{{ previous_outputs.context_classifier }}"
        has_context: "{{ previous_outputs.conversation_memory | length > 0 }}"
        user_sentiment: "pending"      # Could be analyzed separately
        timestamp: "{{ now() }}"
    prompt: |
      Conversation Record:
      
      User: {{ input }}
      Type: {{ previous_outputs.context_classifier }}
      Context Found: {{ previous_outputs.conversation_memory | length }} previous interactions
      Assistant: {{ previous_outputs.smart_responder }}
      
      Memory Metadata:
      - Interaction type: {{ previous_outputs.context_classifier }}
      - Had relevant history: {{ previous_outputs.conversation_memory | length > 0 }}
      - Response quality: To be evaluated by user feedback
```

### Test Your Smart Assistant

```bash
# Run your first conversation
python -m orka.orka_cli smart-assistant.yml "Hello! I'm new to OrKa. Can you help me understand how it works?"

# Ask a follow-up question
python -m orka.orka_cli smart-assistant.yml "What makes OrKa different from other AI tools?"

# Test memory with a related question
python -m orka.orka_cli smart-assistant.yml "Can you remind me what we were just discussing about OrKa?"
```

**What you'll notice:**
- First interaction: No previous memory, creates new conversation entry
- Second interaction: Builds on previous context about OrKa
- Third interaction: Demonstrates memory recall and contextual awareness

## 🧠 Understanding OrKa's Memory Magic

### What Just Happened?

1. **Memory Retrieval**: OrKa searched for relevant past conversations
2. **Context Classification**: Determined the type of interaction
3. **Intelligent Response**: Generated contextually aware answers
4. **Memory Storage**: Stored the interaction for future reference
5. **Automatic Decay**: Will clean up old conversations automatically

### Memory Lifecycle Visualization

```
New Interaction
       ↓
   Memory Search ──→ [Found: Previous context about OrKa]
       ↓
  Classification ──→ [Type: followup]
       ↓
Response Generation ──→ [Uses context + new input]
       ↓
  Memory Storage ──→ [Stored with metadata]
       ↓
   Decay System ──→ [Auto-cleanup in 2 hours unless important]
```

### Monitor Your Memory

```bash
# Watch memory in real-time
orka memory watch

# View detailed statistics
orka memory stats

# Manual cleanup if needed
orka memory cleanup
```

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
    type: memory-reader
    namespace: chat_history
    params:
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
    type: memory-writer
    namespace: chat_history
    params:
              # memory_type automatically classified based on content and importance
      vector: true
      metadata:
        interaction_type: "chat"
        timestamp: "{{ now() }}"
        response_length: "{{ previous_outputs.response_generator | length }}"
        has_memory_context: "{{ previous_outputs.memory_retrieval | length > 0 }}"
        confidence: "auto_classified"
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

### 4. Advanced Knowledge Base with Self-Learning

```yaml
orchestrator:
  id: learning-knowledge-base
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 24     # Queries are temporary
      default_long_term_hours: 2160    # Knowledge lasts 90 days
      importance_rules:
        verified_fact: 4.0             # Verified facts are very important
        user_correction: 3.5           # User corrections are critical
        frequently_accessed: 2.0       # Popular knowledge stays longer

agents:
  # Step 1: Analyze what type of knowledge request this is
  - id: knowledge_analyzer
    type: openai-classification
    prompt: |
      Analyze this request: {{ input }}
      What type of knowledge interaction is this?
    options: [factual_lookup, how_to_guide, troubleshooting, definition, comparison, update_request]

  # Step 2: Search existing knowledge base
  - id: knowledge_search
    type: memory-reader
    namespace: knowledge_base
    params:
      limit: 15
      enable_context_search: false     # Facts don't need conversation context
      temporal_weight: 0.1             # Facts don't age much
      similarity_threshold: 0.8        # High threshold for accuracy
      memory_type_filter: "long_term"  # Only search established knowledge
      metadata_filters:
        verified: "true"
        confidence: "> 0.7"
    prompt: |
      Search for verified information about: {{ input }}
      Query type: {{ previous_outputs.knowledge_analyzer }}

  # Step 3: Determine if we need to search for new information
  - id: knowledge_freshness_check
    type: openai-binary
    prompt: |
      Existing knowledge: {{ previous_outputs.knowledge_search }}
      New query: {{ input }}
      Query type: {{ previous_outputs.knowledge_analyzer }}
      
      Is the existing knowledge sufficient and current?
      Consider completeness, accuracy, and recency.

  # Step 4: Route based on knowledge assessment
  - id: knowledge_router
    type: router
    params:
      decision_key: knowledge_freshness_check
      routing_map:
        "true": [knowledge_responder, query_logger]
        "false": [web_search, fact_verifier, knowledge_updater, enhanced_responder, query_logger]

  # Step 5a: Search for new information
  - id: web_search
    type: duckduckgo
    prompt: |
      Search for current information about: {{ input }}
      Focus on {{ previous_outputs.knowledge_analyzer }} type content.

  # Step 5b: Verify and structure new information
  - id: fact_verifier
    type: openai-answer
    prompt: |
      Verify this information:
      
      Query: {{ input }}
      Existing Knowledge: {{ previous_outputs.knowledge_search }}
      New Information: {{ previous_outputs.web_search }}
      
      Provide:
      1. Verified facts (confidence 0-100)
      2. Source reliability assessment
      3. What's new vs existing knowledge
      4. Any contradictions found

  # Step 5c: Update knowledge base with verified information
  - id: knowledge_updater
    type: memory-writer
    namespace: knowledge_base
    params:
      memory_type: long_term
      vector: true
      metadata:
        query_type: "{{ previous_outputs.knowledge_analyzer }}"
        confidence: "{{ previous_outputs.fact_verifier.confidence }}"
        verified: "true"
        last_updated: "{{ now() }}"
    decay_config:
      enabled: true
      default_long_term_hours: 2160    # Keep verified knowledge for 90 days
    prompt: |
      Verified Knowledge Entry:
      
      Topic: {{ input }}
      Type: {{ previous_outputs.knowledge_analyzer }}
      Verified Facts: {{ previous_outputs.fact_verifier }}
      Sources: {{ previous_outputs.web_search }}
      Previous Knowledge: {{ previous_outputs.knowledge_search }}

  # Step 5d: Enhanced response with new knowledge
  - id: enhanced_responder
    type: openai-answer
    prompt: |
      Provide a comprehensive answer using:
      
      Query: {{ input }}
      Existing Knowledge: {{ previous_outputs.knowledge_search }}
      New Verified Information: {{ previous_outputs.fact_verifier }}
      
      Integrate old and new information seamlessly.

  # Step 5e: Response from existing knowledge
  - id: knowledge_responder
    type: openai-answer
    prompt: |
      Based on verified knowledge: {{ previous_outputs.knowledge_search }}
      Answer: {{ input }}

  # Step 6: Log analytics
  - id: query_logger
    type: memory-writer
    namespace: analytics
    params:
      memory_type: short_term
      metadata:
        query_type: "{{ previous_outputs.knowledge_analyzer }}"
        knowledge_found: "{{ previous_outputs.knowledge_search | length > 0 }}"
        update_needed: "{{ previous_outputs.knowledge_freshness_check == 'false' }}"
    prompt: |
      Analytics: {{ input }} | Type: {{ previous_outputs.knowledge_analyzer }} | Updated: {{ previous_outputs.knowledge_freshness_check == 'false' }}
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
orka memory watch     # Real-time monitoring
orka memory stats     # Detailed statistics
orka memory cleanup   # Manual cleanup

# Configuration
orka memory configure # View current settings
```

## 🚀 Next Steps

### Explore Advanced Features
- **Fork/Join Patterns**: Parallel processing workflows
- **Router Nodes**: Dynamic workflow routing
- **Failover Nodes**: Resilient error handling
- **Local LLM Integration**: Privacy-preserving processing
- **Memory Namespaces**: Organized memory management

### Learn More
- [YAML Configuration Guide](./yaml-configuration-guide.md) - Complete agent reference
- [Memory System Guide](./MEMORY_SYSTEM_GUIDE.md) - Deep dive into memory
- [Agent Types](./agents.md) - All available agent types
- [Architecture](./architecture.md) - System design principles

### Join the Community
- GitHub: [OrKa Repository](https://github.com/marcosomma/orka-reasoning)
- Documentation: [OrKa Docs](https://orkacore.web.app/docs)
- Examples: [Example Workflows](../examples/)

## 💡 Pro Tips

1. **Start with Memory**: Memory is OrKa's superpower - use it from day one
2. **Use Auto-Classification**: Let OrKa decide short-term vs long-term memory
3. **Monitor Memory Usage**: Use `orka memory watch` during development
4. **Test Incrementally**: Add one agent at a time and test thoroughly
5. **Use Rich Metadata**: Store context that helps future searches
6. **Plan for Scale**: Consider memory decay and cleanup from the start

With this foundation, you're ready to build sophisticated AI agents that learn, remember, and improve over time. OrKa's memory system makes your agents truly intelligent!
