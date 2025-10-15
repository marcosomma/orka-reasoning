# Memory Presets - Operation-Based Configuration 🧠

> **Memory configuration templates** - Simplify your memory configuration with preset templates that provide different defaults for read vs write operations

## 🧠 Understanding OrKa Memory Agents

OrKa's memory system uses memory agents (`type: memory`) that can both read from and write to Redis-based memory. These agents handle:

- **Vector embeddings** for semantic search
- **Classification** (short-term vs long-term based on importance factors)
- **Configurable expiration** based on importance multipliers
- **Namespace organization** for logical separation

### Memory Agent Operations

Memory agents support two primary operations:

**📖 Memory Reading (Search & Retrieval)**
```yaml
- id: memory_search
  type: memory
  config:
    operation: read  # Default - searches memory
  namespace: conversations
  params:
    limit: 5
    similarity_threshold: 0.8
  prompt: "Find relevant information about: {{ input }}"
```

**📝 Memory Writing (Storage & Persistence)**  
```yaml
- id: memory_store
  type: memory
  config:
    operation: write  # Stores to memory
  namespace: conversations
  params:
    vector: true  # Enable semantic search
  prompt: "Store this interaction: {{ input }}"
```

## 🎯 Quick Start with Operation-Based Presets

**NEW in v0.9.2**: Presets now provide different default parameters for read vs write operations!

**Instead of manual memory configuration:**

```yaml
# ❌ BEFORE: Manual configuration (multiple parameters per agent)
- id: conversation_memory
  type: memory
  config:
    operation: write
  namespace: conversations
  decay:
    enabled: true
    default_short_term_hours: 24.0
    default_long_term_hours: 168.0
    check_interval_minutes: 60
    memory_type_rules:
      long_term_events: ["success", "completion", "write"]
      short_term_events: ["debug", "processing", "start"]
    importance_rules:
      base_score: 0.5
      event_type_boosts:
        user_interaction: 0.4
        conversation: 0.3
  params:
    vector: true
    # ... 20+ more lines
```

**Use simple, operation-aware presets:**

```yaml
# ✅ AFTER: Operation-aware presets (auto-optimized!)
- id: conversation_reader
  type: memory
  memory_preset: "episodic"  # 🎯 Auto-applies episodic READ defaults!
  config:
    operation: read           # (similarity_threshold=0.6, vector_weight=0.7, etc.)
  namespace: conversations

- id: conversation_writer
  type: memory
  memory_preset: "episodic"  # 🎯 Auto-applies episodic WRITE defaults!
  config:
    operation: write          # (vector=true, optimized indexing, etc.)
  namespace: conversations
```

## 🧠 The 6 Memory Preset Types (Operation-Based)

Memory presets are templates with predefined retention durations and search parameters. Each preset provides different default parameters for read and write operations:

### 1. **Sensory Memory** (`sensory`)
```yaml
memory_preset: "sensory"
```
- **Use for**: Real-time data, sensor input, immediate responses
- **Duration**: 15 minutes (very short-term)
- **Read Defaults**: Fast retrieval (limit=3, similarity_threshold=0.95, no vector search)
- **Write Defaults**: Minimal indexing (vector=false, fast storage)
- **Perfect for**: IoT sensors, stream processing, immediate alerts

### 2. **Working Memory** (`working`)
```yaml
memory_preset: "working"
```
- **Use for**: Session context, temporary calculations, active workflows
- **Duration**: 2 hours short-term, 8 hours max
- **Read Defaults**: Context-aware search (limit=5, similarity_threshold=0.7, context_weight=0.5)
- **Write Defaults**: Session optimization (vector=true, optimized for temporary storage)
- **Perfect for**: User sessions, workflow context, active processing

### 3. **Episodic Memory** (`episodic`)
```yaml
memory_preset: "episodic"
```
- **Use for**: User conversations, interaction history, personal experiences
- **Duration**: 1 day short-term, 1 week long-term
- **Read Defaults**: Conversational context (limit=8, similarity_threshold=0.6, temporal_weight=0.3)
- **Write Defaults**: Rich metadata storage (vector=true, conversation-optimized indexing)
- **Perfect for**: Chatbots, customer service, user interactions

