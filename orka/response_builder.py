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
Response Builder Utility
========================

This module provides utilities for creating and converting OrkaResponse objects.
It centralizes the creation of standardized responses and handles conversion
from legacy response formats to ensure consistent data flow throughout the system.

The ResponseBuilder class offers static methods for:
1. Creating success and error responses
2. Converting legacy response formats
3. Validating response structures
4. Extracting standardized fields

This utility ensures all components return properly formatted OrkaResponse objects
while maintaining compatibility during migration phases.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

from .contracts import OrkaResponse


class ResponseBuilder:
    """
    Utility class for creating and converting OrkaResponse objects.

    Provides static methods to standardize response creation and handle
    conversions from legacy formats to the new OrkaResponse structure.
    """

    @staticmethod
    def create_success_response(
        result: Any,
        component_id: str,
        component_type: str,
        execution_start_time: Optional[float] = None,
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ) -> OrkaResponse:
        """
        Create a successful OrkaResponse.

        Args:
            result: The primary output data
            component_id: Unique identifier of the component
            component_type: Type of component ("agent", "node", "tool")
            execution_start_time: Start time for calculating execution duration
            trace_id: Optional trace identifier
            **kwargs: Additional optional fields

        Returns:
            OrkaResponse: Standardized success response
        """
        response: OrkaResponse = {
            "result": result,
            "status": "success",
            "component_id": component_id,
            "component_type": component_type,
            "timestamp": datetime.now(),
            "metadata": {},
            "metrics": {},
        }

        # Calculate execution time if start time provided
        if execution_start_time is not None:
            response["execution_time_ms"] = (time.time() - execution_start_time) * 1000

        # Add trace ID if provided
        if trace_id:
            response["trace_id"] = trace_id

        # Add optional fields from kwargs
        optional_fields = [
            "error",
            "token_usage",
            "cost_usd",
            "formatted_prompt",
            "confidence",
            "internal_reasoning",
            "memory_entries",
            "sources",
        ]

        for field in optional_fields:
            if field in kwargs and kwargs[field] is not None:
                response[field] = kwargs[field]  # type: ignore[literal-required]

        # Merge metadata and metrics
        if "metadata" in kwargs:
            response["metadata"].update(kwargs["metadata"])
        if "metrics" in kwargs:
            response["metrics"].update(kwargs["metrics"])

        return response

    @staticmethod
    def create_error_response(
        error: str,
        component_id: str,
        component_type: str,
        result: Any = None,
        execution_start_time: Optional[float] = None,
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ) -> OrkaResponse:
        """
        Create an error OrkaResponse.

        Args:
            error: Error message describing what went wrong
            component_id: Unique identifier of the component
            component_type: Type of component ("agent", "node", "tool")
            result: Partial result if any was produced before error
            execution_start_time: Start time for calculating execution duration
            trace_id: Optional trace identifier
            **kwargs: Additional optional fields

        Returns:
            OrkaResponse: Standardized error response
        """
        response: OrkaResponse = {
            "result": result,
            "status": "error",
            "component_id": component_id,
            "component_type": component_type,
            "timestamp": datetime.now(),
            "error": error,
            "metadata": {},
            "metrics": {},
        }

        # Calculate execution time if start time provided
        if execution_start_time is not None:
            response["execution_time_ms"] = (time.time() - execution_start_time) * 1000

        # Add trace ID if provided
        if trace_id:
            response["trace_id"] = trace_id

        # Add optional fields from kwargs
        optional_fields = [
            "token_usage",
            "cost_usd",
            "formatted_prompt",
            "confidence",
            "internal_reasoning",
            "memory_entries",
            "sources",
        ]

        for field in optional_fields:
            if field in kwargs and kwargs[field] is not None:
                response[field] = kwargs[field]  # type: ignore[literal-required]

        # Merge metadata and metrics
        if "metadata" in kwargs:
            response["metadata"].update(kwargs["metadata"])
        if "metrics" in kwargs:
            response["metrics"].update(kwargs["metrics"])

        return response

    @staticmethod
    def from_llm_agent_response(
        legacy_response: Dict[str, Any], component_id: str, component_type: str = "agent"
    ) -> OrkaResponse:
        """
        Convert a legacy LLM agent response to OrkaResponse format.

        Args:
            legacy_response: Original response dict with "response" field
            component_id: Identifier of the component
            component_type: Type of component

        Returns:
            OrkaResponse: Converted response
        """
        return ResponseBuilder.create_success_response(
            result=legacy_response.get("response"),
            component_id=component_id,
            component_type=component_type,
            formatted_prompt=legacy_response.get("formatted_prompt"),
            internal_reasoning=legacy_response.get("internal_reasoning"),
            token_usage=legacy_response.get("token_usage"),
            cost_usd=legacy_response.get("cost_usd"),
            confidence=legacy_response.get("confidence"),
            metadata=legacy_response.get("metadata", {}),
            metrics=legacy_response.get("_metrics", {}),
        )

    @staticmethod
    def from_memory_agent_response(
        legacy_response: Dict[str, Any], component_id: str, component_type: str = "agent"
    ) -> OrkaResponse:
        """
        Convert a legacy memory agent response to OrkaResponse format.

        Args:
            legacy_response: Original response dict with "memories" field
            component_id: Identifier of the component
            component_type: Type of component

        Returns:
            OrkaResponse: Converted response
        """
        return ResponseBuilder.create_success_response(
            result=legacy_response.get("memories"),
            component_id=component_id,
            component_type=component_type,
            memory_entries=legacy_response.get("memories"),
            metadata=legacy_response.get("metadata", {}),
            metrics=legacy_response.get("_metrics", {}),
        )

    @staticmethod
    def from_node_response(
        legacy_response: Dict[str, Any], component_id: str, component_type: str = "node"
    ) -> OrkaResponse:
        """
        Convert a legacy node response to OrkaResponse format.

        Args:
            legacy_response: Original response dict
            component_id: Identifier of the component
            component_type: Type of component

        Returns:
            OrkaResponse: Converted response
        """
        # Try to extract the most likely result field
        result = legacy_response.get("result") or legacy_response.get("output") or legacy_response

        return ResponseBuilder.create_success_response(
            result=result,
            component_id=component_id,
            component_type=component_type,
            metadata=legacy_response.get("metadata", {}),
            metrics=legacy_response.get("_metrics", {}),
        )

    @staticmethod
    def from_tool_response(
        legacy_response: Any, component_id: str, component_type: str = "tool"
    ) -> OrkaResponse:
        """
        Convert a legacy tool response to OrkaResponse format.

        Args:
            legacy_response: Original response (any type)
            component_id: Identifier of the component
            component_type: Type of component

        Returns:
            OrkaResponse: Converted response
        """
        return ResponseBuilder.create_success_response(
            result=legacy_response,
            component_id=component_id,
            component_type=component_type,
            metadata={},
            metrics={},
        )

    @staticmethod
    def validate_response(response: Any) -> bool:
        """
        Validate that a response conforms to OrkaResponse structure.

        Args:
            response: Response object to validate

        Returns:
            bool: True if valid OrkaResponse, False otherwise
        """
        if not isinstance(response, dict):
            return False

        required_fields = ["result", "status", "component_id", "component_type", "timestamp"]
        return all(field in response for field in required_fields)

    @staticmethod
    def extract_legacy_fields(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract common fields from legacy response formats.

        Args:
            response: Legacy response dictionary

        Returns:
            Dict containing extracted fields
        """
        extracted = {}

        # Map common legacy field names to standard names
        field_mappings = {
            "response": "result",
            "answer": "result",
            "output": "result",
            "content": "result",
            "text": "result",
            "memories": "memory_entries",
            "_metrics": "metrics",
        }

        for legacy_field, standard_field in field_mappings.items():
            if legacy_field in response:
                extracted[standard_field] = response[legacy_field]

        return extracted
