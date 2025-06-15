# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

from jinja2 import Template


class CommonUtils:
    """
    Common utility functions used across the orchestrator.
    """

    @staticmethod
    def normalize_bool(value):
        """
        Normalize a value to boolean.
        Accepts bools or strings like 'true', 'yes', etc.

        Args:
            value: Value to normalize

        Returns:
            bool: Normalized boolean value
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes", "1", "on"]
        if isinstance(value, int):
            return value != 0
        return False

    @staticmethod
    def render_prompt(template_str, payload):
        """
        Render a Jinja2 template string with the given payload.
        Used for dynamic prompt construction.

        Args:
            template_str: Jinja2 template string
            payload: Dictionary with template variables

        Returns:
            str: Rendered template

        Raises:
            ValueError: If template_str is not a string
        """
        if not isinstance(template_str, str):
            raise ValueError(
                f"Expected template_str to be str, got {type(template_str)} instead.",
            )
        return Template(template_str).render(**payload)

    @staticmethod
    def add_prompt_to_payload(agent, payload_out, payload):
        """
        Add prompt and formatted_prompt to payload_out if agent has a prompt.

        Args:
            agent: The agent instance
            payload_out: The payload dictionary to modify
            payload: The context payload for template rendering
        """
        if hasattr(agent, "prompt") and agent.prompt:
            payload_out["prompt"] = agent.prompt
            # If the agent has a prompt, render it with the current payload context
            try:
                formatted_prompt = CommonUtils.render_prompt(agent.prompt, payload)
                payload_out["formatted_prompt"] = formatted_prompt
            except Exception:
                # If rendering fails, keep the original prompt
                payload_out["formatted_prompt"] = agent.prompt

    @staticmethod
    def render_agent_prompt(agent, payload):
        """
        Render agent's prompt and add formatted_prompt to payload for agent execution.

        Args:
            agent: The agent instance
            payload: The payload dictionary to modify
        """
        if hasattr(agent, "prompt") and agent.prompt:
            try:
                formatted_prompt = CommonUtils.render_prompt(agent.prompt, payload)
                payload["formatted_prompt"] = formatted_prompt
            except Exception:
                # If rendering fails, use the original prompt
                payload["formatted_prompt"] = agent.prompt

    @staticmethod
    def build_previous_outputs(logs):
        """
        Build a dictionary of previous agent outputs from the execution logs.
        Used to provide context to downstream agents.

        Args:
            logs: List of execution log entries

        Returns:
            dict: Dictionary mapping agent IDs to their outputs
        """
        outputs = {}
        for log in logs:
            agent_id = log["agent_id"]
            payload = log.get("payload", {})

            # Case: regular agent output
            if "result" in payload:
                outputs[agent_id] = payload["result"]

            # Case: JoinNode with merged dict
            if "result" in payload and isinstance(payload["result"], dict):
                merged = payload["result"].get("merged")
                if isinstance(merged, dict):
                    outputs.update(merged)

        return outputs

    @staticmethod
    def extract_llm_metrics(agent, result):
        """
        Extract LLM metrics from agent result or agent state.

        Args:
            agent: The agent instance
            result: The agent's result

        Returns:
            dict or None: LLM metrics if found
        """
        # Check if result is a dict with _metrics
        if isinstance(result, dict) and "_metrics" in result:
            return result["_metrics"]

        # Check if agent has stored metrics (for binary/classification agents)
        if hasattr(agent, "_last_metrics") and agent._last_metrics:
            return agent._last_metrics

        return None

    @staticmethod
    def safe_json_loads(json_str, default=None):
        """
        Safely load JSON string with fallback.

        Args:
            json_str: JSON string to parse
            default: Default value if parsing fails

        Returns:
            Parsed JSON or default value
        """
        try:
            import json

            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def safe_json_dumps(obj, default=None):
        """
        Safely dump object to JSON string with fallback.

        Args:
            obj: Object to serialize
            default: Default value if serialization fails

        Returns:
            JSON string or default value
        """
        try:
            import json

            return json.dumps(obj, default=str)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def validate_agent_id(agent_id):
        """
        Validate agent ID format.

        Args:
            agent_id: Agent ID to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(agent_id, str):
            return False
        if not agent_id.strip():
            return False
        # Agent IDs should not contain special characters that could cause issues
        invalid_chars = [" ", "\t", "\n", "\r", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        return not any(char in agent_id for char in invalid_chars)

    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitize filename for safe file system operations.

        Args:
            filename: Filename to sanitize

        Returns:
            str: Sanitized filename
        """
        import re

        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(" .")
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed"
        return sanitized

    @staticmethod
    def get_nested_value(data, key_path, default=None):
        """
        Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search
            key_path: Dot-separated key path (e.g., "config.memory.limit")
            default: Default value if key not found

        Returns:
            Value at key path or default
        """
        try:
            keys = key_path.split(".")
            value = data
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError, AttributeError):
            return default

    @staticmethod
    def set_nested_value(data, key_path, value):
        """
        Set nested value in dictionary using dot notation.

        Args:
            data: Dictionary to modify
            key_path: Dot-separated key path (e.g., "config.memory.limit")
            value: Value to set
        """
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
