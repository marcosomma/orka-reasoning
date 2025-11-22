# Template Filters and Functions

OrKa provides powerful custom Jinja2 filters and functions for workflow templates, enabling safe access to agent outputs, text manipulation, and complex data extraction.

## Overview

All custom filters are automatically available in your workflow YAML templates. They provide:
- **Safe data access**: Graceful handling of missing or undefined values
- **Agent output retrieval**: Multiple strategies for getting previous agent results
- **Text manipulation**: Truncation, formatting, and cleaning
- **Loop utilities**: Access to past loop data and metadata
- **Debate analysis**: Evolution tracking and synthesis helpers

## Available Filters

### Safe Data Access

#### `safe_get(obj, key, default="")`
Safely access dictionary or object attributes with a default fallback.

**Usage:**
```yaml
prompt: "Status: {{ loop_data | safe_get('status', 'unknown') }}"
prompt: "Score: {{ result | safe_get('confidence', 0.0) }}"
```

**Parameters:**
- `obj`: Dictionary or object to access
- `key`: Key name to retrieve
- `default`: Fallback value if key is missing (default: empty string)

**Returns:** Value at key, or default if not found

---

#### `safe_get_response(agent_id, default="No response available")`
Get an agent's response from previous_outputs with multiple fallback strategies.

**Usage:**
```yaml
prompt: "Previous analysis: {{ safe_get_response('analysis_agent', 'No analysis yet') }}"
prompt: "Synthesis: {{ safe_get_response('synthesis_attempt', 'No synthesis') }}"
```

**Parameters:**
- `agent_id`: ID of the agent whose response to retrieve
- `default`: Fallback value if agent response not found

**Returns:** Agent's response text, checking multiple field names ('response', 'result', 'output')

**Note:** This filter handles nested structures from LoopNode and other wrapper agents automatically.

---

#### `get_agent_response(agent_id)`
Strict version of response getter - returns empty string on failure instead of fallback message.

**Usage:**
```yaml
prompt: "{{ get_agent_response('radical_progressive') }}"
```

**Parameters:**
- `agent_id`: ID of the agent whose response to retrieve

**Returns:** Agent's response or empty string if not found

---

### Text Manipulation

#### `truncate(text, length=100, suffix="...")`
Truncate text to specified length with optional suffix.

**Usage:**
```yaml
prompt: "Summary: {{ long_response | truncate(200) }}"
prompt: "{{ get_agent_response('verbose_agent') | truncate(150, '…') }}"
```

**Parameters:**
- `text`: Text to truncate
- `length`: Maximum character length (default: 100)
- `suffix`: String to append when truncated (default: "...")

**Returns:** Truncated text with suffix if needed

**Use Cases:**
- Token budget management
- Prompt length optimization
- Display formatting

---

### Loop and History Access

#### `format_loop_metadata(past_loops, max_loops=5)`
Format past loop history as human-readable string.

**Usage:**
```yaml
prompt: |
  Past debate rounds:
  {{ past_loops | format_loop_metadata(3) }}
```

**Parameters:**
- `past_loops`: List of loop iteration data
- `max_loops`: Maximum number of loops to display (default: 5)

**Returns:** Formatted string showing loop progression

---

#### `get_debate_evolution(past_loops)`
Analyze debate progression and generate evolution summary.

**Usage:**
```yaml
prompt: |
  Debate evolution: {{ past_loops | get_debate_evolution }}
  
  Current round: Focus on...
```

**Parameters:**
- `past_loops`: List of loop iteration data with score fields

**Returns:** Summary of debate trends (improving/declining/stable)

---

## Available Functions

These functions are available directly in templates (no pipe `|` needed).

### Input Access

#### `get_input()`
Get the main input string, handling nested structures.

**Usage:**
```yaml
prompt: "Analyze: {{ get_input() }}"
```

**Returns:** Main workflow input text

---

#### `get_current_topic()`
Alias for `get_input()` - more semantic for debate/discussion workflows.

**Usage:**
```yaml
prompt: "Current discussion topic: {{ get_current_topic() }}"
```

---

### Loop Metadata

#### `get_loop_number()`
Get current loop iteration number.

**Usage:**
```yaml
prompt: "Round {{ get_loop_number() }} of debate"
```

