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

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from jinja2 import Template

from .cognitive_extraction import extract_cognitive_insights
from .secondary_metrics import extract_secondary_metric
from .types import MetadataKey, PastLoopMetadata

logger = logging.getLogger(__name__)


def create_past_loop_object(
    *,
    loop_number: int,
    score: float,
    result: Dict[str, Any],
    original_input: Any,
    past_loops_metadata_templates: Dict[MetadataKey, str],
    cognitive_extraction: Dict[str, Any],
    create_safe_result_fn,
) -> PastLoopMetadata:
    """Create past_loop object using metadata template with cognitive insights.

    Direct extraction of LoopNode._create_past_loop_object.
    """
    cognitive_insights = extract_cognitive_insights(
        result=result,
        cognitive_extraction=cognitive_extraction,
    )

    reasoning_quality = extract_secondary_metric(result, "REASONING_QUALITY")
    convergence_trend = extract_secondary_metric(result, "CONVERGENCE_TREND", default="STABLE")

    safe_result = create_safe_result_fn(result)

    safe_input = str(original_input)
    if len(safe_input) > 200:
        safe_input = safe_input[:200] + "...<truncated>"

    template_context: Dict[str, Any] = {
        "loop_number": loop_number,
        "score": score,
        "reasoning_quality": reasoning_quality,
        "convergence_trend": convergence_trend,
        "timestamp": datetime.now().isoformat(),
        # BUG #9: do NOT include full result/previous_outputs in templates (trace bloat)
        "input": safe_input,
        "insights": cognitive_insights.get("insights", ""),
        "improvements": cognitive_insights.get("improvements", ""),
        "mistakes": cognitive_insights.get("mistakes", ""),
    }

    # Add template helper functions (same approach as execution engine)
    try:
        helper_payload = {
            "input": safe_input,
            "previous_outputs": {},
            "loop_number": loop_number,
        }

        # Lazy import to avoid circular dependencies
        from ...orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer

        renderer = SimplifiedPromptRenderer()
        helper_functions = renderer._get_template_helper_functions(helper_payload)
        template_context.update(helper_functions)
        logger.debug("- Added %s helper functions to LoopNode template context", len(helper_functions))
    except Exception as e:
        logger.debug("Failed to add helper functions to LoopNode template context: %s", e)

    past_loop_obj: PastLoopMetadata = {}
    for field_name, template_str in past_loops_metadata_templates.items():
        try:
            if not isinstance(template_str, str):
                raise ValueError("Template must be a string")
            template = Template(template_str)
            rendered = template.render(**template_context)
            past_loop_obj[field_name] = rendered  # type: ignore[typeddict-item]
        except Exception as e:
            logger.debug("Failed to render metadata field '%s': %s", field_name, e)
            # Fallbacks preserve old behavior
            if field_name == "loop_number":
                past_loop_obj[field_name] = loop_number  # type: ignore[typeddict-item]
            elif field_name == "score":
                past_loop_obj[field_name] = score  # type: ignore[typeddict-item]
            elif field_name == "timestamp":
                past_loop_obj[field_name] = datetime.now().isoformat()  # type: ignore[typeddict-item]
            elif field_name in cognitive_insights:
                past_loop_obj[field_name] = cognitive_insights[field_name]  # type: ignore[typeddict-item]
            else:
                past_loop_obj[field_name] = f"Error rendering {field_name}"  # type: ignore[typeddict-item]

    past_loop_obj.setdefault("loop_number", loop_number)  # type: ignore[arg-type]
    past_loop_obj.setdefault("score", score)  # type: ignore[arg-type]
    past_loop_obj.setdefault("timestamp", datetime.now().isoformat())  # type: ignore[arg-type]
    # BUG #9: do NOT add "result" field (trace bloat)
    _ = safe_result  # keep variable for parity; intentionally unused

    return past_loop_obj


