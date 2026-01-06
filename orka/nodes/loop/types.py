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

from typing import Any, Dict, Literal, TypedDict


class PastLoopMetadata(TypedDict, total=False):
    loop_number: int
    score: float
    timestamp: str
    insights: str
    improvements: str
    mistakes: str
    result: Dict[str, Any]


class InsightCategory(TypedDict):
    insights: str
    improvements: str
    mistakes: str


CategoryType = Literal["insights", "improvements", "mistakes"]
MetadataKey = Literal["loop_number", "score", "timestamp", "insights", "improvements", "mistakes"]