**Returns:** Integer loop counter (1-indexed)

---

#### `has_past_loops()`
Check if previous loop iterations exist.

**Usage:**
```yaml
prompt: |
  {% if has_past_loops() %}
    Building on previous rounds...
  {% else %}
    Starting fresh debate...
  {% endif %}
```

**Returns:** Boolean

---

#### `get_past_loops()`
Get list of all past loop iterations.

**Usage:**
```yaml
prompt: |
  {% for loop in get_past_loops() %}
    Round {{ loop.round }}: Score {{ loop.score }}
  {% endfor %}
```

**Returns:** List of loop iteration dictionaries

---

#### `get_past_insights()`
Extract insights from the last loop iteration.

**Usage:**
```yaml
prompt: |
  Previous insights:
  {{ get_past_insights() }}
```

**Returns:** Synthesis insights from last loop

---

#### `get_loop_rounds()`
Get number of completed loop rounds.

**Usage:**
```yaml
prompt: "After {{ get_loop_rounds() }} rounds of discussion..."
```

**Returns:** Integer count or "Unknown"

---

#### `get_final_score()`
Get final score from loop validation.

**Usage:**
```yaml
prompt: "Final agreement score: {{ get_final_score() }}"
```

**Returns:** Float score or "Unknown"

---

### Fork/Join Utilities

#### `get_fork_responses(fork_group_name)`
Get all responses from a fork group execution.

**Usage:**
```yaml
prompt: |
  Perspectives:
  {% for agent_id, response in get_fork_responses('debate_perspectives').items() %}
    - {{ agent_id }}: {{ response }}
  {% endfor %}
```

**Parameters:**
- `fork_group_name`: Name of the fork group

**Returns:** Dictionary mapping agent IDs to responses

---

#### `joined_results()`
Get joined results from fork operations.

**Usage:**
```yaml
prompt: "Combined analysis: {{ joined_results() }}"
```

**Returns:** List of joined results

---

### Perspective-Specific Helpers

For cognitive_society workflows, these helpers provide quick access to common agent types:

#### `get_progressive_response()`
Get response from progressive/radical perspective agent.

**Usage:**
```yaml
prompt: "Progressive view: {{ get_progressive_response() }}"
```

---

#### `get_conservative_response()`
Get response from conservative/traditional perspective agent.

---

#### `get_realist_response()`
Get response from pragmatic/realist perspective agent.

---

#### `get_purist_response()`
Get response from ethical/purist perspective agent.

---

#### `get_collaborative_responses()`
Get all collaborative refinement responses formatted as string.

**Usage:**
```yaml
prompt: |
  Collaborative perspectives:
  {{ get_collaborative_responses() }}
```

**Returns:** Formatted multi-line string with all perspectives

---

### Memory and Context

#### `format_memory_query(perspective, topic=None)`
Format a memory query for a specific perspective.

**Usage:**
```yaml
prompt: "{{ format_memory_query('progressive') }}"
prompt: "{{ format_memory_query('conservative', get_input()) }}"
```

**Parameters:**
- `perspective`: Perspective name (e.g., 'progressive', 'realist')
- `topic`: Optional topic override (defaults to main input)

**Returns:** Formatted memory query string

---

#### `get_my_past_memory(agent_type)`
Get past memory entries for a specific agent type.

**Usage:**
```yaml
prompt: |
  My past thoughts:
  {{ get_my_past_memory('progressive') }}
```

**Parameters:**
- `agent_type`: Agent type identifier

**Returns:** Recent memory entries (last 3)

---

#### `get_my_past_decisions(agent_name)`
Get past loop decisions for a specific agent.

**Usage:**
```yaml
prompt: |
  My evolution:
  {{ get_my_past_decisions('radical_progressive') }}
```

**Parameters:**
- `agent_name`: Specific agent ID

**Returns:** Recent decisions (last 2 loops)

---

#### `get_agent_memory_context(agent_type, agent_name)`
Get comprehensive context including memory and decisions.

**Usage:**
```yaml
prompt: |
  Full context:
  {{ get_agent_memory_context('progressive', 'radical_progressive') }}
```

**Returns:** Combined memory and decision history

---

## Complex Workflow Examples

