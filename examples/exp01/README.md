# Cognitive Iteration Experiment - Society of Agents

## Overview

This experiment implements a **Society of Agents** approach to building comprehensive answers to complex questions through iterative cognitive processes. Unlike traditional consensus-seeking methods, this system focuses on **answer-building** where specialized agents contribute their expertise to create well-rounded, multi-perspective responses.

## 🧠 Agent Society Architecture

### Core Agents

1. **Logic Agent** - Provides analytical reasoning, evidence-based analysis, and logical frameworks
2. **Empathy Agent** - Focuses on human welfare, ethics, moral dimensions, and social impact
3. **Skeptic Agent** - Identifies weaknesses, risks, alternative perspectives, and potential pitfalls
4. **Historian Agent** - Contributes historical context, precedents, patterns, and lessons from the past

### Orchestration Agents

- **Moderator** - Evaluates completeness of answers (0.85 threshold) and guides the iteration process
- **Answer Builder** - Synthesizes contributions into comprehensive multi-sentence answers
- **Memory System** - Tracks answer-building progress and agent interactions

## 📁 Project Structure

```
examples/exp01/
├── cognitive_iteration_experiment_answer.yml      # Main experiment configuration
├── cognitive_iteration_experiment_opinion.yml     # Opinion-focused variant
├── cognitive_iteration_experiment_opinion_local.yml # Local LLM variant
├── run_cognitive_iteration.py                     # Single experiment runner
├── run_cognitive_iteration_100.py                 # Batch experiment runner (100 topics)
└── organize_experiment_logs.py                    # Log organization utility
```

## 🚀 Running the Experiment

### Prerequisites

1. **Environment Setup**:
   ```bash
   cd /d/OrkaProject/orka-core
   ```

2. **Required Dependencies**:
   - OrKa framework installed
   - OpenAI API key configured
   - Redis/Kafka for memory backend (optional)

### Single Experiment

To run a single cognitive iteration experiment:

```bash
python examples/exp01/run_cognitive_iteration.py
```

### Batch Experiment (100 Topics)

To run the comprehensive 100-topic experiment:

```bash
python examples/exp01/run_cognitive_iteration_100.py
```

**What this does:**
- Processes 100 diverse topics automatically
- Each topic gets multiple iteration loops until completeness threshold (0.85) is reached
- Generates timestamped output files and detailed trace logs
- Automatically manages loop counting and progress tracking

### Experiment Configuration

The experiment uses three configuration variants:

#### 1. Answer-Building Mode (`cognitive_iteration_experiment_answer.yml`)
- **Focus**: Building comprehensive answers
- **Agents**: Logic, Empathy, Skeptic, Historian in "analytical modes"
- **Goal**: Multi-perspective, well-reasoned responses
- **Threshold**: 0.85 completeness score

#### 2. Opinion Mode (`cognitive_iteration_experiment_opinion.yml`)
- **Focus**: Opinion formation and perspective sharing
- **Agents**: Same agents in "opinion-focused modes"
- **Goal**: Balanced viewpoint exploration

#### 3. Local LLM Mode (`cognitive_iteration_experiment_opinion_local.yml`)
- **Focus**: Running with local language models
- **Agents**: Optimized for local inference
- **Goal**: Cost-effective experimentation

## 📊 Output Structure

### Immediate Output Files

After running `run_cognitive_iteration_100.py`, you'll get:

```
logs/
├── 100_run_output/
│   ├── orka-reasoning-output_100_001.json
│   ├── orka-reasoning-output_100_002.json
│   └── ... (100 final result files)
└── 100_run_logs/
    ├── orka_trace_20241231_143052.json
    ├── orka_trace_20241231_143127.json
    └── ... (~354 trace files)
```

### Organized Output Structure

Run the organization script to structure the data:

```bash
python examples/exp01/organize_experiment_logs.py
```

This creates:

```
logs/100_run_organized/
├── experiment_001_topic_name/
│   ├── final_result.json
│   ├── trace_loop_01.json
│   ├── trace_loop_02.json
│   ├── ...
│   └── experiment_metadata.json
├── experiment_002_topic_name/
│   └── ... (similar structure)
└── organization_summary.json
```

## 📈 Analytics and Insights

### Generate Comprehensive Analytics

The experiment includes detailed analytics extraction:

```bash
python examples/exp01/extract_experiment_analytics.py
```

**Analytics Generated:**
- **27 detailed metrics** per experiment
- **Execution timing** and **performance data**
- **Cost analysis** and **token usage**
- **Latency patterns** and **efficiency metrics**
- **Technology stack** tracking (models, providers)

