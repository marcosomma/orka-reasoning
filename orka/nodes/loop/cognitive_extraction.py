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
import re
from typing import Any, Dict, List, cast

from .types import CategoryType, InsightCategory

logger = logging.getLogger(__name__)


def extract_cognitive_insights(
    result: Dict[str, Any],
    cognitive_extraction: Dict[str, Any],
    max_length: int = 300,
) -> InsightCategory:
    """Extract cognitive insights from result using configured patterns.

    This is a direct extraction of LoopNode._extract_cognitive_insights.
    """
    if not cognitive_extraction.get("enabled", True):
        return InsightCategory(insights="", improvements="", mistakes="")

    extract_patterns = cast(Dict[str, List[str]], cognitive_extraction.get("extract_patterns", {}))
    max_length = cognitive_extraction.get("max_length_per_category", max_length)

    extracted: Dict[CategoryType, List[str]] = {
        "insights": [],
        "improvements": [],
        "mistakes": [],
    }

    if not isinstance(result, dict):
        return InsightCategory(insights="", improvements="", mistakes="")

    # Extract from all agent responses (preserves current behavior)
    for agent_id, agent_result in result.items():
        if not isinstance(agent_result, (str, dict)):
            continue

        texts_to_analyze: list[str] = []
        if isinstance(agent_result, str):
            texts_to_analyze.append(agent_result)
        else:
            for field in ["response", "result", "output", "data"]:
                if field in agent_result and isinstance(agent_result[field], str):
                    texts_to_analyze.append(agent_result[field])
            if not texts_to_analyze:
                texts_to_analyze.append(str(agent_result))

        for text in texts_to_analyze:
            if not text or len(text) < 20:
                continue

            for category in ["insights", "improvements", "mistakes"]:
                cat_key = cast(CategoryType, category)
                patterns = extract_patterns.get(category, [])
                if not isinstance(patterns, list):
                    continue

                for pattern in patterns:
                    if not isinstance(pattern, str):
                        continue
                    try:
                        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            if len(match.groups()) > 0:
                                insight = match.group(1).strip()
                                if insight and len(insight) > 10:
                                    insight = re.sub(r"\s+", " ", insight)
                                    if len(insight) <= 200:
                                        extracted[cat_key].append(insight)
                                        logger.debug(
                                            "[OK] Extracted %s from %s: %s...",
                                            category,
                                            agent_id,
                                            insight[:50],
                                        )
                    except re.error as e:
                        logger.warning("Invalid regex pattern '%s': %s", pattern, e)
                        continue

    result_insights: list[str] = []
    result_improvements: list[str] = []
    result_mistakes: list[str] = []

    for category, items in extracted.items():
        if not items:
            continue

        unique_items: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item.lower() not in seen:
                unique_items.append(item)
                seen.add(item.lower())

        combined = " | ".join(unique_items)
        if len(combined) > max_length:
            combined = combined[:max_length] + "..."

        if category == "insights":
            result_insights.append(combined)
        elif category == "improvements":
            result_improvements.append(combined)
        elif category == "mistakes":
            result_mistakes.append(combined)

    return InsightCategory(
        insights=" | ".join(result_insights),
        improvements=" | ".join(result_improvements),
        mistakes=" | ".join(result_mistakes),
    )


