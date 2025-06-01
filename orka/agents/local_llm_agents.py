# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Local LLM Agents Module
======================

This module provides agents for interfacing with locally running large language models.
Supports various local LLM serving solutions including Ollama, LM Studio, LMDeploy,
and other OpenAI-compatible APIs.

Local LLM agents enable:
- Fully offline LLM workflows
- Privacy-preserving AI processing
- Custom model deployment flexibility
- Reduced dependency on cloud services
- Integration with self-hosted models
"""

from .base_agent import LegacyBaseAgent as BaseAgent


class LocalLLMAgent(BaseAgent):
    """
    Calls a local LLM endpoint (e.g. Ollama, LM Studio) with a prompt and returns the response.

    This agent mimics the same interface as OpenAI-based agents but uses local model endpoints
    for inference. It supports various local LLM serving solutions like Ollama, LM Studio,
    LMDeploy, and other OpenAI-compatible APIs.

    Supported Providers:
    ------------------
    - ollama: Native Ollama API format
    - lm_studio: LM Studio with OpenAI-compatible endpoint
    - openai_compatible: Any OpenAI-compatible API endpoint

    Configuration Example:
    --------------------
    ```yaml
    - id: my_local_agent
      type: local_llm
      prompt: "Summarize this: {{ input }}"
      model: "mistral"
      model_url: "http://localhost:11434/api/generate"
      provider: "ollama"
      temperature: 0.7
    ```
    """

    def run(self, input_data):
        """
        Generate an answer using a local LLM endpoint.

        Args:
            input_data (dict or str): Input data containing:
                - If dict: prompt (str), model (str), temperature (float), and other params
                - If str: Direct input text to process

        Returns:
            str: Generated answer from the local model.
        """
        # Handle both dict and string inputs for flexibility
        if isinstance(input_data, str):
            input_text = input_data
            prompt = self.prompt or "Input: {{ input }}"
            model = self.params.get("model", "llama3")
            temperature = float(self.params.get("temperature", 0.7))
        else:
            input_text = str(input_data)
            prompt = input_data.get("prompt", self.prompt)
            model = input_data.get("model", self.params.get("model", "llama3"))
            temperature = float(
                input_data.get("temperature", self.params.get("temperature", 0.7))
            )

        # Build the full prompt using template replacement
        full_prompt = self.build_prompt(input_text, prompt)

        # Get model endpoint configuration
        model_url = self.params.get("model_url", "http://localhost:11434/api/generate")
        provider = self.params.get("provider", "ollama")

        try:
            if provider.lower() == "ollama":
                return self._call_ollama(model_url, model, full_prompt, temperature)
            elif provider.lower() in ["lm_studio", "lmstudio"]:
                return self._call_lm_studio(model_url, model, full_prompt, temperature)
            elif provider.lower() == "openai_compatible":
                return self._call_openai_compatible(
                    model_url, model, full_prompt, temperature
                )
            else:
                # Default to Ollama format
                return self._call_ollama(model_url, model, full_prompt, temperature)

        except Exception as e:
            return f"[LocalLLMAgent error: {str(e)}]"

    def build_prompt(self, input_data, template=None):
        """
        Build the prompt from template and input data.

        Args:
            input_data (str): The input data to substitute
            template (str, optional): Template string, defaults to self.prompt

        Returns:
            str: The built prompt
        """
        if template is None:
            template = self.prompt or "Input: {{ input }}"

        # Simple template replacement - replace {{ input }} with input_data
        return template.replace("{{ input }}", str(input_data))

    def _call_ollama(self, model_url, model, prompt, temperature):
        """Call Ollama API endpoint."""
        import requests

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        response = requests.post(model_url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()

    def _call_lm_studio(self, model_url, model, prompt, temperature):
        """Call LM Studio API endpoint (OpenAI-compatible)."""
        import requests

        # LM Studio uses OpenAI-compatible endpoint structure
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": False,
        }

        # Ensure URL ends with /chat/completions for OpenAI compatibility
        if not model_url.endswith("/chat/completions"):
            if model_url.endswith("/"):
                model_url = model_url + "v1/chat/completions"
            else:
                model_url = model_url + "/v1/chat/completions"

        response = requests.post(model_url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def _call_openai_compatible(self, model_url, model, prompt, temperature):
        """Call any OpenAI-compatible API endpoint."""
        import requests

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": False,
        }

        response = requests.post(model_url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
