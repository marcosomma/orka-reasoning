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
OrKa Utilities Module
====================

Common utilities for the OrKa framework.

Modules:
--------
- json_parser: Robust JSON parsing and schema validation for LLM outputs
- embedder: Vector embedding utilities for semantic search
- concurrency: Async and concurrency helpers
- logging_utils: Enhanced logging capabilities
- template_validator: Jinja2 template validation
- bootstrap_memory_index: Memory system initialization
"""

from .json_parser import (
    JSONParseError,
    ParseStrategy,
    create_standard_schema,
    parse_llm_json,
    parse_json_safely,
    validate_and_coerce,
)
from .structured_output import (
    StructuredOutputConfig,
    AGENT_DEFAULT_SCHEMAS,
    PROVIDER_CAPABILITIES,
)
from .metric_normalization import (
    normalize_confidence,
    normalize_cost,
    normalize_tokens,
    normalize_latency,
    normalize_metrics,
    normalize_payload,
)

__all__ = [
    "JSONParseError",
    "ParseStrategy",
    "parse_llm_json",
    "parse_json_safely",
    "validate_and_coerce",
    "create_standard_schema",
    "StructuredOutputConfig",
    "AGENT_DEFAULT_SCHEMAS",
    "PROVIDER_CAPABILITIES",
    "normalize_confidence",
    "normalize_cost",
    "normalize_tokens",
    "normalize_latency",
    "normalize_metrics",
    "normalize_payload",
]
