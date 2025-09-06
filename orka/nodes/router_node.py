# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
🚦 **Router Node** - Intelligent Traffic Controller
================================================

The RouterNode is the intelligent traffic controller of OrKa workflows, enabling
sophisticated branching logic based on dynamic conditions and previous outputs.

**Core Capabilities:**
- **Dynamic Routing**: Route execution paths based on runtime decisions
- **Multi-path Logic**: Support complex branching with multiple destinations
- **Flexible Matching**: Handle various data types and formats seamlessly
- **Fallback Handling**: Graceful degradation when no routes match

**Real-world Applications:**
- Customer service escalation based on urgency classification
- Content processing pipelines with quality-based routing
- Multi-language support with language-specific agent routing
- A/B testing with random or criteria-based routing
"""

from .base_node import BaseNode


class RouterNode(BaseNode):
    """
    🚦 **The intelligent traffic controller** - routes execution based on dynamic conditions.

    **What makes routing powerful:**
    - **Context-Aware Decisions**: Routes based on previous agent outputs and classifications
    - **Flexible Matching**: Handles strings, booleans, numbers, and complex conditions
    - **Multi-destination Support**: Can route to multiple agents simultaneously
    - **Fallback Safety**: Provides default routes when conditions don't match

    **Routing Patterns:**

    **1. Binary Routing** (most common):
    
    .. code-block:: yaml
    
        - id: content_router
          type: router
          params:
            decision_key: safety_check
            routing_map:
              "true": [content_processor, quality_checker]
              "false": [content_moderator, human_review]

    **2. Multi-way Classification Routing**:
    
    .. code-block:: yaml
    
        - id: intent_router
          type: router
          params:
            decision_key: intent_classifier
            routing_map:
              "question": [search_agent, answer_builder]
              "complaint": [escalation_agent, sentiment_analyzer]
              "compliment": [thank_you_generator]
              "request": [request_processor, validation_agent]

    **3. Priority-based Routing**:
    
    .. code-block:: yaml
    
        - id: priority_router
          type: router
          params:
            decision_key: urgency_classifier
            routing_map:
              "critical": [immediate_response, alert_manager]
              "high": [priority_queue, escalation_check]
              "medium": [standard_processor]
              "low": [batch_processor]

    **Advanced Features:**
    - **Intelligent Type Conversion**: Automatically handles "true"/"false" strings vs boolean values
    - **Case-Insensitive Matching**: Robust matching regardless of case variations
    - **Empty Route Handling**: Graceful handling when no routes are defined
    - **Multi-agent Routing**: Single decision can trigger multiple parallel paths

    **Perfect for:**
    - Workflow branching based on AI agent decisions
    - Quality gates and approval workflows
    - Multi-language or multi-domain routing
    - Error handling and fallback logic
    - A/B testing and experimentation
    """

    def __init__(self, node_id, params=None, **kwargs):
        """
        Initialize the router node.

        Args:
            node_id (str): Unique identifier for the node.
            params (dict): Parameters containing decision_key and routing_map.
            **kwargs: Additional configuration parameters.

        Raises:
            ValueError: If required parameters are missing.
        """
        queue = kwargs.pop("queue", None)
        super().__init__(node_id=node_id, prompt=None, queue=None, **kwargs)
        if params is None:
            raise ValueError(
                "RouterAgent requires 'params' with 'decision_key' and 'routing_map'.",
            )
        self.params = params

    def run(self, input_data):
        """
        Route the workflow based on the decision value.

        Args:
            input_data (dict): Input data containing previous outputs.

        Returns:
            list: List of next nodes to execute based on routing decision.
        """
        # Get decision value from previous outputs
        previous_outputs = input_data.get("previous_outputs", {})
        decision_key = self.params.get("decision_key")
        routing_map = self.params.get("routing_map", {})

        decision_value = previous_outputs.get(decision_key)

        # Handle dictionary decision values
        if isinstance(decision_value, dict):
            decision_value = decision_value.get('response')

        # Normalize decision value for flexible matching
        decision_value_str = str(decision_value).strip().lower()

        # Try different matching strategies in order of preference
        route = (
            routing_map.get(decision_value)  # literal (True, False)
            or routing_map.get(decision_value_str)  # string "true"/"false"
            or routing_map.get(self._bool_key(decision_value_str))  # normalized boolean
            or []  # default empty list
        )

        return route

    def _bool_key(self, val):
        """
        Convert string values to boolean for routing.

        Args:
            val (str): String value to convert.

        Returns:
            bool or str: Boolean value if recognized, original string otherwise.
        """
        if val in ("true", "yes", "1"):
            return True
        if val in ("false", "no", "0"):
            return False
        return val
