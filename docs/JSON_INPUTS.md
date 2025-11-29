# JSON Input Support in OrKa

OrKa supports passing structured JSON input to your workflows, enabling advanced use cases such as multi-field data processing, clinical assistants, document automation, and more. This guide explains how to use JSON inputs, best practices, and common patterns.

---

## Why Use JSON Input?
- **Structured Data:** Pass complex objects, arrays, and nested fields directly to your workflow.
- **Dynamic Prompts:** Agents can access any field in the input using Jinja2 syntax (e.g., `{{ input.field }}` or `{{ input.user.name }}`).
- **Reproducibility:** Use the same workflow with different input files for batch or automated runs.
- **Advanced Use Cases:** Ideal for medical, legal, financial, or any scenario where input is more than a single string.

---

## How to Pass JSON Input

### 1. Prepare Your JSON File
Create a file (e.g., `input.json`) with your structured data:

```json
{
  "patient": {
    "name": "Fido",
    "species": "dog",
    "symptoms": ["vomiting", "lethargy"],
    "age": 7
  },
  "history": "No previous major illnesses."
}
```

### 2. Run Your Workflow with JSON Input
Pass the file using the `--json-input` flag **before** the `run` command:

```bash
orka --json-input input.json run my-workflow.yml
```

Or pass inline JSON:

```bash
orka --json-input '{"foo": 123, "bar": "baz"}' run my-workflow.yml
```

**Note:** If you use `--json-input`, any plain text input is ignored.

---

## Accessing JSON Fields in YAML

In your workflow YAML, use Jinja2 syntax to access fields:

```yaml
prompt: "Patient: {{ input.patient.name }}, Symptoms: {{ input.patient.symptoms }}"
```

- Nested fields: `{{ input.patient.name }}`
- Arrays: `{{ input.patient.symptoms }}`
- Top-level: `{{ input.history }}`

You can use all Jinja2 features (loops, conditionals, filters) for advanced templating.

---

## Example: Veterinary Assistant Workflow

**YAML:**
```yaml
orchestrator:
  id: vet-assistant
  agents: [case_summary, diagnosis, recommendations]

agents:
  - id: case_summary
    type: local_llm
    prompt: |
      Patient: {{ input.patient.name }} ({{ input.patient.species }})\n
      Symptoms: {{ input.patient.symptoms | join(', ') }}\n
      History: {{ input.history }}\n
      Summarize the case in 2 sentences.

  - id: diagnosis
    type: local_llm
    prompt: |
      Given the summary: {{ previous_outputs.case_summary }}\n
      What are the most likely diagnoses?

  - id: recommendations
    type: local_llm
    prompt: |
      Based on the diagnosis: {{ previous_outputs.diagnosis }}\n
      Suggest next steps and tests.
```

**Input JSON:**
```json
{
  "patient": {
    "name": "Fido",
    "species": "dog",
    "symptoms": ["vomiting", "lethargy"],
    "age": 7
  },
  "history": "No previous major illnesses."
}
```

**Run:**
```bash
orka --json-input input.json run vet-assistant.yml
```

---

## Tips & Best Practices
- Validate your JSON before running (invalid JSON will cause errors).
- Use descriptive field names for clarity.
- Document expected input structure in your workflow README or YAML comments.
- For batch runs, prepare multiple JSON files and automate with a script.
- Use Jinja2 filters for formatting (e.g., `join`, `upper`, `default`).

---

## Troubleshooting
- **Error: Invalid JSON** – Check for syntax errors or missing commas/brackets.
- **Field not found** – Make sure your YAML references match the JSON structure.
- **Input ignored** – Remember: if `--json-input` is used, plain text input is not passed to agents.

---

## More Examples
See the `examples/` folder for real-world workflows using JSON input.

For further help, visit the [documentation](https://orkacore.com/docs) or open an issue on GitHub.
---
← [YAML Configuration](YAML_CONFIGURATION.md) | [📚 INDEX](index.md) | [Agents](agents.md) →