### Cognitive Society Pattern

```yaml
agents:
  - id: progressive_refinement
    type: openai-gpt-4o-mini
    prompt: |
      Topic: {{ get_input() }}
      
      {% if has_past_loops() %}
      Previous progressive stance:
      {{ get_my_past_decisions('radical_progressive') }}
      
      Other perspectives:
      - Conservative: {{ safe_get_response('traditional_conservative', 'No view yet') | truncate(150) }}
      - Realist: {{ safe_get_response('pragmatic_realist', 'No view yet') | truncate(150) }}
      
      Debate evolution: {{ get_debate_evolution(get_past_loops()) }}
      {% endif %}
      
      Provide your refined progressive perspective.
```

### Loop with Synthesis

```yaml
agents:
  - id: final_synthesis_processor
    type: openai-gpt-4o-mini
    prompt: |
      === COGNITIVE SOCIETY DEBATE SYNTHESIS ===
      
      Topic: {{ get_current_topic() }}
      Rounds completed: {{ get_loop_rounds() }}
      Final score: {{ get_final_score() }}
      
      Last insights:
      {{ get_past_insights() | truncate(300) }}
      
      Collaborative perspectives:
      {{ get_collaborative_responses() }}
      
      Generate final balanced synthesis.
```

### Fork Group Processing

```yaml
agents:
  - id: synthesis_agent
    type: openai-gpt-4o-mini
    prompt: |
      Synthesize these parallel analyses:
      
      {% for agent_id, response in get_fork_responses('parallel_analysis').items() %}
      **{{ agent_id }}**: {{ response | truncate(200) }}
      {% endfor %}
```

## Best Practices

### 1. Always Use Safe Accessors
❌ **Bad:**
```yaml
prompt: "Score: {{ previous_outputs.validator.result.score }}"
```

✅ **Good:**
```yaml
prompt: "Score: {{ safe_get_response('validator') | safe_get('score', 'Unknown') }}"
```

### 2. Truncate Long Outputs for Token Efficiency
```yaml
# Good for token budget management
prompt: "Summary: {{ get_agent_response('verbose_analyzer') | truncate(200) }}"
```

### 3. Provide Meaningful Defaults
```yaml
# Helps debugging when things go wrong
prompt: "Analysis: {{ safe_get_response('analyzer', 'Analysis not yet available') }}"
```

### 4. Use Conditional Logic for Optional Data
```yaml
prompt: |
  {% if has_past_loops() %}
    Building on {{ get_loop_rounds() }} previous rounds...
  {% else %}
    First round - establishing baseline...
  {% endif %}
```

### 5. Chain Filters for Complex Transformations
```yaml
# Safe access + truncation + formatting
prompt: "{{ safe_get_response('agent1', 'N/A') | truncate(150) }}"
```

## Debugging Template Issues

If you encounter "unknown" values or template errors:

1. **Check agent IDs match exactly** - case-sensitive
2. **Verify agent has executed** - use conditional checks
3. **Use safe accessors** - prevent KeyError exceptions
4. **Enable verbose logging** - see template rendering details

```bash
# Run with debug logging
orka run workflow.yml "input" --verbose
```

## Migration from Legacy Templates

If upgrading from older OrKa versions without custom filters:

**Old Pattern:**
```yaml
prompt: "{{ previous_outputs.agent1.result }}"
```

**New Pattern:**
```yaml
prompt: "{{ safe_get_response('agent1') }}"
```

**Benefits:**
- Handles missing agents gracefully
- Works with nested structures (LoopNode, etc.)
- Supports multiple response field names
- Provides meaningful fallback values

## Technical Notes

- Filters are registered via `SimplifiedPromptRenderer`
- Available in all workflow YAML templates automatically
- Implemented in `orka/orchestrator/template_helpers.py`
- Jinja2 Environment created per render with filters attached
- Performance impact minimal (filters cached in Environment)

## See Also

- [Agents Guide](agents.md) - Agent configuration and types
- [Workflow Configuration](CONFIGURATION.md) - YAML workflow structure
- [Memory System Guide](MEMORY_SYSTEM_GUIDE.md) - Memory agent integration
- [Loop Nodes](agents-advanced.md#loop-node) - Loop execution patterns
