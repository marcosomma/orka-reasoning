# OrKa UI - Visual Workflow Builder

> **Last Updated:** 29 November 2025  
> **Version:** 0.9.6  
> **Status:** 🟢 Current  
> **Related:** [Getting Started](getting-started.md) | [YAML Configuration](YAML_CONFIGURATION.md) | [Architecture](architecture.md)

OrKa UI is a visual drag-and-drop interface for building complex AI agent workflows without writing YAML by hand. It provides an intuitive canvas where you can design, test, and export OrKa workflows visually.

---

## 📋 Table of Contents

- [What is OrKa UI?](#what-is-orka-ui)
- [Why Use OrKa UI?](#why-use-orka-ui)
- [Key Features](#key-features)
- [Installation & Setup](#installation--setup)
  - [Using Docker (Recommended)](#using-docker-recommended)
  - [Building from Source](#building-from-source)
- [Quick Start Tutorial](#quick-start-tutorial)
- [Core Concepts](#core-concepts)
- [Agent Types](#agent-types)
- [Configuration](#configuration)
- [Integration with OrKa Core](#integration-with-orka-core)
- [Troubleshooting](#troubleshooting)

---

## What is OrKa UI?

OrKa UI is a **browser-based visual editor** that transforms the complexity of YAML workflow configuration into an interactive drag-and-drop experience. Instead of manually editing YAML files, you:

1. **Drag** agents and control flow nodes onto a canvas
2. **Connect** them with visual links to define execution order
3. **Configure** each node's properties in a sidebar panel
4. **Generate** production-ready YAML with one click
5. **Execute** workflows directly from the UI

Think of it as a **visual programming environment** for AI agent orchestration, similar to Node-RED but specifically designed for LLM-powered workflows with memory, routing, and advanced control flow.

---

## Why Use OrKa UI?

### Problems It Solves

**Without OrKa UI:**
- ❌ Hand-writing complex YAML files prone to syntax errors
- ❌ Difficult to visualize agent dependencies and flow
- ❌ No live validation of connections and configurations
- ❌ Hard to debug workflow structure
- ❌ Steep learning curve for new team members

**With OrKa UI:**
- ✅ Visual canvas with drag-and-drop node placement
- ✅ Real-time connection validation with helpful hints
- ✅ Automatic YAML generation from visual graph
- ✅ Live workflow execution and testing
- ✅ Example workflows to learn from
- ✅ Built-in documentation and tooltips

---

## Key Features

### 🎨 Visual Workflow Builder
- **Drag-and-drop interface**: Add agents, routers, loops, memory nodes, and control flow
- **Smart connections**: Visual links with real-time validation
- **Node categories**: Agents grouped by functionality (LLM, Memory, Control Flow, Search)
- **Canvas navigation**: Pan, zoom, fit-to-view controls

### 🔧 Configuration Panel
- **Property editor**: Configure agent parameters, prompts, models, and settings
- **Loop configuration**: Visual editor for loop paths, scoring, and cognitive extraction
- **Memory presets**: Select from semantic, episodic, working, and procedural memory types
- **Template support**: Jinja2 syntax highlighting for prompt templates

### 📤 YAML Generation & Import
- **One-click export**: Generate production-ready YAML from visual graph
- **Import workflows**: Load existing YAML files for visualization and editing
- **Example library**: Pre-built workflows for common patterns (fork/join, routing, loops, memory)
- **Validation**: Real-time schema validation with error highlighting

### 🚀 Execution & Testing
- **Live execution**: Run workflows directly from the UI
- **Input/output panels**: Test with custom inputs and view results
- **Execution tracing**: Monitor agent execution order and outputs
- **Error handling**: Visual feedback for workflow errors

### 🎯 Advanced Features
- **GraphScout support**: Intelligent path discovery with budget controls
- **Floating panels**: Draggable, resizable panels for workspace organization
- **Guided tour**: Interactive walkthrough for new users
- **Workspace presets**: Save and load common panel layouts

---

## Installation & Setup

### Option 1: Automatic Start with `orka-start` (Recommended)

The **easiest way** to use OrKa UI is through the `orka-start` command, which automatically sets up everything you need:

```bash
# Install OrKa if you haven't already
pip install orka-reasoning

# Start Redis, Backend, and UI all at once
orka-start
```

**What this does:**
1. ✅ Starts **RedisStack** (memory backend)
2. ✅ Starts **OrKa Backend API** (port 8000)
3. ✅ Starts **OrKa UI** (port 8080) - if Docker is available
4. ✅ Automatically pulls the latest UI Docker image

**Access the UI:**
```
http://localhost:8080
```

**Configuration Options:**
```bash
# Skip Docker image pull for faster startup (uses cached version)
export ORKA_UI_SKIP_PULL=true
orka-start

# Disable UI completely (Redis + Backend only)
export ORKA_DISABLE_UI=true
orka-start

# Custom API URL
export ORKA_API_URL=http://custom-host:8000
orka-start

# Windows PowerShell:
$env:ORKA_UI_SKIP_PULL="true"
$env:ORKA_DISABLE_UI="true"
orka-start
```

### Option 2: Manual Docker Setup

If you prefer to run the UI container manually or need custom configuration:

#### Prerequisites
- Docker installed and running
- OrKa backend running (optional, for execution)

#### Step 1: Pull the Image
```bash
docker pull marcosomma/orka-ui:latest
```

#### Step 2: Run the Container
```bash
docker run -d \
  -p 8080:80 \
  -e VITE_API_URL_LOCAL=http://localhost:8000/api/run@dist \
  --name orka-ui \
  marcosomma/orka-ui:latest
```

#### Step 3: Access the UI
Open your browser and navigate to:
```
http://localhost:8080
```

### Manual Configuration Options

When running the UI container manually, you can customize its behavior:

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL_LOCAL` | OrKa backend API endpoint | `http://localhost:8000/api/run@dist` |

#### Custom API URL Example
```bash
docker run -d \
  -p 8080:80 \
  -e VITE_API_URL_LOCAL=https://your-api-domain.com/api/run@dist \
  --name orka-ui \
  marcosomma/orka-ui:latest
```

#### Port Mapping
Change the host port (left side) to use a different port:
```bash
# Use port 3000 instead of 8080
docker run -d \
  -p 3000:80 \
  -e VITE_API_URL_LOCAL=http://localhost:8000/api/run@dist \
  --name orka-ui \
  marcosomma/orka-ui:latest
```

> **💡 Tip:** When using `orka-start`, the UI is automatically configured with the correct API URL and port mappings. Manual configuration is only needed if you're running the UI separately.

### Option 3: Building from Source

For developers who want to customize the UI or contribute to development:

#### Prerequisites
- Node.js 18+ and npm
- Git

#### Step 1: Clone the Repository
```bash
git clone https://github.com/marcosomma/orka-ui-ts.git
cd orka-ui-ts
```

#### Step 2: Install Dependencies
```bash
npm install
```

#### Step 3: Run Development Server
```bash
npm run dev
```

The UI will be available at `http://localhost:5173`

#### Step 4: Build for Production
```bash
npm run build
```

#### Step 5: Build Docker Image (Optional)
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-registry/orka-ui:latest \
  --push .
```

---

## Quick Start Tutorial

### 1. Launch OrKa UI

Open `http://localhost:8080` in your browser. You'll see:
- **Header**: OrKa logo, workspace selector, panel toggles
- **Node Palette** (left): Available agent types grouped by category
- **Canvas** (center): Visual workspace for building workflows
- **Properties Panel** (right): Configuration for selected nodes
- **YAML Panel** (bottom): Generated YAML preview
- **Execution Panel**: Input/output for testing workflows

### 2. Create Your First Workflow

#### Example: Simple Question-Answer Pipeline

**Step 1: Add a Search Agent**
1. Click **Node Palette** → **SEARCH & RETRIEVAL** → **DuckDuckGo**
2. A green `duckduckgo` node appears on the canvas
3. Click the node to select it
4. In the **Properties Panel**, configure:
   - **ID**: `search_agent`
   - **Prompt**: `{{ input }}`

**Step 2: Add an LLM Agent**
1. Click **Node Palette** → **LLM INTEGRATION** → **Local LLM**
2. A purple `local_llm` node appears
3. Drag it to the right of the search agent
4. Configure properties:
   - **ID**: `answer_agent`
   - **Model**: `llama3:8b` (or your preferred model)
   - **Provider**: `ollama`
   - **Prompt**:
     ```jinja
     Answer this question using the search results:
     
     Question: {{ input }}
     Search Results: {{ previous_outputs.search_agent }}
     ```

**Step 3: Connect the Nodes**
1. Click the **search_agent** node
2. Click the **answer_agent** node
3. A blue arrow appears connecting them

**Step 4: Generate YAML**
1. Click the **YAML** panel toggle in the header
2. Click **Generate YAML** button
3. The YAML appears in the editor:
   ```yaml
   orchestrator:
     id: my_workflow
     strategy: sequential
     agents:
       - search_agent
       - answer_agent
   
   agents:
     - id: search_agent
       type: duckduckgo
       queue: orka:search_agent
       prompt: "{{ input }}"
     
     - id: answer_agent
       type: local_llm
       queue: orka:answer_agent
       model: llama3:8b
       provider: ollama
       prompt: |
         Answer this question using the search results:
         
         Question: {{ input }}
         Search Results: {{ previous_outputs.search_agent }}
   ```

**Step 5: Test Execution**
1. Click the **Execution** panel toggle
2. Enter a question: "What is quantum computing?"
3. Click **Run Workflow**
4. Watch the execution trace and see the final answer

### 3. Save Your Work

**Export YAML:**
1. Click **Generate YAML**
2. Click **Copy** button
3. Save to a `.yml` file

**Save as Example:**
1. Click the **Upload/Examples** button
2. Save your workflow for later reuse

---

## Core Concepts

### Agents
**Modular reasoning units** that perform specific tasks:
- **LLM Agents**: Generate text using language models (OpenAI, local models)
- **Classification Agents**: Binary decisions or multi-option classification
- **Search Agents**: Web search via DuckDuckGo
- **Memory Agents**: Read/write to persistent memory with semantic search

### Nodes
**Control flow elements** that manage workflow execution:
- **Router**: Conditional branching based on decision keys
- **Fork**: Parallel execution of multiple paths
- **Join**: Synchronization point for parallel paths
- **Loop**: Iterative execution with convergence scoring

### Links
**Directional connections** that define execution order:
- Sequential: Agent A → Agent B
- Parallel: Fork → [Agent A, Agent B, Agent C] → Join
- Conditional: Router → {option1: Agent A, option2: Agent B}

### Templates
**Jinja2 syntax** for dynamic prompts:
- `{{ input }}`: Original user input
- `{{ previous_outputs.agent_id }}`: Output from specific agent
- `{{ get_agent_response('agent_id') }}`: Alternative syntax
- `{{ get_loop_number() }}`: Current loop iteration

---

## Agent Types

### LLM Integration Agents

#### Local LLM
- **Type**: `local_llm`
- **Purpose**: Run local models via Ollama, LM Studio, or OpenAI-compatible APIs
- **Configuration**:
  - `model`: Model name (e.g., `llama3:8b`, `deepseek-r1:8b`)
  - `model_url`: API endpoint (default: `http://localhost:11434/api/generate`)
  - `provider`: `ollama` or `openai-compatible`
  - `temperature`: 0.0-2.0 (creativity control)

#### OpenAI Answer
- **Type**: `openai-answer`
- **Purpose**: Generate text using OpenAI models
- **Configuration**:
  - `model`: GPT model (e.g., `gpt-4`, `gpt-3.5-turbo`)
  - `temperature`: 0.0-2.0

### Memory Agents

#### Memory Read/Write
- **Type**: `memory`
- **Purpose**: Persistent memory with semantic search and decay
- **Configuration**:
  - `memory_preset`: `semantic`, `episodic`, `working`, `procedural`, `meta`
  - `operation`: `read` or `write`
  - `namespace`: Memory isolation key
  - `vector`: Enable semantic search (default: true)

**Memory Presets:**
- **Sensory**: Very short-term (15 min) - immediate context
- **Working**: Short-term (1 hour) - active task memory
- **Episodic**: Medium-term (7 days) - personal experiences
- **Semantic**: Long-term (30 days) - factual knowledge
- **Procedural**: Long-term (30 days) - skills and procedures
- **Meta**: Very long-term (90 days) - self-knowledge

### Control Flow Nodes

#### Router
- **Type**: `router`
- **Purpose**: Conditional branching based on classification
- **Configuration**:
  - `decision_key`: Classification agent that provides the routing decision
  - `routing_map`: Map of {option: target_agent_id}

#### Loop
- **Type**: `loop`
- **Purpose**: Iterative execution until convergence
- **Configuration**:
  - `max_loops`: Maximum iterations (default: 3)
  - `score_threshold`: Convergence threshold 0.0-1.0 (default: 0.95)
  - `cognitive_extraction`: Extract insights, improvements, mistakes
  - `internal_workflow`: Nested workflow to execute per iteration

#### Fork/Join
- **Fork Type**: `fork` - Split execution into parallel paths
- **Join Type**: `join` - Synchronize parallel paths
- **Configuration**: Connected via visual links (no manual config needed)

### Search & Retrieval Agents

#### DuckDuckGo
- **Type**: `duckduckgo`
- **Purpose**: Web search with instant answers
- **Configuration**: Prompt with search query

---

## Configuration

### Workspace Presets

Save and load panel layouts:
1. **Development**: Node Palette + Properties + YAML
2. **Execution**: Node Palette + Execution + Output
3. **Custom**: Create your own layout

Toggle panels with toolbar buttons:
- **Node Palette**: Agent types library
- **Properties**: Node configuration
- **YAML**: Generated workflow preview
- **Execution**: Testing and execution

### Canvas Controls

- **Pan**: Click and drag on empty canvas
- **Zoom**: Mouse wheel or pinch gesture
- **Fit View**: Click fit-view button (bottom-left)
- **Select**: Click node to select, click empty space to deselect
- **Multi-select**: Ctrl/Cmd + click multiple nodes
- **Delete**: Select node and press Delete key

### Keyboard Shortcuts

- **Ctrl/Cmd + Z**: Undo
- **Ctrl/Cmd + Shift + Z**: Redo
- **Delete**: Delete selected nodes
- **Ctrl/Cmd + A**: Select all nodes
- **Escape**: Deselect all

---

## Integration with OrKa Core

### Running Generated Workflows

#### Option 1: CLI Execution
```bash
# Export YAML from UI
# Save to workflow.yml
orka run workflow.yml "What is quantum computing?"
```

#### Option 2: API Execution
```bash
# POST to OrKa backend
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "yaml_content": "<generated_yaml>",
    "input": "What is quantum computing?"
  }'
```

#### Option 3: Direct UI Execution
1. Configure `VITE_API_URL_LOCAL` to point to OrKa backend
2. Use **Execution Panel** to run workflows directly
3. View real-time execution traces and outputs

### YAML Compatibility

OrKa UI generates **fully compatible** YAML with OrKa Core v0.9.6:
- ✅ All agent types supported
- ✅ Memory presets with decay configuration
- ✅ Advanced loop configurations (cognitive extraction, score extraction)
- ✅ Nested workflows (loop internal workflows)
- ✅ Fork/join parallel execution
- ✅ Router conditional logic
- ✅ Template rendering with Jinja2

### Backend Requirements

For full functionality, OrKa backend must be running:
```bash
# Start Redis backend
orka-start

# Run a workflow
orka run workflow.yml "input text"
```

---

## Troubleshooting

### Common Issues

#### **Canvas is blank / nodes not appearing**
- **Cause**: Browser cache or rendering issue
- **Solution**: 
  1. Refresh page (F5)
  2. Clear browser cache
  3. Try Ctrl+Shift+R (hard refresh)

#### **YAML generation fails**
- **Cause**: Missing required node properties
- **Solution**:
  1. Select each node and check Properties panel for red error messages
  2. Ensure all required fields are filled (ID, Type, Prompt)
  3. Check connection validation hints

#### **Execution returns errors**
- **Cause**: Backend not running or misconfigured
- **Solution**:
  1. Verify `VITE_API_URL_LOCAL` points to running backend
  2. Check OrKa backend logs: `docker logs orka-backend`
  3. Ensure Redis is running: `orka-start`

#### **Panels not visible**
- **Cause**: Panels collapsed or hidden
- **Solution**:
  1. Click panel toggle buttons in header toolbar
  2. Click collapsed panel header to expand
  3. Use "Start Tour" button to reset layout

#### **Connection validation errors**
- **Cause**: Invalid agent connections (e.g., Join without Fork)
- **Solution**:
  1. Read validation hint tooltips (hover over red connection)
  2. Follow recommended connection patterns
  3. Check [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md) for valid patterns

### Performance Issues

#### **Slow canvas rendering with many nodes**
- **Solution**: 
  1. Use Fit View to reset viewport
  2. Collapse unused panels
  3. Break large workflows into sub-workflows

#### **Slow YAML generation**
- **Solution**:
  1. Reduce number of nodes (>50 nodes can be slow)
  2. Simplify nested loop workflows
  3. Use browser with better performance (Chrome recommended)

---

## Example Workflows

OrKa UI includes pre-built examples in the **Upload Modal**:

### Basic Examples
- **Simple Agent**: Single LLM agent with prompt
- **Search + Answer**: DuckDuckGo search with LLM synthesis
- **Classification Router**: Binary classification with conditional routing

### Advanced Examples
- **Fork/Join Parallel**: Parallel agent execution with synchronization
- **Loop Convergence**: Iterative refinement with scoring
- **Memory Integration**: Semantic memory read/write with decay
- **Cognitive Society**: Multi-agent debate with memory and routing

### Loading Examples
1. Click **Upload** button in header
2. Select **Examples** tab
3. Browse by category (Basic, Control Flow, Memory, Loops, Orka Society)
4. Click example name to load onto canvas

---

## Resources

### Documentation Links
- **Getting Started**: [getting-started.md](getting-started.md)
- **YAML Configuration**: [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md)
- **Agent Types**: [agents.md](agents.md)
- **Memory System**: [MEMORY_SYSTEM_GUIDE.md](MEMORY_SYSTEM_GUIDE.md)
- **GraphScout**: [GRAPH_SCOUT_AGENT.md](GRAPH_SCOUT_AGENT.md)

### Repository Links
- **OrKa UI (TypeScript)**: https://github.com/marcosomma/orka-ui-ts
- **OrKa Core (Python)**: https://github.com/marcosomma/orka-reasoning
- **Docker Hub**: https://hub.docker.com/r/marcosomma/orka-ui

### Support
- **GitHub Issues**: Report bugs or request features
- **Discord**: Join the OrKa community (link in main repo)
- **Documentation**: This guide and related docs

---

## Version Compatibility

| OrKa UI Version | OrKa Core Version | Notes |
|-----------------|-------------------|-------|
| 0.9.6 | 0.9.6 | Current - GraphScout, unified memory |
| 0.9.5 | 0.9.5 | Memory presets, loop validators |
| 0.9.x | 0.9.x | Compatible within minor version |

---

## Security

### Docker Container Security
- Runs as **non-root user** (UID 101)
- All security headers enabled by default
- Static assets served with appropriate cache headers
- API requests proxied with proper security headers

### Best Practices
- Use environment variables for sensitive configuration
- Don't expose Docker port directly to internet (use reverse proxy)
- Keep Docker images updated: `docker pull marcosomma/orka-ui:latest`
- Review generated YAML before production deployment

---

## Contributing

OrKa UI is open source! Contributions welcome:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

---

## License

OrKa UI is licensed under the **Apache License 2.0**. See [LICENSE](../LICENSE) for details.

---

**Next Steps:**
- [Getting Started with OrKa Core](getting-started.md)
- [YAML Configuration Guide](YAML_CONFIGURATION.md)
- [Building Custom Agents](extending-agents.md)