### 4. **Semantic Memory** (`semantic`)
```yaml
memory_preset: "semantic"
```
- **Use for**: Facts, knowledge base, learned information
- **Duration**: 3 days short-term, 90 days long-term
- **Read Defaults**: Knowledge matching (limit=10, similarity_threshold=0.65, no temporal bias)
- **Write Defaults**: Knowledge optimization (vector=true, long-term knowledge indexing)
- **Perfect for**: Knowledge bases, documentation, fact storage

### 5. **Procedural Memory** (`procedural`)
```yaml
memory_preset: "procedural"
```
- **Use for**: Workflows, patterns, skills, process optimization
- **Duration**: 1 week short-term, 6 months long-term
- **Read Defaults**: Pattern recognition (limit=6, similarity_threshold=0.7, minimal temporal bias)
- **Write Defaults**: Process indexing (vector=true, pattern-optimized storage)
- **Perfect for**: Workflow optimization, skill learning, process improvement

### 6. **Meta Memory** (`meta`)
```yaml
memory_preset: "meta"
```
- **Use for**: System behavior, performance metrics, self-reflection
- **Duration**: 2 days short-term, 1 year long-term
- **Read Defaults**: System analysis (limit=4, similarity_threshold=0.8, high precision)
- **Write Defaults**: Performance optimization (vector=true, high-quality indexing)
- **Perfect for**: System monitoring, performance analysis, self-improvement

## 🎯 Operation-Aware Smart Defaults

**NEW in v0.9.2**: Each memory preset automatically provides **different optimized configurations** based on whether you're reading from or writing to memory.

### Read vs Write Operation Defaults

```yaml
# SAME PRESET, DIFFERENT OPERATIONS = DIFFERENT DEFAULTS!

# Reading with episodic preset
- id: memory_search
  type: memory
  memory_preset: "episodic"  # 🎯 Auto-applies READ defaults:
  config:                      #   - limit: 8
    operation: read            #   - similarity_threshold: 0.6
  namespace: conversations     #   - vector_weight: 0.7
                              #   - temporal_weight: 0.3
                              #   - enable_hybrid_search: true

# Writing with same preset
- id: memory_store
  type: memory
  memory_preset: "episodic"  # 🎯 Auto-applies WRITE defaults:
  config:                      #   - vector: true
    operation: write           #   - vector_field_name: "content_vector"
  namespace: conversations     #   - ef_construction: 200
                              #   - optimized indexing params
```

### Operation-Specific Optimization

| Preset | Read Optimization | Write Optimization |
|--------|-------------------|--------------------|
| **sensory** | Fast retrieval, high precision | Minimal indexing, speed focus |
| **working** | Context-aware search, session bias | Session optimization, temporary storage |
| **episodic** | Conversational context, temporal ranking | Rich metadata, conversation indexing |
| **semantic** | Knowledge matching, no time bias | Knowledge optimization, long-term indexing |
| **procedural** | Pattern recognition, skill search | Process indexing, pattern storage |
| **meta** | System analysis, high precision | Performance optimization, quality indexing |

## 🚀 Examples

### Basic Usage

```yaml
orchestrator:
  id: my-assistant
  memory_preset: "episodic"  # Great for conversations
  agents: [...]
```

### Agent-Specific Presets

```yaml
agents:
  - id: conversation_agent
    type: memory
    memory_preset: "episodic"  # Store interactions
    config:
      operation: write
    namespace: conversations
    
  - id: knowledge_agent  
    type: memory
    memory_preset: "semantic"  # Store facts
    config:
      operation: write
    namespace: knowledge
    
  - id: monitor_agent
    type: memory
    memory_preset: "meta"  # System insights
    config:
      operation: write
    namespace: system
```

### Override Specific Settings

```yaml
orchestrator:
  id: my-assistant
  memory_preset: "semantic"  # Use semantic base
  memory_config:
    # Override specific values from preset
    default_long_term_hours: 720  # Extend to 30 days
```

## 📊 Configuration Comparison