### Key Metrics Tracked

1. **Execution Metrics**:
   - Total loops completed
   - Execution time per experiment
   - Loop efficiency and convergence patterns

2. **Cost Analysis**:
   - Total cost per experiment (~$0.016 average)
   - Cost per loop and per agent
   - Token usage breakdown

3. **Performance Data**:
   - Latency per agent execution
   - Memory usage and blob storage
   - Size reduction through deduplication

4. **Quality Metrics**:
   - Completeness scores progression
   - Agent confidence levels
   - Answer quality indicators

## 🔍 Experiment Results Analysis

### Typical Experiment Flow

1. **Initialization**: Topic loaded, agents initialized
2. **Loop 1**: Each agent provides initial perspective
3. **Loop 2-N**: Agents refine and build upon previous contributions
4. **Convergence**: Completeness threshold (0.85) reached
5. **Final Answer**: Comprehensive multi-perspective response generated

### Expected Outcomes

- **Average loops per experiment**: 3.54
- **Average execution time**: 1.36 minutes
- **Success rate**: 100% (all experiments complete)
- **Quality**: Comprehensive, multi-perspective answers

### Sample Topics Covered

The 100-topic experiment covers diverse areas:
- **Ethics**: Gene editing, AI rights, privacy
- **Policy**: Climate action, taxation, regulation
- **Technology**: AI governance, digital rights, automation
- **Society**: Education, healthcare, social justice
- **Economics**: Wealth distribution, market regulation
- **Environment**: Climate engineering, resource management

## 🛠️ Customization Options

### Modifying Agent Behavior

Edit the YAML configuration files to:
- Change agent prompts and personas
- Adjust completeness thresholds
- Modify memory strategies
- Add or remove agents

### Scaling the Experiment

- **More topics**: Add entries to the topic list in `run_cognitive_iteration_100.py`
- **Different models**: Update model configurations in YAML files
- **Local deployment**: Use the `_local.yml` variant for local LLMs
- **Custom metrics**: Modify analytics extraction for specific insights

## 🎯 Use Cases

### Research Applications
- **Cognitive science**: Study multi-agent reasoning patterns
- **AI safety**: Explore collective intelligence approaches
- **Decision making**: Analyze complex policy questions
- **Ethics**: Examine multi-perspective moral reasoning

### Practical Applications
- **Strategic planning**: Generate comprehensive business analyses
- **Policy development**: Create well-rounded policy recommendations
- **Education**: Develop multi-perspective learning materials
- **Consulting**: Provide thorough stakeholder analysis

## 📝 Quick Start Guide

### Complete Workflow

1. **Run the 100-topic experiment**:
   ```bash
   python examples/exp01/run_cognitive_iteration_100.py
   ```

2. **Organize the results**:
   ```bash
   python examples/exp01/organize_experiment_logs.py
   ```

3. **Generate analytics**:
   ```bash
   python examples/exp01/extract_experiment_analytics.py
   ```

4. **Analyze results**:
   - CSV file: `logs/100_run_organized/experiment_analytics.csv`
   - Organized data: `logs/100_run_organized/experiment_XXX_topic_name/`

### Expected Results

After running the complete workflow, you'll have:
- **100 comprehensive answers** to complex questions
- **Detailed execution analytics** (27 metrics per experiment)
- **Performance insights** (cost: ~$1.58, time: ~2.3 hours)
- **Structured data** ready for visualization and analysis

## 🔧 Troubleshooting

### Common Issues

1. **API Rate Limits**: Reduce concurrent requests or add delays
2. **Memory Issues**: Ensure Redis/Kafka backends are running
3. **File Permissions**: Check write permissions for log directories
4. **Configuration Errors**: Validate YAML syntax and agent definitions

### Performance Tips

- Use local LLM variant for cost reduction
- Adjust completeness threshold (0.85) based on quality requirements
- Monitor token usage and adjust agent prompts accordingly
- Use memory backends for improved performance

## 📚 Additional Resources

### Key Files to Explore

- `cognitive_iteration_experiment_answer.yml` - Main experiment configuration
- `run_cognitive_iteration_100.py` - Batch processing script
- `organize_experiment_logs.py` - Log organization utility
- `extract_experiment_analytics.py` - Analytics generation script

### Generated Data

- Final results with comprehensive answers
- Detailed trace logs of agent interactions
- Performance metrics and cost analysis
- Structured data for further analysis

---

*This experiment represents a novel approach to AI-assisted reasoning through society-of-agents collaboration, focusing on comprehensive answer building rather than consensus seeking.* 