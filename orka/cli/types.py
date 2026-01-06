# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
CLI Type Definitions
===================

This module contains type definitions used throughout the OrKa CLI system.
These types provide structure and validation for orchestration events and data.
"""

from typing import Any, Dict, Optional, TypedDict


class EventPayload(TypedDict):
    """
    [STATS] **Event payload structure** - standardized data format for orchestration events.

    **Purpose**: Provides consistent structure for all events flowing through OrKa workflows,
    enabling reliable monitoring, debugging, and analytics across complex AI systems.

    **Fields:**
    - **message**: Human-readable description of what happened
    - **status**: Machine-readable status for automated processing
    - **data**: Rich structured data for detailed analysis and debugging
    """

    message: str
    status: str
    data: Optional[Dict[str, Any]]


class Event(TypedDict):
    """
    [TARGET] **Complete event record** - comprehensive tracking of orchestration activities.

    **Purpose**: Captures complete context for every action in your AI workflow,
    providing full traceability and enabling sophisticated monitoring and debugging.

    **Event Lifecycle:**
    1. **Creation**: Agent generates event with rich context
    2. **Processing**: Event flows through orchestration pipeline
    3. **Storage**: Event persisted to memory for future analysis
    4. **Analysis**: Event used for monitoring, debugging, and optimization

    **Fields:**
    - **agent_id**: Which agent generated this event
    - **event_type**: What type of action occurred
    - **timestamp**: Precise timing for performance analysis
    - **payload**: Rich event data with status and context
    - **run_id**: Links events across a single workflow execution
    - **step**: Sequential ordering within the workflow
    """

    agent_id: str
    event_type: str
    timestamp: str
    payload: EventPayload
    run_id: Optional[str]
    step: Optional[int]