| Aspect | Manual Config | Memory Presets |
|--------|---------------|----------------|
| **Lines of code** | 30+ per agent | 1 line |
| **Cognitive meaning** | Technical parameters | Human-understandable |
| **Error-prone** | High (complex nesting) | Low (validated presets) |
| **Maintenance** | Difficult | Easy |
| **Performance** | Manual tuning | Pre-optimized |
| **Learning curve** | Steep | Gentle |

## 🔧 Technical Details

### How It Works

1. **Preset Selection**: Choose from 6 cognitively-inspired presets
2. **Base Configuration**: Preset provides optimized default settings
3. **Custom Overrides**: Override specific settings when needed
4. **Backward Compatibility**: Existing configs continue to work

### Preset Configuration Structure

Each preset includes:
- **Decay rules** (retention periods, cleanup intervals)
- **Importance scoring** (what content matters most)
- **Vector search settings** (semantic similarity thresholds)
- **Namespace organization** (logical memory grouping)

### Implementation

```python
from orka.memory.presets import get_memory_preset, merge_preset_with_config

# Get preset configuration
config = get_memory_preset("episodic")

# Merge with custom settings
final_config = merge_preset_with_config("episodic", {"default_long_term_hours": 240})
```

## 💡 Best Practices

### Choose the Right Preset

| Use Case | Recommended Preset |
|----------|-------------------|
| **Chatbots** | `episodic` |
| **Knowledge Base** | `semantic` |
| **Real-time Processing** | `sensory` |
| **Workflow Optimization** | `procedural` |
| **System Monitoring** | `meta` |
| **Session Management** | `working` |

### Mixing Presets

```yaml
orchestrator:
  memory_preset: "episodic"  # Main orchestrator memory
  
agents:
  - id: facts_extractor
    type: memory
    memory_preset: "semantic"  # Extract and store knowledge
    config:
      operation: write
    namespace: knowledge
    
  - id: conversation_logger
    type: memory
    memory_preset: "episodic"  # Log interactions
    config:
      operation: write
    namespace: conversations
    
  - id: performance_monitor
    type: memory
    memory_preset: "meta"  # Monitor system performance
    config:
      operation: write
    namespace: metrics
```

### Advanced Customization

```yaml
orchestrator:
  memory_preset: "semantic"
  memory_config:
    # Fine-tune the preset
    decay:
      default_long_term_hours: 2160  # 90 days → 90 days (custom)
      importance_rules:
        event_type_boosts:
          validation: 0.4  # Add custom event boost
```

## 🔍 Troubleshooting

### Common Issues

**Q: My preset isn't working**
```bash
# Check if presets are available
python -c "from orka.memory.presets import list_memory_presets; print(list_memory_presets())"
```

**Q: I want to see the actual configuration**
```python
from orka.memory.presets import get_memory_preset
config = get_memory_preset("episodic")
print(json.dumps(config, indent=2))
```

**Q: How do I migrate from manual config?**
1. Identify your use case (conversation, knowledge, etc.)
2. Choose the appropriate preset
3. Test with the preset
4. Add custom overrides if needed
5. Remove the old manual configuration

## 🎯 Migration Guide

### From Complex Config to Presets

**Step 1**: Identify your memory type
```yaml
# If you have conversation/interaction focused config
memory_preset: "episodic"

# If you have knowledge/facts focused config  
memory_preset: "semantic"

# If you have process/workflow focused config
memory_preset: "procedural"
```

**Step 2**: Test the preset
```bash
orka run your-workflow.yml "test input"
```

**Step 3**: Add overrides if needed
```yaml
memory_preset: "episodic"
memory_config:
  # Only override what you need
  default_long_term_hours: 336  # 2 weeks instead of 1
```

**Step 4**: Remove old configuration
```yaml
# ❌ Delete this complex block
# memory_config:
#   decay: { ... 30 lines ... }

# ✅ Keep this simple line
memory_preset: "episodic"
```

## 📚 See Also

- [Memory System Guide](./MEMORY_SYSTEM_GUIDE.md) - Complete memory documentation
- [YAML Configuration Guide](./yaml-configuration-guide.md) - Full YAML reference  
- [Examples](../examples/) - Working examples with presets
- [Getting Started](./getting-started.md) - Quick start guide
