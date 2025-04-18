# OrKa

<div align="center">

  <img src="./assets/logo_256.png" alt="OrKa Logo" width="256" height="256"/>

![Tests](https://github.com/marcosomma/orka/actions/workflows/tests.yml/badge.svg)
[![codecov](https://codecov.io/gh/marcosomma/orka/graph/badge.svg?token=50DUUWVJA9)](https://codecov.io/gh/marcosomma/orka)

[WEB](https://marcosomma.github.io/orka/)
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

---
## 🛠️ Installation

- Ensure you have Python and Redis installed on your system.
- Ensure redis is up and running


  ### PIP

  1. **Clone the Repository**:
    ```
      pip install orka-reasoning
    ```
  2. **Build your orkestrator**
    ```
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

  3. **Test Sctipr**
    ```
      import orka.orka_cli

      if __name__ == "__main__":
      # Path to your YAML orchestration config
      config_path = "example.yml"

      # Input to be passed to the orchestrator
      input_text = "What is the capital of France?"

      # Run the orchestrator with logging
      orka.orka_cli.run_cli_entrypoint(
          config_path=config_path,
          input_text=input_text,
          log_to_file=True
      )
    ```
  ### OR 

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/marcosomma/orka.git
   cd orka
   ```

2. **Install Dependencies**:
   ```bash
   pip install -e .
   ```

***!IMPORTANT¡*** **Create a `.env` file** in the root directory with your API credentials and settings:
   ```
   OPENAI_API_KEY=your_openai_api_key
   BASE_OPENAI_MODEL=gpt-4o-mini
   GOOGLE_API_KEY=sksdsadasqwdad....
   GOOGLE_CSE_ID=1234
   ```

## 📄 Usage

OrKa operates based on YAML configuration files that define the orchestration of agents.

1. **Prepare a YAML Configuration**: Create a YAML file (e.g., `example.yml`) that outlines your agentic workflow.
2. **Run OrKa with the Configuration**:
   ```bash
   python -m orka.orka_cli ./example.yml "Your input question" --log-to-file
   ```

This command processes the input question through the defined workflow and logs the reasoning steps.

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

## 📚 Documentation

📘 [View the Documentation](./docs/index.md)

## PIP deploy
```
rm -rf dist/ build/ ./*.egg-info
python3 -m build
pip install --upgrade twine
twine upload dist/*
```

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📜 License & Attribution

This project is licensed under the CC BY-NC 4.0 License. For more details, refer to the [LICENSE](./LICENSE) file.
